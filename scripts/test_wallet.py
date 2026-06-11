import sys; sys.path.insert(0, '.')
import os, json, joblib
import pandas as pd
import numpy as np
from dotenv import load_dotenv
load_dotenv()

from data_pipeline.mantle_fetcher import MantleDataFetcher
from data_pipeline.feature_engineer import BehavioralFeatureEngineer
from interrogator.model import InterrogatorModel

# Config
RPC_URL = os.getenv("MANTLE_TESTNET_RPC", "https://rpc.sepolia.mantle.xyz")
WALLETS = [
    os.getenv("GHOST_WALLET_ADDRESS", "").strip(),       # your wallet
    "0xDeaDDEaDDeAdDeAdDEAdDEaddeAddEAdDEAd0001",       # dead address
]

model = InterrogatorModel()
model.load()

scaler = joblib.load("interrogator/models/scaler.joblib")
with open("interrogator/models/feature_names.json") as f:
    feature_names = json.load(f)

engineer = BehavioralFeatureEngineer()
fetcher = MantleDataFetcher(RPC_URL)

for addr in WALLETS:
    if not addr: continue
    print(f"\n--- {addr[:10]}... ---")
    df = fetcher.fetch_wallet_transactions(addr, max_txs=200)
    if df is None or len(df) < 10:
        print(f"  Only {len(df) if df is not None else 0} txs — need 10+")
        continue

    features = engineer.compute_all_features(df, addr)
    X = pd.DataFrame([features])[feature_names].fillna(0)
    X_scaled = scaler.transform(X)

    hps = model.score_wallet(X_scaled)
    label = "HUMAN" if hps > 5000 else "AGENT"
    print(f"  Txs: {len(df)} | HPS: {hps}/10000 -> {label}")

    contribs = model.explain_wallet(X_scaled, feature_names)
    print(f"  Top features:")
    for c in contribs[:5]:
        direction = "+HUMAN" if c["direction"] == "human" else "+AGENT"
        print(f"    {c['feature']}: {c['value']:.4f} ({direction} {c['contribution']:+.3f})")
