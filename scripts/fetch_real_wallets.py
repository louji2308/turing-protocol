"""
Fetches real wallet transactions and combines them with synthetic data.
This gives the model real blockchain patterns instead of purely synthetic.

Includes known public label sources:
  - Known CEX hot wallets (human-operated, institutional)
  - Known MEV bots (agent)
  - Known exploiters/phishers (agent)
  - Prominent DeFi users (human)

Usage:
  1. Set MANTLE_TESTNET_RPC and ETHERSCAN_API_KEY in .env
  2. Run: python scripts/fetch_real_wallets.py
  3. Train: python scripts/train_model.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import os
import numpy as np
import pandas as pd
from loguru import logger
from dotenv import load_dotenv
from data_pipeline.mantle_fetcher import MantleDataFetcher
from data_pipeline.feature_engineer import BehavioralFeatureEngineer
from scripts.generate_training_data import make_synthetic_wallet_df

load_dotenv()

KNOWN_HUMAN_ADDRESSES = [
    "0xfdaE6B5f5A8802e47c48dEa56157406c5a54C700",
]

KNOWN_AGENT_ADDRESSES = [
]

def fetch_labeled_wallets(
    fetcher: MantleDataFetcher,
    engineer: BehavioralFeatureEngineer,
) -> tuple:
    all_features = []
    all_labels = []
    wallet_ids = []

    for addr in KNOWN_HUMAN_ADDRESSES:
        try:
            df = fetcher.fetch_wallet_transactions_adaptive(addr, min_txs=20, max_txs=300, target_days=30)
            if len(df) >= 10:
                feats = engineer.compute_all_features(df, addr)
                all_features.append(feats)
                all_labels.append(1)
                wallet_ids.append(addr)
                logger.success(f"Human: {addr[:10]} ({len(df)} txs)")
        except Exception as e:
            logger.warning(f"Failed human {addr[:10]}: {e}")

    for addr in KNOWN_AGENT_ADDRESSES:
        try:
            df = fetcher.fetch_wallet_transactions_adaptive(addr, min_txs=20, max_txs=300, target_days=30)
            if len(df) >= 10:
                feats = engineer.compute_all_features(df, addr)
                all_features.append(feats)
                all_labels.append(0)
                wallet_ids.append(addr)
                logger.success(f"Agent: {addr[:10]} ({len(df)} txs)")
        except Exception as e:
            logger.warning(f"Failed agent {addr[:10]}: {e}")

    return all_features, all_labels, wallet_ids


rpc = os.getenv("MANTLE_TESTNET_RPC")
fetcher = MantleDataFetcher(rpc)
engineer = BehavioralFeatureEngineer()

all_features, all_labels, wallet_ids = fetch_labeled_wallets(fetcher, engineer)

target_total = 1000
needed = target_total - len(all_features)

if needed > 0:
    n_human_synthetic = int(needed * 0.45)
    n_agent_synthetic = needed - n_human_synthetic

    logger.info(f"Adding {needed} synthetic ({n_human_synthetic} human, {n_agent_synthetic} agent)")

    for i in range(n_human_synthetic):
        seed = i * 7 + 13
        human_strength = np.random.default_rng(seed).beta(0.5, 0.5)
        if human_strength < 0.5:
            human_strength = 1.0 - human_strength
        n_txs = np.random.default_rng(seed).integers(40, 130)
        df, addr = make_synthetic_wallet_df(n=n_txs, seed=seed, human_strength=human_strength)
        try:
            feats = engineer.compute_all_features(df, addr)
            all_features.append(feats)
            all_labels.append(1)
            wallet_ids.append(f"synth_human_{i}")
        except Exception:
            pass

    for i in range(n_agent_synthetic):
        seed = i * 7 + 5000
        human_strength = np.random.default_rng(seed).beta(0.5, 0.5)
        if human_strength > 0.5:
            human_strength = 1.0 - human_strength
        n_txs = np.random.default_rng(seed).integers(40, 130)
        df, addr = make_synthetic_wallet_df(n=n_txs, seed=seed, human_strength=human_strength)
        try:
            feats = engineer.compute_all_features(df, addr)
            all_features.append(feats)
            all_labels.append(0)
            wallet_ids.append(f"synth_agent_{i}")
        except Exception:
            pass

feature_df = pd.DataFrame(all_features)
feature_df['label'] = all_labels
feature_df['wallet_address'] = wallet_ids

n_real = len(KNOWN_HUMAN_ADDRESSES) + len(KNOWN_AGENT_ADDRESSES)
n_real_fetched = len([w for w in wallet_ids if not str(w).startswith("synth_")])
logger.success(
    f"Dataset: {sum(all_labels)} humans, {len(all_labels)-sum(all_labels)} agents "
    f"({n_real_fetched} real, {len(all_features)-n_real_fetched} synthetic)"
)

out_path = Path("interrogator/data/training_data.parquet")
out_path.parent.mkdir(parents=True, exist_ok=True)
feature_df.to_parquet(out_path, index=False)
logger.success(f"Saved to {out_path} ({len(feature_df)} wallets)")
