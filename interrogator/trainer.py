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


def temporal_train_test_split(
    X: np.ndarray,
    y: np.ndarray,
    wallet_ids: np.ndarray,
    test_size: float = 0.2,
    random_state: int = 42,
) -> tuple:
    """
    Splits wallets into train/test by wallet identity, not by row.
    This prevents data leakage from time-series features where
    a wallet's early transactions could leak into test if split by row.

    For full temporal holdout, use temporal_by_block_split() instead.
    This wallet-stratified split is a minimum requirement.
    """
    rng = np.random.default_rng(random_state)
    unique_wallets = np.unique(wallet_ids)
    n_test = max(1, int(len(unique_wallets) * test_size))
    test_wallets = set(rng.choice(unique_wallets, size=n_test, replace=False))

    train_idx = [i for i, w in enumerate(wallet_ids) if w not in test_wallets]
    test_idx = [i for i, w in enumerate(wallet_ids) if w in test_wallets]

    return X[train_idx], X[test_idx], y[train_idx], y[test_idx]


def temporal_by_block_split(
    df: pd.DataFrame,
    feature_cols: list,
    label_col: str = "label",
    wallet_col: str = "wallet_address",
    block_col: str = "latest_block",
    test_ratio: float = 0.2,
) -> tuple:
    """
    True temporal holdout: split wallets by time.
    Train on wallets whose latest activity predates a cutoff.
    Test on wallets whose earliest activity postdates the cutoff.
    This is the gold standard for time-series validation.
    """
    if block_col not in df.columns:
        logger.warning(f"Column '{block_col}' not found. Falling back to random split.")
        return None

    cutoff_block = df[block_col].quantile(1.0 - test_ratio)
    train_df = df[df[block_col] < cutoff_block].copy()
    test_df = df[df[block_col] >= cutoff_block].copy()

    if len(train_df) < 10 or len(test_df) < 5:
        logger.warning(f"Temporal split too small (train={len(train_df)}, test={len(test_df)}). Falling back.")
        return None

    logger.info(f"Temporal split: train={len(train_df)} (pre-block {cutoff_block}), test={len(test_df)}")
    return (
        train_df[feature_cols].values,
        test_df[feature_cols].values,
        train_df[label_col].values,
        test_df[label_col].values,
    )


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
        tx_df = fetcher.fetch_wallet_transactions_adaptive(ghost, min_txs=20, max_txs=300, target_days=30)
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

        temporal_result = None
        wallet_col = "wallet_address" if "wallet_address" in data.columns else None
        if wallet_col and wallet_col in data.columns:
            wallet_ids = data[wallet_col].values if wallet_col in data.columns else np.arange(len(y))
            temporal_result = temporal_by_block_split(
                data, feature_names, label_col=label_col
            )

        if temporal_result is not None:
            X_train, X_val, y_train, y_val = temporal_result
            split_type = "temporal"
        elif wallet_col and wallet_col in data.columns:
            wallet_ids = data[wallet_col].values
            X_train, X_val, y_train, y_val = temporal_train_test_split(
                X, y, wallet_ids, test_size=0.2
            )
            split_type = "wallet_stratified"
        else:
            X_train, X_val, y_train, y_val = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            split_type = "random"

        model = InterrogatorModel(
            models_dir=str(Path(__file__).parent / "models")
        )
        train_metrics = model.train(X_train, y_train, X_val, y_val, feature_names)

        logger.success(
            f"Adversarial retraining v{new_version} complete | "
            f"split={split_type} | train={len(X_train)} | val={len(X_val)} | auc={train_metrics['auc']:.4f}"
        )

        meta_path = Path(__file__).parent / "models" / "model_meta.json"
        try:
            with open(meta_path, "r") as f:
                meta = json.load(f)
            meta["split_type"] = split_type
            meta["train_count"] = len(X_train)
            meta["val_count"] = len(X_val)
            meta["auc"] = train_metrics["auc"]
            with open(meta_path, "w") as f:
                json.dump(meta, f, indent=2)
        except Exception:
            pass

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
