#!/usr/bin/env python3
"""
Retrain the XGBoost model with real wallet data merged into synthetic training set.
Then re-score ghost agent and re-run validation.

Pipeline:
  1. Load 300 synthetic wallets (interrogator/data/training_data.parquet)
  2. For each scorable real wallet in validation/wallets.csv:
       fetch txs → compute 47 features → append to dataset
  3. Retrain model from scratch (saves to interrogator/models/)
  4. Score ghost agent on testnet with new model
  5. Run validation/run_validation.py (uses new model from disk)
  6. Print before/after comparison
"""

import sys, os, time, json, csv, subprocess
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import pandas as pd
from loguru import logger
from dotenv import load_dotenv
from sklearn.model_selection import train_test_split

from data_pipeline.feature_engineer import BehavioralFeatureEngineer
from data_pipeline.preprocessing import FeaturePreprocessor
from data_pipeline.mantle_fetcher import MantleDataFetcher
from interrogator.model import InterrogatorModel
from scorers.dimension_scorer import DimensionScorer, hybrid_hps

load_dotenv()
logger.remove()
logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{level:8s}</level> | <level>{message}</level>")

SYNTHETIC_PATH = "interrogator/data/training_data.parquet"
MODELS_DIR = "interrogator/models"
CSV_PATH = "validation/wallets.csv"
MAINNET_RPC = "https://rpc.mantle.xyz"
TESTNET_RPC = "https://rpc.sepolia.mantle.xyz"
GHOST_ADDR = "0xfdaE6B5f5A8802e47c48dEa56157406c5a54C700"


# ── 1. Load synthetic training data ────────────────────────────────
def load_synthetic():
    df = pd.read_parquet(SYNTHETIC_PATH)
    logger.info(f"Synthetic data: {len(df)} wallets ({int((df.label==1).sum())}H / {int((df.label==0).sum())}B)")
    return df


# ── 2. Extract feature vectors from real wallets ───────────────────
def extract_real_features(csv_path):
    rows = []
    with open(csv_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            rows.append(next(csv.reader([line])))
    meta = pd.DataFrame(rows[1:], columns=["address","chain","label","confidence","source","evidence_link","notes"])
    meta["label"] = pd.to_numeric(meta["label"], errors="coerce")
    meta = meta.dropna(subset=["label"])

    mainnet = meta[meta.chain == "mantle"]
    testnet = meta[meta.chain == "mantle_sepolia"]

    mainnet_fetcher = MantleDataFetcher(MAINNET_RPC)
    testnet_fetcher = MantleDataFetcher(TESTNET_RPC)
    engineer = BehavioralFeatureEngineer()

    records = []
    ok = 0
    skip = 0

    def process(addr, label, fetcher, source_tag):
        nonlocal ok, skip
        addr = addr.strip().lower()
        try:
            df_tx = fetcher.fetch_wallet_transactions_adaptive(addr, min_txs=50, max_txs=500, target_days=90)
            feats = engineer.compute_all_features(df_tx, addr)
            feats["label"] = int(label)
            feats["wallet_address"] = addr
            feats["source"] = f"real_{source_tag}"
            records.append(feats)
            ok += 1
            logger.success(f"  {addr[:10]}... label={int(label)} OK")
        except Exception as e:
            skip += 1
            logger.warning(f"  {addr[:10]}... SKIP: {e}")
        time.sleep(0.2)

    for _, r in mainnet.iterrows():
        process(r.address, r.label, mainnet_fetcher, r.source)
    for _, r in testnet.iterrows():
        process(r.address, r.label, testnet_fetcher, r.source)

    logger.info(f"Real wallets: {ok} OK, {skip} skipped")
    return pd.DataFrame(records) if records else pd.DataFrame()


# ── 3. Retrain model ───────────────────────────────────────────────
def retrain(df_combined, save_dir):
    logger.info(f"Training set: {len(df_combined)} wallets ({int((df_combined.label==1).sum())}H / {int((df_combined.label==0).sum())}B)")

    preprocessor = FeaturePreprocessor(save_dir)
    X, y = preprocessor.fit_transform(df_combined)
    fn = preprocessor.feature_names

    X_t, X_te, y_t, y_te = train_test_split(X, y, test_size=0.15, random_state=42, stratify=y)
    X_tr, X_v, y_tr, y_v = train_test_split(X_t, y_t, test_size=0.176, random_state=42, stratify=y_t)
    logger.info(f"  Train={len(X_tr)} Val={len(X_v)} Test={len(X_te)}")

    model = InterrogatorModel(save_dir)
    val_metrics = model.train(X_tr, y_tr, X_v, y_v, fn)
    test_metrics = model._evaluate(X_te, y_te)

    logger.success(f"  Val AUC: {val_metrics['auc']:.4f}  Test AUC: {test_metrics['auc']:.4f}  Test Acc: {test_metrics['accuracy']:.4f}")
    return model, preprocessor, fn


# ── 4. Score ghost agent ───────────────────────────────────────────
def score_ghost(model, preprocessor, feature_names):
    fetcher = MantleDataFetcher(TESTNET_RPC)
    engineer = BehavioralFeatureEngineer()
    dim_scorer = DimensionScorer()

    df_tx = fetcher.fetch_wallet_transactions_adaptive(GHOST_ADDR, min_txs=50, max_txs=500, target_days=90)
    feats = engineer.compute_all_features(df_tx, GHOST_ADDR)
    X = preprocessor.transform(feats)
    ml_hps = model.score_wallet(X)
    final_hps, mw, dw, ds = hybrid_hps(ml_hps=ml_hps, features=feats, dim_scorer=dim_scorer, block_time=2.0)
    logger.success(f"Ghost HPS={final_hps}  ML_HPS={ml_hps}")
    return final_hps, ml_hps


# ── Main ───────────────────────────────────────────────────────────
def main():
    logger.info("=" * 56)
    logger.info("RETRAINING: Synthetic + Real Data")
    logger.info("=" * 56)

    # BEFORE metrics
    before = {"ghost_hps": None, "auc": None, "acc": None, "prec": None, "rec": None, "f1": None}
    if os.path.exists("validation/results/metrics.json"):
        with open("validation/results/metrics.json") as f:
            m = json.load(f)
            before["auc"] = m.get("auc_roc")
            before["acc"] = m.get("accuracy")
            before["prec"] = m.get("precision")
            before["rec"] = m.get("recall")
            before["f1"] = m.get("f1")

    if os.path.exists("validation/results/per_wallet_scores.csv"):
        df_old = pd.read_csv("validation/results/per_wallet_scores.csv")
        ghost_row = df_old[df_old.address.str.contains("fdae", na=False)]
        if len(ghost_row):
            before["ghost_hps"] = int(ghost_row.iloc[0].hps)

    logger.info(f"BEFORE: Ghost HPS={before['ghost_hps']}  AUC={before['auc']}  Acc={before['acc']}")

    # Step 1: Load synthetic
    logger.info("")
    logger.info("--- [1/4] Loading synthetic data ---")
    df_syn = load_synthetic()

    # Step 2: Extract real wallet features
    logger.info("")
    logger.info("--- [2/4] Extracting real wallet features ---")
    df_real = extract_real_features(CSV_PATH)

    # Step 3: Merge & retrain
    logger.info("")
    logger.info("--- [3/4] Merging & retraining ---")
    # Align feature columns
    feat_cols = [c for c in df_syn.columns if c not in ("label", "source", "wallet_address")]
    for c in feat_cols:
        if c not in df_real.columns:
            df_real[c] = 0.0
    common = [c for c in feat_cols if c in df_real.columns]
    df_syn_a = df_syn[common + ["label"]].copy()
    df_syn_a["wallet_address"] = "synthetic"
    df_syn_a["source"] = "synthetic"
    df_real_a = df_real[common + ["label", "wallet_address", "source"]].copy()
    df_combined = pd.concat([df_syn_a, df_real_a], ignore_index=True)
    logger.info(f"Combined: {len(df_combined)} total ({len(df_syn)} synthetic + {len(df_real)} real)")

    model, preprocessor, fn = retrain(df_combined, MODELS_DIR)

    # Step 4: Score ghost
    logger.info("")
    logger.info("--- [4/4] Scoring ghost agent ---")
    after_ghost_hps, after_ml_hps = score_ghost(model, preprocessor, fn)

    # Step 5: Run validation script
    logger.info("")
    logger.info("--- Running validation pipeline ---")
    result = subprocess.run(
        [sys.executable, "validation/run_validation.py"],
        capture_output=True, text=True, timeout=600,
        env={**os.environ, "PYTHONUTF8": "1"}
    )
    print(result.stdout[-3000:] if len(result.stdout) > 3000 else result.stdout)

    # AFTER metrics
    after = {"ghost_hps": after_ghost_hps, "auc": None, "acc": None, "prec": None, "rec": None, "f1": None}
    if os.path.exists("validation/results/metrics.json"):
        with open("validation/results/metrics.json") as f:
            m = json.load(f)
            after["auc"] = m.get("auc_roc")
            after["acc"] = m.get("accuracy")
            after["prec"] = m.get("precision")
            after["rec"] = m.get("recall")
            after["f1"] = m.get("f1")

    # Comparison
    logger.info("")
    logger.info("=" * 56)
    logger.info("BEFORE  vs  AFTER  COMPARISON")
    logger.info("=" * 56)
    h = f"{'Metric':>20s} {'BEFORE':>10s} {'AFTER':>10s} {'Δ':>8s}"
    logger.info(h)
    logger.info("-" * 50)
    for k in ["ghost_hps", "auc", "acc", "prec", "rec", "f1"]:
        bv = before.get(k)
        av = after.get(k)
        if bv is not None and av is not None:
            delta = av - bv
            logger.info(f"{k:>20s} {bv:>10.4f} {av:>10.4f} {delta:>+8.4f}")
        elif bv is None and av is not None:
            logger.info(f"{k:>20s} {'N/A':>10s} {av:>10.4f} {'NEW':>8s}")
        elif bv is not None:
            logger.info(f"{k:>20s} {bv:>10.4f} {'N/A':>10s}")

    logger.info(f"\nTraining data:")
    logger.info(f"  Before: 300 synthetic ({int((df_syn.label==1).sum())}H/{int((df_syn.label==0).sum())}B)")
    logger.info(f"  After:  {len(df_combined)} ({int((df_combined.label==1).sum())}H/{int((df_combined.label==0).sum())}B) [+{len(df_real)} real]")
    logger.success("Done. Check validation/results/metrics.json for full after-training metrics.")


if __name__ == "__main__":
    main()
