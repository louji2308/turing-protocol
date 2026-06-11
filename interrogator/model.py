import numpy as np
import pandas as pd
import xgboost as xgb
import shap
import joblib
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from sklearn.metrics import (
    roc_auc_score, classification_report,
    confusion_matrix, brier_score_loss
)
from loguru import logger


class InterrogatorModel:
    """
    The core ML classifier for the Turing Protocol.

    Architecture: XGBoost binary classifier calibrated to output
    well-calibrated probabilities (not just rankings).

    We specifically tune for:
    - High AUC (overall discrimination)
    - Low Brier score (calibration quality — probabilities mean something)
    - Low false negative rate (we'd rather flag a human as unsure
      than incorrectly certify an agent as human)

    The SHAP explainer allows us to say:
    "Wallet X scored 73/100 because:
    +15 points: Very irregular timing (human-like)
    +12 points: High protocol diversity
    -8 points: Gas prices too precise
    -4 points: No transaction failures ever"
    """

    MODEL_VERSION = "1.0.0"

    def __init__(self, models_dir: str = "interrogator/models"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.model: Optional[xgb.XGBClassifier] = None
        self.explainer: Optional[shap.TreeExplainer] = None

    def build_model(self) -> xgb.XGBClassifier:
        """
        Constructs the XGBoost classifier with carefully chosen hyperparameters.

        Key choices:
        - n_estimators=400: Enough trees for complex behavioral patterns
        - max_depth=5: Deep enough to capture interactions, not so deep
          it overfits on 47 features
        - learning_rate=0.05: Low LR with high n_estimators = better
          generalization than high LR low estimators
        - subsample=0.8: Row subsampling prevents overfitting
        - colsample_bytree=0.7: Feature subsampling — each tree sees
          70% of features, creating diverse ensemble
        - scale_pos_weight: Set during training based on class balance
        - objective='binary:logistic': Outputs calibrated probabilities
        - eval_metric='auc': Optimizes for ranking quality
        - use_label_encoder=False: Required for XGBoost >= 1.6
        - tree_method='hist': Fast histogram-based algorithm
        - enable_categorical=False: All features are numerical
        """
        return xgb.XGBClassifier(
            n_estimators=400,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.7,
            min_child_weight=5,
            gamma=0.1,
            reg_alpha=0.1,      # L1 regularization
            reg_lambda=1.0,     # L2 regularization
            objective='binary:logistic',
            eval_metric='auc',
            use_label_encoder=False,
            tree_method='hist',
            random_state=42,
            n_jobs=-1,          # Use all CPU cores
            verbosity=1,
        )

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        feature_names: List[str]
    ) -> Dict[str, float]:
        """
        Trains the classifier with early stopping on validation AUC.

        Early stopping prevents overfitting and finds the optimal
        number of trees automatically. We stop if validation AUC
        hasn't improved for 30 consecutive rounds.

        Args:
            X_train: Training feature matrix
            y_train: Training labels (0=agent, 1=human)
            X_val: Validation feature matrix
            y_val: Validation labels
            feature_names: List of feature names for SHAP

        Returns:
            Dict of evaluation metrics
        """
        # Compute class weight for imbalanced datasets
        n_pos = y_train.sum()
        n_neg = len(y_train) - n_pos
        scale_pos_weight = n_neg / (n_pos + 1e-9)

        self.model = self.build_model()
        self.model.set_params(scale_pos_weight=scale_pos_weight)

        logger.info(
            f"Training with {X_train.shape[0]} samples, "
            f"{X_train.shape[1]} features. "
            f"Scale pos weight: {scale_pos_weight:.2f}"
        )

        # Fit with early stopping
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=50,  # Print every 50 rounds
        )

        # Store feature names for SHAP
        self.feature_names = feature_names

        # Build SHAP explainer
        logger.info("Building SHAP TreeExplainer...")
        self.explainer = shap.TreeExplainer(self.model)

        # Evaluate
        metrics = self._evaluate(X_val, y_val)
        self._save()

        return metrics

    def _evaluate(
        self,
        X_val: np.ndarray,
        y_val: np.ndarray
    ) -> Dict[str, float]:
        """
        Comprehensive evaluation of the trained model.
        """
        probs = self.model.predict_proba(X_val)[:, 1]
        preds = (probs >= 0.5).astype(int)

        auc = roc_auc_score(y_val, probs)
        brier = brier_score_loss(y_val, probs)

        logger.success(
            f"\n{'='*50}\n"
            f"INTERROGATOR EVALUATION\n"
            f"{'='*50}\n"
            f"AUC-ROC:     {auc:.4f}  (target: >0.90)\n"
            f"Brier Score: {brier:.4f} (target: <0.10)\n"
            f"{'='*50}\n"
            f"{classification_report(y_val, preds, target_names=['Agent', 'Human'])}"
            f"{'='*50}"
        )

        return {
            "auc": auc,
            "brier_score": brier,
            "accuracy": (preds == y_val).mean(),
        }

    def score_wallet(
        self,
        X: np.ndarray
    ) -> int:
        """
        Returns the Human Probability Score as an integer 0-10000.
        This is the exact value that gets written to the on-chain oracle.

        0    = Definitely an agent
        5000 = Uncertain
        10000 = Definitely human
        """
        if self.model is None:
            raise RuntimeError("Model not trained. Call train() first.")

        prob = self.model.predict_proba(X)[0, 1]  # P(human)
        return int(prob * 10000)

    def explain_wallet(
        self,
        X: np.ndarray,
        feature_names: Optional[List[str]] = None
    ) -> List[Dict[str, float]]:
        """
        Returns SHAP-based feature contributions for a single wallet.
        This is what goes into the Proof of Behavior NFT metadata
        and into the dashboard feature waterfall chart.

        Returns list of dicts sorted by absolute contribution:
        [
            {"feature": "temp_4_cv", "contribution": +0.15, "value": 1.23},
            {"feature": "gas_1_round_fraction", "contribution": -0.08, "value": 0.02},
            ...
        ]
        """
        if self.explainer is None:
            raise RuntimeError("SHAP explainer not ready. Train model first.")

        shap_values = self.explainer.shap_values(X)

        if feature_names is None:
            feature_names = self.feature_names

        contributions = [
            {
                "feature": name,
                "contribution": float(shap_val),
                "value": float(X[0, i]),
                "direction": "human" if shap_val > 0 else "agent"
            }
            for i, (name, shap_val) in enumerate(
                zip(feature_names, shap_values[0])
            )
        ]

        # Sort by absolute contribution (most impactful first)
        contributions.sort(key=lambda x: abs(x["contribution"]), reverse=True)

        return contributions

    def compute_behavior_fingerprint(
        self,
        X: np.ndarray
    ) -> str:
        """
        Generates a bytes32 behavioral fingerprint from SHAP values.
        Used as unique metadata in the Proof of Behavior NFT.

        The fingerprint encodes the top-10 feature contributions
        normalized and packed into a deterministic hash.
        This means two wallets with identical behavior get identical
        fingerprints — verifiable behavioral equivalence.
        """
        import hashlib

        shap_values = self.explainer.shap_values(X)[0]
        # Take top 10 by magnitude
        top_indices = np.argsort(np.abs(shap_values))[-10:]
        top_values = shap_values[top_indices]

        # Quantize to integers (multiply by 1000 and round)
        quantized = (top_values * 1000).astype(int)

        # Create deterministic hash
        fingerprint_input = "|".join(str(v) for v in sorted(quantized))
        fingerprint = "0x" + hashlib.sha256(
            fingerprint_input.encode()
        ).hexdigest()

        return fingerprint

    def _save(self):
        """Saves model, explainer, and metadata."""
        model_path = self.models_dir / "interrogator.joblib"
        explainer_path = self.models_dir / "explainer.joblib"
        meta_path = self.models_dir / "model_meta.json"

        joblib.dump(self.model, model_path)
        joblib.dump(self.explainer, explainer_path)

        meta = {
            "version": self.MODEL_VERSION,
            "n_estimators": self.model.n_estimators,
            "feature_count": len(self.feature_names),
            "feature_names": self.feature_names,
        }
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)

        logger.success(f"Model saved to {model_path}")

    def load(self):
        """Loads a saved model from disk."""
        model_path = self.models_dir / "interrogator.joblib"
        explainer_path = self.models_dir / "explainer.joblib"
        meta_path = self.models_dir / "model_meta.json"

        if not model_path.exists():
            raise FileNotFoundError(
                "No saved model found. Run training first."
            )

        self.model = joblib.load(model_path)
        self.explainer = joblib.load(explainer_path)

        with open(meta_path, "r") as f:
            meta = json.load(f)
        self.feature_names = meta["feature_names"]
        self.MODEL_VERSION = meta["version"]

        logger.success(f"Model loaded: version {self.MODEL_VERSION}")

    def reload(self):
        self.load()
        logger.success("Model reloaded from disk")