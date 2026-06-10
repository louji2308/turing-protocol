"""
Fetches real wallet transactions and combines them with synthetic data.
This gives the model real blockchain patterns instead of purely synthetic.

Usage:
  1. Replace the addresses below with wallets you know are human or agent
  2. Run: python fetch_real_wallets.py
  3. Train: python scripts/train_model.py
"""
import sys; sys.path.insert(0, '.')
import os
import numpy as np
import pandas as pd
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv
from data_pipeline.mantle_fetcher import MantleDataFetcher
from data_pipeline.feature_engineer import BehavioralFeatureEngineer
from scripts.generate_training_data import make_synthetic_wallet_df

load_dotenv()

# ====== STEP 1: Put your known wallet addresses here ======
# "human" = wallets YOU control and trade manually
# "agent" = wallets YOU deployed as bots
HUMAN_ADDRESSES = [
    "0xfdaE6B5f5A8802e47c48dEa56157406c5a54C700",  # Your ghost wallet
]

AGENT_ADDRESSES = [
    # Add bot wallet addresses here after you deploy them
]

# ====== STEP 2: Fetch real data ======
rpc = os.getenv("MANTLE_TESTNET_RPC")
fetcher = MantleDataFetcher(rpc)
engineer = BehavioralFeatureEngineer()

all_features = []
all_labels = []

for addr in HUMAN_ADDRESSES:
    try:
        df = fetcher.fetch_wallet_transactions(addr, max_txs=150)
        if len(df) >= 20:
            feats = engineer.compute_all_features(df, addr)
            all_features.append(feats)
            all_labels.append(1)
            logger.success(f"Fetched human: {addr[:10]} ({len(df)} txs)")
        else:
            logger.warning(f"Too few txs for {addr[:10]}: {len(df)}")
    except Exception as e:
        logger.warning(f"Failed human {addr[:10]}: {e}")

for addr in AGENT_ADDRESSES:
    try:
        df = fetcher.fetch_wallet_transactions(addr, max_txs=150)
        if len(df) >= 20:
            feats = engineer.compute_all_features(df, addr)
            all_features.append(feats)
            all_labels.append(0)
            logger.success(f"Fetched agent: {addr[:10]} ({len(df)} txs)")
    except Exception as e:
        logger.warning(f"Failed agent {addr[:10]}: {e}")

# ====== STEP 3: Fill remaining with synthetic data ======
target_total = 300
needed = target_total - len(all_features)

if needed > 0:
    n_human_synthetic = int(needed * 0.45)  # ~45% humans
    n_agent_synthetic = needed - n_human_synthetic

    logger.info(f"Adding {needed} synthetic wallets ({n_human_synthetic} human, {n_agent_synthetic} agent)")

    for i in range(n_human_synthetic):
        human_strength = np.random.default_rng(i*7+13).beta(0.5, 0.5)
        if human_strength < 0.5:
            human_strength = 1.0 - human_strength  # ensure > 0.5
        n_txs = np.random.default_rng(i*7+13).integers(40, 130)
        df, addr = make_synthetic_wallet_df(n=n_txs, seed=i*7+13, human_strength=human_strength)
        try:
            feats = engineer.compute_all_features(df, addr)
            all_features.append(feats)
            all_labels.append(1)
        except:
            pass

    for i in range(n_agent_synthetic):
        human_strength = np.random.default_rng(i*7+5000).beta(0.5, 0.5)
        if human_strength > 0.5:
            human_strength = 1.0 - human_strength  # ensure < 0.5
        n_txs = np.random.default_rng(i*7+5000).integers(40, 130)
        df, addr = make_synthetic_wallet_df(n=n_txs, seed=i*7+5000, human_strength=human_strength)
        try:
            feats = engineer.compute_all_features(df, addr)
            all_features.append(feats)
            all_labels.append(0)
        except:
            pass

# ====== STEP 4: Save ======
feature_df = pd.DataFrame(all_features)
feature_df['label'] = all_labels

n_real = len(HUMAN_ADDRESSES) + len(AGENT_ADDRESSES)
logger.success(f"Dataset: {sum(all_labels)} humans, {len(all_labels)-sum(all_labels)} agents ({n_real} real, {len(all_features)-n_real} synthetic)")

out_path = Path("interrogator/data/training_data.parquet")
out_path.parent.mkdir(parents=True, exist_ok=True)
feature_df.to_parquet(out_path, index=False)
logger.success(f"Saved to {out_path}")
