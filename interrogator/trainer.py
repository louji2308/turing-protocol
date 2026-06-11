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


def load_latest_ghost_data():
    logger.info("Loading latest ghost data for adversarial retraining")
    data_dir = Path(__file__).parent / "data"
    parquet_path = data_dir / "training_data.parquet"
    if parquet_path.exists():
        df = pd.read_parquet(parquet_path)
        logger.info(f"Loaded {len(df)} rows from {parquet_path}")
        return df
    logger.warning("No training_data.parquet found, using empty dataset")
    return pd.DataFrame()


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

        engineer = BehavioralFeatureEngineer()
        preprocessor = FeaturePreprocessor(
            save_dir=str(Path(__file__).parent / "models")
        )

        X, y = preprocessor.fit_transform(data)

        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        model = InterrogatorModel(
            models_dir=str(Path(__file__).parent / "models")
        )
        model.build(X_train, y_train, X_val, y_val)
        model.save()

        logger.success(
            f"Adversarial retraining v{new_version} complete | "
            f"train_size={len(X_train)} | val_size={len(X_val)}"
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
