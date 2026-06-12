import json
from pathlib import Path
from typing import Dict, Union, Tuple, List

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import RobustScaler


class FeaturePreprocessor:
    """
    Handles:
    - Missing values
    - Outlier clipping
    - Feature scaling
    - Saving/loading scaler
    - Consistent feature ordering
    """

    def __init__(self, save_dir: str = "interrogator/models"):
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)

        self.scaler = RobustScaler()
        self.feature_names: List[str] = []

    def fit_transform(
        self,
        df: pd.DataFrame
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Train scaler on dataset.
        Returns X, y.
        """

        feature_cols = [
            c for c in df.columns
            if c not in ["label", "source", "wallet_address"]
        ]

        self.feature_names = feature_cols

        X = df[feature_cols].copy()
        y = df["label"].values

        # Fill missing values
        X = X.fillna(X.median(numeric_only=True))

        # Outlier clipping
        for col in feature_cols:
            q1 = X[col].quantile(0.05)
            q99 = X[col].quantile(0.95)

            X[col] = X[col].clip(
                lower=q1 * 0.1,
                upper=q99 * 10
            )

        X_scaled = self.scaler.fit_transform(X)

        # Save scaler
        joblib.dump(
            self.scaler,
            self.save_dir / "scaler.joblib"
        )

        # Save feature order
        with open(
            self.save_dir / "feature_names.json",
            "w"
        ) as f:
            json.dump(self.feature_names, f, indent=2)

        return X_scaled, y

    def transform(
        self,
        features: Union[Dict[str, float], pd.DataFrame]
    ) -> np.ndarray:
        """
        Transform inference input.
        Returns scaled features, or zeros if scaler is unavailable.
        """

        scaler_path = self.save_dir / "scaler.joblib"
        names_path = self.save_dir / "feature_names.json"

        if not scaler_path.exists() or not names_path.exists():
            from loguru import logger
            logger.warning("Scaler or feature names not found. Returning zero features.")
            if isinstance(features, dict):
                return np.zeros((1, len(features)), dtype=np.float64)
            return np.zeros((len(features), len(features.columns)), dtype=np.float64)

        scaler = joblib.load(scaler_path)

        with open(names_path, "r") as f:
            feature_names = json.load(f)

        if isinstance(features, dict):
            X = pd.DataFrame([features])
        else:
            X = features.copy()

        X = X.reindex(
            columns=feature_names,
            fill_value=0.0
        )

        X = X.fillna(0.0)

        return scaler.transform(X)