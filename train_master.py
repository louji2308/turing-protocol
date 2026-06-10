"""
PHASE 3: MASTER TRAINING PIPELINE
==================================
Reads your approved bot addresses (from label_bots.py) and your known human
wallet, fetches their full transaction histories, computes features, blends
with synthetic data to reach a target dataset size, then trains the model.

Usage:
  python train_master.py

What happens:
  1. Loads approved agents from interrogator/data/known_agents.json
  2. Loads approved humans from interrogator/data/known_humans.json
  3. Adds your GHOST_WALLET_ADDRESS as a known human (you control it)
  4. Fetches ALL their transactions via Etherscan V2 API
  5. Computes 47 behavioral features for each real wallet
  6. Generates synthetic wallets to reach 300 total samples
  7. Trains the XGBoost model
  8. Evaluates on holdout test set
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

from data_pipeline.feature_engineer import BehavioralFeatureEngineer
from data_pipeline.mantle_fetcher import MantleDataFetcher
from scripts.generate_training_data import make_synthetic_wallet_df
from scripts.train_model import main as train_main

load_dotenv()

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
AGENTS_FILE = Path("interrogator/data/known_agents.json")
HUMANS_FILE = Path("interrogator/data/known_humans.json")
OUTPUT_DIR = Path("interrogator/data")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DATASET_PATH = OUTPUT_DIR / "training_data.parquet"

TARGET_TOTAL = 1000
SYNTHETIC_BATCH = 50  # Generate this many at a time

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "").strip()
GHOST_WALLET = os.getenv("GHOST_WALLET_ADDRESS", "").strip()
RPC_URL = os.getenv("MANTLE_TESTNET_RPC", "https://rpc.sepolia.mantle.xyz")


# ---------------------------------------------------------------------------
# STEP 1: Fetch real wallet data
# ---------------------------------------------------------------------------
def fetch_and_compute(address: str, label: int, source: str, engineer) -> dict:
    """
    Fetches transaction history for a single wallet via Etherscan API
    and computes behavioral features.

    Returns a dict with all 47 features + 'label' key.
    Returns None if it fails.
    """
    address = Web3.to_checksum_address(address) if Web3.is_address(address) else address
    w3_check = Web3(Web3.HTTPProvider(RPC_URL))

    try:
        # Use MantleDataFetcher to get the data (handles V2 API + RPC fallback)
        fetcher = MantleDataFetcher(RPC_URL)
        df = fetcher.fetch_wallet_transactions(address, max_txs=200)

        if df is None or len(df) < 10:
            logger.warning(f"  {address[:10]}: only {len(df) if df is not None else 0} txs")
            return None

        features = engineer.compute_all_features(df, address)
        features["label"] = label
        features["source"] = source
        features["wallet_address"] = address

        logger.success(f"  {address[:10]}: {len(df)} txs → features computed ✓")
        return features

    except Exception as e:
        logger.warning(f"  {address[:10]}: failed — {e}")
        return None


# ---------------------------------------------------------------------------
# STEP 2: Generate synthetic data to fill gaps
# ---------------------------------------------------------------------------
def generate_synthetic_batch(
    n_wallets: int,
    label: int,
    engineer,
    base_seed: int = 999
) -> list:
    """
    Generates `n_wallets` synthetic wallets of the given class.
    Label 1 = human (human_strength > 0.5), Label 0 = agent (human_strength < 0.5).
    """
    rng = np.random.default_rng(base_seed)
    results = []

    for i in range(n_wallets):
        # Draw human_strength from a bimodal distribution
        if rng.random() < 0.4:
            human_strength = rng.beta(0.5, 0.5)
        else:
            human_strength = rng.beta(1.5, 1.5)

        # Ensure it matches the requested label
        if label == 1 and human_strength <= 0.5:
            human_strength = 0.5 + rng.random() * 0.5
        elif label == 0 and human_strength >= 0.5:
            human_strength = rng.random() * 0.5

        n_txs = int(rng.integers(40, 130))
        seed = base_seed + i * 7 + 13

        try:
            df, addr = make_synthetic_wallet_df(
                n=n_txs, seed=seed, human_strength=human_strength
            )
            features = engineer.compute_all_features(df, addr)
            features["label"] = label
            features["source"] = f"synthetic_strength_{human_strength:.2f}"
            features["wallet_address"] = f"synthetic_{seed}"
            results.append(features)
        except Exception as e:
            logger.debug(f"  Skipped synthetic {i}: {e}")
            continue

    return results


# ---------------------------------------------------------------------------
# STEP 3: Build the complete dataset
# ---------------------------------------------------------------------------
def build_dataset():
    logger.info("=" * 60)
    logger.info("BUILDING TRAINING DATASET")
    logger.info("=" * 60)

    engineer = BehavioralFeatureEngineer()
    all_features = []
    real_counts = {"human": 0, "agent": 0}

    # --- Load approved addresses ---
    approved_agents = []
    if AGENTS_FILE.exists():
        with open(AGENTS_FILE) as f:
            approved_agents = json.load(f)

    approved_humans = []
    if HUMANS_FILE.exists():
        with open(HUMANS_FILE) as f:
            approved_humans = json.load(f)

    # Always add your ghost wallet as a known human
    human_addresses = [h["address"] for h in approved_humans]
    if GHOST_WALLET and GHOST_WALLET not in human_addresses:
        human_addresses.append(GHOST_WALLET)

    agent_addresses = [a["address"] for a in approved_agents]

    logger.info(f"Real humans: {len(human_addresses)}")
    logger.info(f"Real agents: {len(agent_addresses)}")

    # --- Fetch real humans ---
    logger.info("\n--- Fetching HUMAN wallets ---")
    for addr in human_addresses:
        result = fetch_and_compute(addr, 1, "real_human", engineer)
        if result:
            all_features.append(result)
            real_counts["human"] += 1

    # --- Fetch real agents ---
    logger.info("\n--- Fetching AGENT wallets ---")
    for addr in agent_addresses:
        result = fetch_and_compute(addr, 0, "real_agent", engineer)
        if result:
            all_features.append(result)
            real_counts["agent"] += 1

    # --- Generate synthetic wallets to reach target ---
    current_count = len(all_features)
    needed = TARGET_TOTAL - current_count

    if needed > 0:
        n_human_synth = int(needed * (real_counts["human"] + 1) / (real_counts["human"] + real_counts["agent"] + 2))
        n_agent_synth = needed - n_human_synth

        # Weight toward class with fewer real samples
        if real_counts["human"] < real_counts["agent"]:
            n_human_synth += int(needed * 0.1)
            n_agent_synth = needed - n_human_synth
        else:
            n_agent_synth += int(needed * 0.1)
            n_human_synth = needed - n_agent_synth

        n_human_synth = max(0, n_human_synth)
        n_agent_synth = max(0, n_agent_synth)

        logger.info(f"\n--- Generating synthetic data ---")
        logger.info(f"Synthetic humans needed: {n_human_synth}")
        logger.info(f"Synthetic agents needed: {n_agent_synth}")

        if n_human_synth > 0:
            synths = generate_synthetic_batch(
                n_human_synth, 1, engineer, base_seed=10000
            )
            all_features.extend(synths)
            logger.success(f"  Generated {len(synths)} synthetic humans")

        if n_agent_synth > 0:
            synths = generate_synthetic_batch(
                n_agent_synth, 0, engineer, base_seed=20000
            )
            all_features.extend(synths)
            logger.success(f"  Generated {len(synths)} synthetic agents")

    # --- Assemble DataFrame ---
    feature_df = pd.DataFrame(all_features)
    n_humans = (feature_df["label"] == 1).sum()
    n_agents = (feature_df["label"] == 0).sum()
    n_feature_cols = feature_df.shape[1] - 3  # minus label, source, wallet_address

    logger.success(f"\n{'='*60}")
    logger.success(f"DATASET SUMMARY")
    logger.success(f"{'='*60}")
    logger.success(f"Total samples: {len(feature_df)}")
    logger.success(f"Humans: {n_humans} ({real_counts['human']} real, {n_humans - real_counts['human']} synthetic)")
    logger.success(f"Agents: {n_agents} ({real_counts['agent']} real, {n_agents - real_counts['agent']} synthetic)")
    logger.success(f"Features: {n_feature_cols}")

    # Save
    feature_df.to_parquet(DATASET_PATH, index=False)
    logger.success(f"Saved to {DATASET_PATH}")

    return feature_df


# ---------------------------------------------------------------------------
# STEP 4: Train model
# ---------------------------------------------------------------------------
def train_model():
    """Runs the existing train_model.py script."""
    logger.info("\n" + "=" * 60)
    logger.info("TRAINING MODEL")
    logger.info("=" * 60)

    # Import and run the existing training script's main logic
    # We just need to trigger the same process
    logger.info("Launching train_model.py...")

    # train_model.py reads from interrogator/data/training_data.parquet
    # which we just saved, so we can directly import and call its main()
    import importlib
    train_mod = importlib.import_module("scripts.train_model")
    train_mod.main()


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    build_dataset()
    train_model()
