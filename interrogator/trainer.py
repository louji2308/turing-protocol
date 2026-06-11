import json
import os
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from loguru import logger
from sklearn.model_selection import train_test_split

from interrogator.model import InterrogatorModel
from data_pipeline.feature_engineer import BehavioralFeatureEngineer
from data_pipeline.preprocessing import FeaturePreprocessor
from data_pipeline.mantle_fetcher import MantleDataFetcher


def load_latest_ghost_data(ghost_wallet: str = None) -> pd.DataFrame:
    data_dir = Path(__file__).parent / "data"
    parquet_path = data_dir / "training_data.parquet"
    if parquet_path.exists():
        df = pd.read_parquet(parquet_path)
        logger.info(f"Loaded {len(df)} rows from {parquet_path}")
    else:
        logger.warning("No training_data.parquet found, creating fresh dataset")
        df = pd.DataFrame()

    ghost = ghost_wallet or os.getenv("GHOST_WALLET_ADDRESS")
    if not ghost:
        logger.warning("No ghost wallet configured — skipping ghost data fetch")
        return df

    rpc_url = os.getenv("MANTLE_TESTNET_RPC", "https://rpc.sepolia.mantle.xyz")
    try:
        fetcher = MantleDataFetcher(rpc_url)
        tx_df = fetcher.fetch_wallet_transactions(ghost, max_txs=150)
        if len(tx_df) < 5:
            logger.warning(f"Ghost wallet has only {len(tx_df)} txs — not enough for retraining")
            return df

        engineer = BehavioralFeatureEngineer()
        features = engineer.compute_all_features(tx_df, ghost)
        features["label"] = 0
        features["source"] = "ghost_agent"
        features["wallet_address"] = ghost

        ghost_row = pd.DataFrame([features])
        combined = pd.concat([df, ghost_row], ignore_index=True)

        logger.success(
            f"Ghost data added | ghost_txs={len(tx_df)} | "
            f"total_dataset={len(combined)} | agents={int((combined['label']==0).sum())}"
        )
        return combined

    except Exception as e:
        logger.error(f"Failed to fetch/engineer ghost data: {e}")
        return df


def adversarial_retrain(interrogator, new_version):
    logger.warning(f"Adversarial retraining to version {new_version}")
    data = load_latest_ghost_data()
    if len(data) < 50:
        logger.warning(f"Insufficient data ({len(data)} rows) for retraining, skipping")
        return

    try:
        label_col = "label" if "label" in data.columns else "is_agent"
        if label_col not in data.columns:
            logger.warning("No label column found, using default labeling")
            data[label_col] = 0

        preprocessor = FeaturePreprocessor(
            save_dir=str(Path(__file__).parent / "models")
        )
        X, y = preprocessor.fit_transform(data)
        feature_names = preprocessor.feature_names

        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        model = InterrogatorModel(
            models_dir=str(Path(__file__).parent / "models")
        )
        train_metrics = model.train(X_train, y_train, X_val, y_val, feature_names)

        logger.success(
            f"Adversarial retraining v{new_version} complete | "
            f"train={len(X_train)} | val={len(X_val)} | auc={train_metrics['auc']:.4f}"
        )
    except Exception as e:
        logger.error(f"Adversarial retraining failed: {e}")
        raise


def save_model(interrogator, model_path):
    model_dir = Path(model_path).parent
    model_dir.mkdir(parents=True, exist_ok=True)

    src_dir = Path(__file__).parent / "models"
    for f in ["interrogator.joblib", "explainer.joblib", "scaler.joblib", "feature_names.json"]:
        src = src_dir / f
        if src.exists():
            dst = model_dir / f
            import shutil
            shutil.copy2(str(src), str(dst))
            logger.info(f"Copied {f} to {model_path}")
        else:
            logger.warning(f"Model file {f} not found at {src}")

    meta = {
        "version": Path(model_path).stem.split("_v")[-1] if "_v" in model_path else "unknown",
        "saved_at": str(pd.Timestamp.now()),
        "source": str(src_dir),
    }
    meta_path = model_dir / "model_meta.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
