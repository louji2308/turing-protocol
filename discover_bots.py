"""
PHASE 1: BOT DISCOVERY
=======================
Scans recent blocks on Mantle Sepolia to find wallets that LOOK like bots
based on their on-chain behavior, then saves the top candidates for your
manual approval in Phase 2.

How it works:
  1. Scans the last 8000 blocks via RPC, collecting all wallet addresses
  2. For each wallet with enough transactions, computes quick heuristics
  3. Ranks wallets by "bot-likeness" (regular timing, uniform hours, few protocols)
  4. Saves the top candidates to a file

You then review these candidates in Phase 2 (label_bots.py).

Usage:
  python discover_bots.py
"""
import sys; sys.path.insert(0, '.')
import os
import json
import time
import numpy as np
import pandas as pd
from pathlib import Path
from collections import defaultdict, Counter
from web3 import Web3
from dotenv import load_dotenv
from loguru import logger
from tqdm import tqdm

load_dotenv()

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
RPC_URL = os.getenv("MANTLE_TESTNET_RPC", "https://rpc.sepolia.mantle.xyz")
SCAN_DEPTH = 2000          # How many blocks back to scan (reduced for speed)
MIN_TXS_FOR_CANDIDATE = 6  # Skip wallets with fewer than this many txs
TOP_N_CANDIDATES = 30      # How many top candidates to save for review
BOT_SCORE_THRESHOLD = 0.4  # Minimum bot-likeness score to be a candidate

OUTPUT_DIR = Path("interrogator/data")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CANDIDATES_FILE = OUTPUT_DIR / "bot_candidates.json"

# ---------------------------------------------------------------------------
# STEP 1: Scan blocks and collect wallet activity
# ---------------------------------------------------------------------------
def scan_blocks(w3: Web3, depth: int) -> dict:
    """
    Scans `depth` blocks backwards from the latest block.
    For each block, extracts all unique sender addresses and basic stats.

    Returns a dict mapping each wallet address to:
      {
        "tx_count": total transactions sent,
        "block_range": [first_block, last_block],
        "timestamps": list of block timestamps (used for timing heuristics),
        "to_addresses": list of destination addresses,
        "hours": list of hours of day (0-23),
      }
    """
    latest = w3.eth.block_number
    start_block = latest - depth
    logger.info(f"Scanning blocks {start_block} → {latest} (depth={depth})")

    wallets = defaultdict(lambda: {
        "tx_count": 0,
        "block_range": [999999999, 0],
        "timestamps": [],
        "to_addresses": [],
        "hours": [],
        "days": [],
        "gas_prices": [],
    })

    for block_num in tqdm(range(latest, start_block, -1), desc="Scanning blocks"):
        try:
            # Fast path: skip empty blocks (most testnet blocks are empty)
            tx_count = w3.eth.get_block_transaction_count(block_num)
            if tx_count == 0:
                continue

            block = w3.eth.get_block(block_num, full_transactions=True)
            ts = block.timestamp
            hour = int(pd.Timestamp(ts, unit="s", tz="UTC").hour)
            day = int(pd.Timestamp(ts, unit="s", tz="UTC").dayofweek)

            for tx in block.transactions:
                sender = tx["from"].lower()
                info = wallets[sender]
                info["tx_count"] += 1
                info["block_range"][0] = min(info["block_range"][0], block_num)
                info["block_range"][1] = max(info["block_range"][1], block_num)
                info["timestamps"].append(ts)
                info["to_addresses"].append((tx.get("to") or "0x0").lower())
                info["hours"].append(hour)
                info["days"].append(day)
                info["gas_prices"].append(tx.gasPrice)

        except Exception as e:
            logger.debug(f"Block {block_num} error: {e}")
            continue

    return wallets


# ---------------------------------------------------------------------------
# STEP 2: Compute bot-likeness heuristics for each wallet
# ---------------------------------------------------------------------------
def compute_bot_score(info: dict) -> float:
    """
    Computes a bot-likeness score from 0.0 (definitely human) to 1.0 (definitely bot).
    Uses lightweight heuristics — not the full 47 features.

    Scoring dimensions:
      - Timing regularity: bots have very consistent inter-tx gaps
      - Hour uniformity: bots are active across all 24 hours
      - Protocol concentration: bots interact with few contracts
      - Gas precision: bots use the same gas price consistently
      - Activity volume: bots tend to have more transactions
    """
    scores = []

    # --- Dimension 1: Timing regularity ---
    timestamps = sorted(info["timestamps"])
    if len(timestamps) >= 3:
        deltas = np.diff(timestamps)
        # Filter out gaps > 1 hour (likely inactivity, not behavior)
        deltas = deltas[deltas < 3600]
        if len(deltas) >= 2:
            cv = np.std(deltas) / (np.mean(deltas) + 1e-9)
            # cv < 0.5 → very regular → bot-like (score near 1)
            # cv > 2.0 → very irregular → human-like (score near 0)
            timing_score = max(0.0, min(1.0, 1.0 - (cv - 0.3) / 2.0))
            scores.append(("timing_cv", timing_score, 0.30))

            # Fast reaction ratio (< 2 seconds)
            fast_ratio = (deltas < 2).sum() / len(deltas)
            fast_score = fast_ratio  # Higher = more bot-like
            scores.append(("fast_ratio", fast_score, 0.15))
        else:
            scores.append(("timing", 0.5, 0.30))
    else:
        scores.append(("timing", 0.5, 0.30))

    # --- Dimension 2: Hour uniformity (Gini) ---
    hours = info["hours"]
    if hours:
        hour_counts = np.zeros(24)
        for h in hours:
            hour_counts[h] += 1
        total = hour_counts.sum()
        if total > 0:
            # Gini = 0 → perfectly uniform (bot-like 24/7)
            # Gini = 1 → all activity in one hour (human-like)
            sorted_counts = np.sort(hour_counts)
            n = len(sorted_counts)
            cumsum = np.cumsum(sorted_counts)
            gini = (2 * np.sum((np.arange(1, n+1)) * sorted_counts) - (n+1) * cumsum[-1]) / (n * cumsum[-1] + 1e-9)
            hour_score = 1.0 - gini  # Low gini = bot-like
            scores.append(("hour_gini", max(0.0, min(1.0, hour_score)), 0.15))

            # Also check: number of unique hours active
            unique_hours = len(np.unique(hours))
            uniq_hour_score = min(1.0, unique_hours / 24.0)
            scores.append(("unique_hours", uniq_hour_score, 0.05))
        else:
            scores.append(("hours", 0.5, 0.20))
    else:
        scores.append(("hours", 0.5, 0.20))

    # --- Dimension 3: Protocol concentration ---
    to_addrs = info["to_addresses"]
    if to_addrs:
        unique_to = len(set(to_addrs))
        total_txs = len(to_addrs)
        # >30% unique destinations → human-like exploration
        # <10% unique destinations → bot-like concentration
        unique_ratio = unique_to / total_txs
        conc_score = max(0.0, min(1.0, 1.0 - unique_ratio * 3))
        scores.append(("concentration", conc_score, 0.15))

        # Top-1 destination ratio
        addr_counts = Counter(to_addrs)
        top1_ratio = max(addr_counts.values()) / total_txs
        top1_score = top1_ratio  # High = bot-like
        scores.append(("top1_ratio", top1_score, 0.05))
    else:
        scores.append(("concentration", 0.5, 0.20))

    # --- Dimension 4: Gas price precision ---
    gas_prices = info["gas_prices"]
    if gas_prices and len(gas_prices) >= 3:
        gas_array = np.array(gas_prices, dtype=float) / 1e9
        gas_cv = np.std(gas_array) / (np.mean(gas_array) + 1e-9)
        # Low CV → precise, bot-like
        gas_score = max(0.0, min(1.0, 1.0 - gas_cv))
        scores.append(("gas_precision", gas_score, 0.10))
    else:
        scores.append(("gas", 0.5, 0.10))

    # --- Dimension 5: Activity volume ---
    tx_count = info["tx_count"]
    vol_score = min(1.0, tx_count / 100.0)  # More txs = more bot-like
    scores.append(("volume", vol_score, 0.05))

    # Compute weighted average
    total_weight = sum(w for _, _, w in scores)
    final_score = sum(s * w for _, s, w in scores) / total_weight

    return float(np.clip(final_score, 0.0, 1.0))


# ---------------------------------------------------------------------------
# STEP 3: Run discovery
# ---------------------------------------------------------------------------
def main():
    logger.info("=" * 60)
    logger.info("PHASE 1: BOT DISCOVERY ON MANTLE SEPOLIA")
    logger.info("=" * 60)

    # Connect
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        logger.error("Cannot connect to Mantle RPC. Check your connection.")
        sys.exit(1)
    logger.info(f"Connected | Chain ID: {w3.eth.chain_id} | Block: {w3.eth.block_number}")

    # Scan blocks
    t0 = time.time()
    wallets = scan_blocks(w3, SCAN_DEPTH)
    scan_time = time.time() - t0
    logger.info(f"Scanned {SCAN_DEPTH} blocks in {scan_time:.0f}s")
    logger.info(f"Found {len(wallets)} unique sender wallets")

    # Filter candidates (minimum transactions)
    candidates = []
    for addr, info in wallets.items():
        if info["tx_count"] >= MIN_TXS_FOR_CANDIDATE:
            score = compute_bot_score(info)
            candidates.append({
                "address": addr,
                "tx_count": info["tx_count"],
                "block_range": info["block_range"],
                "unique_to_addresses": len(set(info["to_addresses"])),
                "unique_hours": len(set(info["hours"])),
                "bot_score": round(score, 4),
            })

    logger.info(f"Candidates with >= {MIN_TXS_FOR_CANDIDATE} txs: {len(candidates)}")

    if not candidates:
        logger.warning("No candidates found. Try increasing SCAN_DEPTH.")
        sys.exit(0)

    # Sort by bot score (descending)
    candidates.sort(key=lambda c: c["bot_score"], reverse=True)

    # Filter by threshold
    candidates = [c for c in candidates if c["bot_score"] >= BOT_SCORE_THRESHOLD]

    # Take top N
    top_candidates = candidates[:TOP_N_CANDIDATES]

    # Show summary
    logger.success(f"\nTop {len(top_candidates)} bot candidates:")
    logger.success(f"{'Rank':<5} {'Address':<45} {'Score':<8} {'Tx Count':<10} {'Unique To':<10} {'Hours':<6}")
    logger.success("-" * 85)
    for i, c in enumerate(top_candidates, 1):
        logger.success(
            f"{i:<5} {c['address']:<45} {c['bot_score']:<8.4f} "
            f"{c['tx_count']:<10} {c['unique_to_addresses']:<10} {c['unique_hours']:<6}"
        )

    # Save to file
    output_data = {
        "scan_info": {
            "chain_id": w3.eth.chain_id,
            "latest_block": w3.eth.block_number,
            "scan_depth": SCAN_DEPTH,
            "total_wallets_found": len(wallets),
            "total_candidates": len(candidates),
        },
        "candidates": top_candidates,
    }

    with open(CANDIDATES_FILE, "w") as f:
        json.dump(output_data, f, indent=2)
    logger.success(f"\nSaved candidates to {CANDIDATES_FILE}")

    logger.info("\n" + "=" * 60)
    logger.info("NEXT STEP: Review these candidates using label_bots.py")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
