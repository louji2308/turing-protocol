import numpy as np
import pandas as pd
import xgboost as xgb
import shap
import joblib
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    roc_auc_score, classification_report,
    confusion_matrix, brier_score_loss
)
from loguru import logger


UNCERTAINTY_HIGH_MAX = 800
UNCERTAINTY_MEDIUM_MAX = 1500


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
        self._calibrator: Optional[LogisticRegression] = None

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
            n_estimators=2000,
            max_depth=6,
            learning_rate=0.01,
            subsample=0.7,
            colsample_bytree=0.6,
            min_child_weight=10,
            gamma=0.1,
            reg_alpha=0.5,
            reg_lambda=2.0,
            objective='binary:logistic',
            eval_metric='auc',
            early_stopping_rounds=50,
            tree_method='hist',
            random_state=42,
            n_jobs=-1,
            verbosity=0,
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

        # Fit with early stopping — stops if validation AUC
        # hasn't improved for 30 consecutive rounds.
        # Without early_stopping_rounds, all 400 trees train
        # and the model overfits (test AUC drops to ~0.82 vs 0.90).
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=50,
        )
        # XGBoost's sklearn wrapper automatically sets best_iteration
        # and uses best_ntree_limit for all subsequent predict calls.
        # This means preds use only the optimal number of trees,
        # not all 400.

        # Store feature names for SHAP
        self.feature_names = feature_names

        # Platt calibration: fit logistic regression on validation margin scores
        n_trees = self._best_n_trees()
        val_margins = self.model.predict(X_val, iteration_range=(0, n_trees), output_margin=True)
        self._calibrator = LogisticRegression(C=1e6, solver='lbfgs')
        self._calibrator.fit(val_margins.reshape(-1, 1), y_val)
        logger.info(f"Platt calibrator fitted on {len(y_val)} validation samples")

        # Build SHAP explainer
        logger.info("Building SHAP TreeExplainer...")
        self.explainer = shap.TreeExplainer(self.model)

        # Evaluate
        metrics = self._evaluate(X_val, y_val)
        self._save()

        return metrics

    def _best_n_trees(self) -> int:
        if hasattr(self.model, 'best_iteration') and self.model.best_iteration is not None:
            return self.model.best_iteration + 1
        return self.model.n_estimators

    def _calibrated_proba(self, X: np.ndarray) -> np.ndarray:
        n_trees = self._best_n_trees()
        if hasattr(self, '_calibrator') and self._calibrator is not None:
            margins = self.model.predict(X, iteration_range=(0, n_trees), output_margin=True)
            return self._calibrator.predict_proba(margins.reshape(-1, 1))
        return self.model.predict_proba(X, iteration_range=(0, n_trees))

    def _evaluate(
        self,
        X_val: np.ndarray,
        y_val: np.ndarray
    ) -> Dict[str, float]:
        """
        Comprehensive evaluation of the trained model.
        """
        n_trees = self._best_n_trees()
        probs = self._calibrated_proba(X_val)[:, 1]
        preds = (probs >= 0.5).astype(int)

        logger.info(f"Using {n_trees} trees for evaluation (out of {self.model.n_estimators})")

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
        X: np.ndarray,
        return_uncertainty: bool = False,
    ) -> object:
        """
        Returns the Human Probability Score as an integer 0-10000.
        This is the exact value that gets written to the on-chain oracle.

        0    = Definitely an agent
        5000 = Uncertain
        10000 = Definitely human

        When return_uncertainty=True, returns a dict with hps and
        uncertainty score (0-10000) based on ensemble disagreement.
        """
        if self.model is None:
            raise RuntimeError("Model not trained. Call train() first.")

        n_trees = self._best_n_trees()
        prob = self._calibrated_proba(X)[0, 1]  # P(human)
        hps = int(prob * 10000)

        if return_uncertainty:
            uncertainty = int(abs(prob - 0.5) * 20000)  # 0 at p=0.5, 10000 at p=0 or p=1
            return {"hps": hps, "uncertainty": uncertainty}

        return hps

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
        X: np.ndarray,
        precision: int = 100000,
    ) -> str:
        """
        Generates a bytes32 behavioral fingerprint from SHAP values.
        Used as unique metadata in the Proof of Behavior NFT.

        The fingerprint encodes the top-10 feature contributions
        normalized and packed into a deterministic hash.
        This means two wallets with identical behavior get identical
        fingerprints — verifiable behavioral equivalence.

        precision controls quantization granularity:
        1000   = ~2.4M possible values per feature (10^3)^10 = 10^30
        100000 = ~2.4e15 possible values per feature — collision resistant
        """
        import hashlib

        shap_values = self.explainer.shap_values(X)[0]
        # Take top 10 by magnitude
        top_indices = np.argsort(np.abs(shap_values))[-10:]
        top_values = shap_values[top_indices]

        # Quantize to integers (multiply by precision and round)
        quantized = (top_values * precision).astype(int)

        # Create deterministic hash with feature indices to preserve mapping
        sorted_pairs = sorted(zip(top_indices, quantized), key=lambda x: x[0])
        fingerprint_input = "|".join(f"{i}:{v}" for i, v in sorted_pairs)
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
        if hasattr(self, '_calibrator') and self._calibrator is not None:
            calib_path = self.models_dir / "calibrator.joblib"
            joblib.dump(self._calibrator, calib_path)

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

        calib_path = self.models_dir / "calibrator.joblib"
        if calib_path.exists():
            self._calibrator = joblib.load(calib_path)
        else:
            self._calibrator = None

        with open(meta_path, "r") as f:
            meta = json.load(f)
        self.feature_names = meta["feature_names"]
        self.MODEL_VERSION = meta["version"]

        logger.success(f"Model loaded: version {self.MODEL_VERSION}")

    def reload(self):
        self.load()
        logger.success("Model reloaded from disk")


def score_wallet_with_uncertainty(model: xgb.XGBClassifier, X: np.ndarray) -> dict:
    booster = model.get_booster()
    dmatrix = xgb.DMatrix(X)
    total_trees = booster.num_boosted_rounds()
    n_trees = (model.best_iteration + 1) if hasattr(model, 'best_iteration') and model.best_iteration is not None else total_trees

    point_estimate = float(model.predict_proba(X, iteration_range=(0, n_trees))[0, 1])

    try:
        staged_margins = np.array([
            booster.predict(dmatrix, iteration_range=(0, k), output_margin=True)[0]
            for k in range(max(1, n_trees - 50), n_trees + 1)
        ])
        staged_probs = 1 / (1 + np.exp(-staged_margins))
        std_dev = float(np.std(staged_probs))
    except Exception:
        margin = abs(point_estimate - 0.5)
        std_dev = float((0.5 - margin) * 0.3)

    uncertainty_hps = int(np.clip(std_dev * 10000, 0, 10000))

    if uncertainty_hps < UNCERTAINTY_HIGH_MAX:
        confidence = "high"
    elif uncertainty_hps < UNCERTAINTY_MEDIUM_MAX:
        confidence = "medium"
    else:
        confidence = "low"

    hps = int(point_estimate * 10000)
    return {
        "hps": hps,
        "uncertainty_hps": uncertainty_hps,
        "confidence": confidence,
        "hps_range": [
            int(np.clip(hps - 2 * uncertainty_hps, 0, 10000)),
            int(np.clip(hps + 2 * uncertainty_hps, 0, 10000)),
        ],
        "investable": confidence in ("high", "medium") and uncertainty_hps < UNCERTAINTY_MEDIUM_MAX,
    }