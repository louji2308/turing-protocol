"""
PHASE 2: INTERACTIVE BOT LABELING
==================================
You review the candidates found by discover_bots.py one by one.
For each candidate, the script:
  1. Fetches their full transaction history via Etherscan V2 API
  2. Computes all 47 behavioral features
  3. Shows you a summary of their behavior
  4. You type 'y' (YES this is a bot) or 'n' (NO, skip)

HOW TO RUN:
  python label_bots.py

WHAT TO LOOK FOR:
  Bots typically have:
  - Very consistent timing (CV < 0.5)
  - Active across all 24 hours (Gini < 0.2)
  - Interact with only 1-3 different contracts
  - Precise gas prices (low CV)
  - Nearly zero failed transactions

  Humans typically have:
  - Irregular timing (CV > 1.0)
  - Active during specific hours only (Gini > 0.5)
  - Interact with many different addresses
  - Variable gas prices with rounding
  - Some failed transactions
"""
import sys; sys.path.insert(0, '.')
import os
import json
import time
import numpy as np
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger
from web3 import Web3
import requests

from data_pipeline.mantle_fetcher import MantleDataFetcher
from data_pipeline.feature_engineer import BehavioralFeatureEngineer

load_dotenv()

CANDIDATES_FILE = Path("interrogator/data/bot_candidates.json")
OUTPUT_FILE = Path("interrogator/data/known_agents.json")
HUMAN_WALLET_FILE = Path("interrogator/data/known_humans.json")

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "").strip()
RPC_URL = os.getenv("MANTLE_TESTNET_RPC", "https://rpc.sepolia.mantle.xyz")


def fetch_wallet_tx_via_explorer(address: str, max_txs: int = 100) -> list:
    """
    Fetches transactions for a wallet using the Etherscan V2 API.
    Returns a list of dicts matching the format expected by BehavioralFeatureEngineer.
    """
    all_txs = []
    page = 1
    per_page = 50

    while len(all_txs) < max_txs:
        params = {
            "chainid": 5003,
            "module": "account",
            "action": "txlist",
            "address": address,
            "startblock": 0,
            "endblock": "latest",
            "page": page,
            "offset": per_page,
            "sort": "asc",
            "apikey": ETHERSCAN_API_KEY,
        }
        try:
            resp = requests.get(
                "https://api.etherscan.io/v2/api",
                params=params,
                timeout=15,
                headers={"User-Agent": "Mozilla/5.0 TuringProtocol/1.0"},
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            if data.get("status") != "1":
                msg = data.get("message", "")
                if "No transactions" in msg or "No records" in msg:
                    return []
                logger.debug(f"API error for {address[:10]}: {msg}")
                return []
            results = data.get("result", [])
            if not results:
                break
            all_txs.extend(results)
            if len(results) < per_page:
                break
            page += 1
            time.sleep(0.2)  # Rate limit: 5 calls/sec max
        except Exception as e:
            logger.debug(f"Fetch error for {address[:10]}: {e}")
            return []

    return all_txs[:max_txs]


def tx_list_to_dataframe(txs: list, wallet_address: str) -> pd.DataFrame:
    """
    Converts a list of explorer API transaction dicts into the DataFrame format
    expected by BehavioralFeatureEngineer.compute_all_features().
    """
    if not txs:
        return pd.DataFrame()

    df = pd.DataFrame(txs)

    # Rename columns to match what feature_engineer expects
    column_map = {
        "hash": "tx_hash",
        "blockNumber": "block_number",
        "timeStamp": "timestamp",
        "from": "from_addr",
        "to": "to_addr",
        "value": "value_wei",
        "gas": "gas_limit",
        "gasUsed": "gas_used",
        "gasPrice": "gas_price",
        "isError": "failed",
        "input": "input_data",
        "methodId": "method_id",
        "functionName": "function_name",
        "txreceipt_status": "txreceipt_status",
        "contractAddress": "contract_address",
    }

    for old, new in column_map.items():
        if old in df.columns:
            df[new] = df[old]

    # Make sure required columns exist with correct types
    for col in ["timestamp", "block_number", "value_wei", "gas_limit", "gas_used", "gas_price"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "failed" in df.columns:
        df["failed"] = pd.to_numeric(df["failed"], errors="coerce").fillna(0).astype(int)
    else:
        df["failed"] = 0

    df["success"] = 1 - df["failed"]
    df["value_mnt"] = df["value_wei"] / 1e18
    df["gas_cost_mnt"] = (df["gas_used"] * df["gas_price"]) / 1e18
    gas_limit = df.get("gas_limit", pd.Series(1))
    df["gas_efficiency"] = df["gas_used"] / (gas_limit + 1e-9)

    wallet_lower = wallet_address.lower()
    if "from_addr" in df.columns:
        df["from_addr"] = df["from_addr"].astype(str).str.lower()
        df["is_sender"] = df["from_addr"] == wallet_lower
    else:
        df["is_sender"] = True

    if "to_addr" in df.columns:
        df["to_addr"] = df["to_addr"].fillna("").astype(str).str.lower()
    else:
        df["to_addr"] = ""

    df["is_contract_call"] = df.get("input_data", pd.Series("")).astype(str).str.len() > 2

    if "method_id" not in df.columns:
        df["method_id"] = df["is_contract_call"].apply(
            lambda x: "0x" if not x else "0x12345678"
        )

    # Compute temporal features
    df = df.sort_values("timestamp").reset_index(drop=True)
    df["time_since_prev_tx"] = df["timestamp"].diff()
    df["hour_of_day"] = pd.to_datetime(df["timestamp"], unit="s", utc=True).dt.hour
    df["day_of_week"] = pd.to_datetime(df["timestamp"], unit="s", utc=True).dt.dayofweek

    # Protocol tagging (simplified — use known addresses if available)
    df["protocol"] = "unknown"
    df["is_known_protocol"] = False

    return df


def print_wallet_summary(address: str, features: dict):
    """Prints a readable summary of the wallet's features."""
    print(f"\n{'='*70}")
    print(f"WALLET: {address}")
    print(f"{'='*70}")

    # Temporal features
    print(f"\n  TIMING:")
    print(f"    Mean log delay:     {features.get('temp_0_log_mean_delta', 0):.4f}")
    print(f"    Std log delay:      {features.get('temp_1_log_std_delta', 0):.4f}")
    print(f"    CV:                 {features.get('temp_4_cv', 0):.4f}")
    print(f"    Fast reaction ratio:{features.get('temp_5_fast_reaction_ratio', 0):.4f}")
    print(f"    Hour Gini:          {features.get('temp_7_hour_gini', 0):.4f}")

    # Gas features
    print(f"\n  GAS BEHAVIOR:")
    print(f"    Price CV:           {features.get('gas_0_price_cv', 0):.4f}")
    print(f"    Round fraction:     {features.get('gas_1_round_fraction', 0):.4f}")
    print(f"    Mean efficiency:    {features.get('gas_5_mean_efficiency', 0):.4f}")

    # Diversity features
    print(f"\n  DIVERSITY:")
    print(f"    Unique protocols:   {features.get('div_1_unique_protocols', 0):.1f}")
    print(f"    Protocol HHI:       {features.get('div_3_protocol_hhi', 0):.4f}")
    print(f"    Exploration ratio:  {features.get('div_4_exploration_ratio', 0):.4f}")

    # Event features
    print(f"\n  BURSTINESS:")
    print(f"    Burstiness:         {features.get('event_0_burstiness', 0):.4f}")
    print(f"    Clustering:          {features.get('event_2_clustering', 0):.4f}")

    # Consistency
    print(f"\n  CONSISTENCY:")
    print(f"    Failure rate:       {features.get('consist_4_failure_rate', 0):.4f}")
    print(f"    Method evolution:   {features.get('consist_5_method_evolution', 0):.4f}")

    print(f"\n  BOT SIGNALS:")
    bot_signals = []
    if features.get('temp_4_cv', 1) < 0.5:
        bot_signals.append("LOW TIMING VARIANCE")
    if features.get('temp_7_hour_gini', 1) < 0.2:
        bot_signals.append("24/7 ACTIVITY")
    if features.get('temp_5_fast_reaction_ratio', 0) > 0.5:
        bot_signals.append("MANY FAST REACTIONS")
    if features.get('div_1_unique_protocols', 5) <= 2:
        bot_signals.append("FEW PROTOCOLS")
    if features.get('div_4_exploration_ratio', 1) < 0.1:
        bot_signals.append("NO EXPLORATION")
    if features.get('gas_0_price_cv', 1) < 0.1:
        bot_signals.append("PRECISE GAS")
    if features.get('consist_4_failure_rate', 1) < 0.01:
        bot_signals.append("NEVER FAILS")
    if features.get('event_0_burstiness', 0) < -0.3:
        bot_signals.append("REGULAR TIMING")

    if bot_signals:
        print(f"    " + ", ".join(bot_signals))
    else:
        print(f"    (no strong bot signals — likely human)")

    print(f"{'='*70}\n")


def main():
    logger.info("=" * 60)
    logger.info("PHASE 2: INTERACTIVE BOT LABELING")
    logger.info("=" * 60)

    # Load candidates from Phase 1
    if not CANDIDATES_FILE.exists():
        logger.error(f"Candidates file not found: {CANDIDATES_FILE}")
        logger.error("Run discover_bots.py first.")
        sys.exit(1)

    with open(CANDIDATES_FILE) as f:
        data = json.load(f)

    candidates = data["candidates"]
    logger.info(f"Loaded {len(candidates)} candidates from Phase 1")

    # Load previously approved agents (if any)
    approved = []
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE) as f:
            approved = json.load(f)
        logger.info(f"Previously approved agents: {len(approved)}")

    # Load previously approved humans (if any)
    approved_humans = []
    if HUMAN_WALLET_FILE.exists():
        with open(HUMAN_WALLET_FILE) as f:
            approved_humans = json.load(f)
        logger.info(f"Previously approved humans: {len(approved_humans)}")

    engineer = BehavioralFeatureEngineer()

    approved_addresses = {a["address"] for a in approved}
    skipped_addresses = set()

    for i, candidate in enumerate(candidates):
        addr = candidate["address"]

        # Skip if already decided
        if addr in approved_addresses or addr in skipped_addresses:
            continue

        print(f"\n{'#'*70}")
        print(f"CANDIDATE {i+1}/{len(candidates)}")
        print(f"{'#'*70}")
        print(f"Address: {addr}")
        print(f"Bot score (from scan): {candidate['bot_score']:.4f}")
        print(f"Tx count (in scan window): {candidate['tx_count']}")
        print(f"Unique to-addresses: {candidate['unique_to_addresses']}")
        print(f"Unique hours active: {candidate['unique_hours']}")

        # Fetch full tx history
        print(f"\n  Fetching full transaction history via Etherscan API...")
        txs = fetch_wallet_tx_via_explorer(addr, max_txs=150)

        if not txs or len(txs) < 10:
            print(f"  ⚠ Only {len(txs) if txs else 0} transactions found — skipping")
            skipped_addresses.add(addr)
            continue

        print(f"  Fetched {len(txs)} transactions")

        # Convert to DataFrame and compute features
        try:
            df = tx_list_to_dataframe(txs, addr)
            if len(df) < 10:
                print(f"  ⚠ Too few usable transactions ({len(df)}) — skipping")
                skipped_addresses.add(addr)
                continue

            features = engineer.compute_all_features(df, addr)
        except Exception as e:
            print(f"  ⚠ Feature computation failed: {e}")
            skipped_addresses.add(addr)
            continue

        # Show summary
        print_wallet_summary(addr, features)

        # Ask user
        while True:
            choice = input("Is this a BOT? (y=yes agent, n=no skip, h=yes human, q=quit): ").strip().lower()
            if choice == 'y':
                approved.append({
                    "address": addr,
                    "label": 0,
                    "source": "discovered_bot",
                    "bot_score": candidate["bot_score"],
                    "tx_count": len(txs),
                })
                approved_addresses.add(addr)
                print(f"  ✓ Saved as AGENT")
                # Save immediately in case of crash
                with open(OUTPUT_FILE, "w") as f:
                    json.dump(approved, f, indent=2)
                break
            elif choice == 'n':
                skipped_addresses.add(addr)
                print(f"  ✗ Skipped")
                break
            elif choice == 'h':
                approved_humans.append({
                    "address": addr,
                    "label": 1,
                    "source": "discovered_human",
                    "bot_score": candidate["bot_score"],
                    "tx_count": len(txs),
                })
                with open(HUMAN_WALLET_FILE, "w") as f:
                    json.dump(approved_humans, f, indent=2)
                print(f"  ✓ Saved as HUMAN")
                break
            elif choice == 'q':
                print(f"\nExiting. Progress saved.")
                sys.exit(0)
            else:
                print("  Please type 'y', 'n', 'h', or 'q'")

    # Final summary
    print(f"\n{'='*70}")
    print(f"LABELING COMPLETE")
    print(f"{'='*70}")
    print(f"Agents approved: {len(approved)}")
    print(f"Humans approved: {len(approved_humans)}")
    print(f"Skipped: {len(skipped_addresses)}")

    with open(OUTPUT_FILE, "w") as f:
        json.dump(approved, f, indent=2)
    if approved_humans:
        with open(HUMAN_WALLET_FILE, "w") as f:
            json.dump(approved_humans, f, indent=2)

    print(f"\n✅ Saved agents to {OUTPUT_FILE}")
    if approved_humans:
        print(f"✅ Saved humans to {HUMAN_WALLET_FILE}")
    print(f"\nNEXT: Run train_master.py to build the final dataset and train the model.")


if __name__ == "__main__":
    main()
