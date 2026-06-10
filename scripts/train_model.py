"""
One-command model training.
Run: python scripts/train_model.py

This script:
1. Loads the training dataset from Phase 1
2. Preprocesses and splits the data
3. Runs 5-fold cross-validation
4. Trains final model on full training set
5. Evaluates on holdout test set
6. Saves model artifacts
"""

import sys
sys.path.append(".")

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from loguru import logger
from dotenv import load_dotenv
import os

from data_pipeline.preprocessing import FeaturePreprocessor
from interrogator.model import InterrogatorModel


def main():
    load_dotenv()

    # ── Load Dataset ──────────────────────────────────────
    data_path = "interrogator/data/training_data.parquet"
    logger.info(f"Loading dataset from {data_path}")
    df = pd.read_parquet(data_path)

    logger.info(
        f"Dataset: {len(df)} samples | "
        f"Humans: {df['label'].sum()} | "
        f"Agents: {(df['label']==0).sum()}"
    )

    # ── Preprocess ────────────────────────────────────────
    preprocessor = FeaturePreprocessor()
    X, y = preprocessor.fit_transform(df)
    feature_names = preprocessor.feature_names

    # ── Split ─────────────────────────────────────────────
    # 70% train, 15% validation (early stopping), 15% test (final eval)
    X_temp, X_test, y_temp, y_test = train_test_split(
        X, y, test_size=0.15, random_state=42, stratify=y
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp, test_size=0.176, random_state=42, stratify=y_temp
    )
    # 0.176 of 0.85 ≈ 0.15 of total

    logger.info(
        f"Split: Train={len(X_train)}, Val={len(X_val)}, Test={len(X_test)}"
    )

    # ── Train ─────────────────────────────────────────────
    interrogator = InterrogatorModel()
    train_metrics = interrogator.train(
        X_train, y_train,
        X_val, y_val,
        feature_names
    )

    # ── Final Test Evaluation ─────────────────────────────
    logger.info("Evaluating on holdout test set...")
    test_metrics = interrogator._evaluate(X_test, y_test)

    logger.success(
        f"\nFINAL TEST METRICS\n"
        f"AUC: {test_metrics['auc']:.4f}\n"
        f"Accuracy: {test_metrics['accuracy']:.4f}\n"
        f"Brier Score: {test_metrics['brier_score']:.4f}"
    )

    # ── Example Explanations ──────────────────────────────
    logger.info("Generating example SHAP explanations...")
    for i in range(3):
        sample = X_test[i:i+1]
        score = interrogator.score_wallet(sample)
        contributions = interrogator.explain_wallet(sample, feature_names)
        top3 = contributions[:3]

        logger.info(
            f"Wallet {i+1}: HPS={score} | "
            f"Label={'HUMAN' if y_test[i] else 'AGENT'}\n"
            f"  Top contribution: {top3[0]['feature']} = {top3[0]['contribution']:+.3f}\n"
            f"  2nd: {top3[1]['feature']} = {top3[1]['contribution']:+.3f}\n"
            f"  3rd: {top3[2]['feature']} = {top3[2]['contribution']:+.3f}"
        )


if __name__ == "__main__":
    main()