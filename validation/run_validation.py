#!/usr/bin/env python3
"""
Validation runner for Turing Protocol.
Scores every wallet in wallets.csv through the full scoring pipeline,
computes AUC-ROC, accuracy, precision/recall/F1 at threshold=7000.
Handles both Mantle mainnet and Sepolia testnet wallets.
"""

import csv
import os
import sys
import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from loguru import logger
from tqdm import tqdm

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from interrogator.scorer import WalletScorer
from data_pipeline.mantle_fetcher import MantleDataFetcher

load_dotenv()


def load_wallets(csv_path: str) -> pd.DataFrame:
    rows = []
    with open(csv_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            row = next(csv.reader([line]))
            rows.append(row)
    if not rows:
        return pd.DataFrame(columns=["address", "chain", "label", "confidence", "source", "evidence_link", "notes"])
    df = pd.DataFrame(
        rows[1:], columns=["address", "chain", "label", "confidence", "source", "evidence_link", "notes"]
    )
    df["label"] = pd.to_numeric(df["label"], errors="coerce")
    return df


def compute_metrics(y_true: List[int], y_scores: List[int], threshold: int = 7000) -> Dict:
    from sklearn.metrics import (
        roc_auc_score, accuracy_score, precision_score,
        recall_score, f1_score, roc_curve, confusion_matrix,
    )
    y_true_arr = np.array(y_true)
    y_prob_arr = np.array(y_scores) / 10000.0
    y_pred_arr = (np.array(y_scores) >= threshold).astype(int)

    n_classes = len(set(y_true_arr))
    if n_classes < 2:
        # Single class — compute accuracy, but AUC not defined
        cm_raw = confusion_matrix(y_true_arr, y_pred_arr)
        accuracy = accuracy_score(y_true_arr, y_pred_arr)
        precision = precision_score(y_true_arr, y_pred_arr, zero_division=0)
        recall = recall_score(y_true_arr, y_pred_arr, zero_division=0)
        f1 = f1_score(y_true_arr, y_pred_arr, zero_division=0)
        # Build 2x2 matrix manually from single-class
        is_bot = int(y_true_arr[0] == 0)
        cm = [[0, 0], [0, 0]]
        if is_bot:
            cm[0][0] = int(cm_raw[0][0]) if len(cm_raw) > 0 and len(cm_raw[0]) > 0 else 1
            cm[1][1] = 0
        else:
            cm[1][1] = int(cm_raw[0][0]) if len(cm_raw) > 0 and len(cm_raw[0]) > 0 else 1
            cm[0][0] = 0
        return {
            "auc_roc": None,
            "accuracy": float(accuracy),
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
            "threshold": threshold,
            "confusion_matrix": cm,
            "fpr": [],
            "tpr": [],
            "n_total": len(y_true_arr),
            "n_bot": int((y_true_arr == 0).sum()),
            "n_human": int((y_true_arr == 1).sum()),
            "note": "Single class in y_true - AUC not defined",
        }

    auc = roc_auc_score(y_true_arr, y_prob_arr)
    accuracy = accuracy_score(y_true_arr, y_pred_arr)
    precision = precision_score(y_true_arr, y_pred_arr, zero_division=0)
    recall = recall_score(y_true_arr, y_pred_arr, zero_division=0)
    f1 = f1_score(y_true_arr, y_pred_arr, zero_division=0)
    cm = confusion_matrix(y_true_arr, y_pred_arr)
    fpr, tpr, _ = roc_curve(y_true_arr, y_prob_arr)

    return {
        "auc_roc": float(auc),
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "threshold": threshold,
        "confusion_matrix": cm.tolist(),
        "fpr": fpr.tolist(),
        "tpr": tpr.tolist(),
        "n_total": len(y_true_arr),
        "n_bot": int((y_true_arr == 0).sum()),
        "n_human": int((y_true_arr == 1).sum()),
    }


def save_roc_curve(fpr: List[float], tpr: List[float], auc: float, save_path: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.figure(figsize=(8, 6))
    plt.plot(fpr, tpr, color="darkorange", lw=2, label=f"ROC curve (AUC = {auc:.4f})")
    plt.plot([0, 1], [0, 1], color="navy", lw=1, linestyle="--", label="Random (AUC = 0.5)")
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("Receiver Operating Characteristic -> Real-World Validation")
    plt.legend(loc="lower right")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()
    logger.info(f"Saved ROC curve to {save_path}")


def save_confusion_matrix(cm: List[List[int]], save_path: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns
    plt.figure(figsize=(6, 5))
    cm_arr = np.array(cm)
    sns.heatmap(cm_arr, annot=True, fmt="d", cmap="Blues",
                xticklabels=["Bot (Predicted)", "Human (Predicted)"],
                yticklabels=["Bot (True)", "Human (True)"])
    plt.title("Confusion Matrix -> Real-World Validation")
    plt.ylabel("True Label")
    plt.xlabel("Predicted Label")
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()
    logger.info(f"Saved confusion matrix to {save_path}")


def score_wallet_safe(scorer, address: str, max_retries: int = 2) -> Optional[Dict]:
    for attempt in range(max_retries + 1):
        try:
            return scorer.score(address, use_cache=True, return_explanation=False)
        except Exception as e:
            if attempt < max_retries:
                wait = (attempt + 1) * 2
                logger.warning(f"Attempt {attempt+1} failed for {address[:10]}: {e}. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                logger.error(f"All attempts failed for {address[:10]}: {e}")
                return None


def score_batch(scorer, wallets_subset, label_desc):
    """Score a batch of wallets and return results list."""
    results = []
    errors = []
    for _, row in tqdm(wallets_subset.iterrows(), total=len(wallets_subset), desc=label_desc):
        address = row["address"].strip().lower()
        true_label = int(row["label"])
        result = score_wallet_safe(scorer, address)

        if result is None:
            errors.append(address)
            continue

        predicted_label = 1 if result.get("hps", 5000) >= 7000 else 0
        error = result.get("error", None)

        results.append({
            "address": address,
            "chain": row.get("chain", ""),
            "true_label": true_label,
            "hps": result.get("hps", 5000),
            "ml_hps": result.get("ml_hps", 5000),
            "probability": result.get("probability", 0.5),
            "predicted_label": predicted_label,
            "correct": int(predicted_label == true_label),
            "confidence": result.get("confidence", "low"),
            "error": error if error else "",
            "source": row.get("source", ""),
            "notes": row.get("notes", ""),
        })
        time.sleep(0.3)
    return results, errors


def main():
    validation_dir = Path(__file__).resolve().parent
    results_dir = validation_dir / "results"
    csv_path = validation_dir / "wallets.csv"
    results_csv_path = results_dir / "per_wallet_scores.csv"
    roc_png_path = results_dir / "roc_curve.png"
    cm_png_path = results_dir / "confusion_matrix.png"
    results_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load wallets
    logger.info("Loading wallets from CSV...")
    wallets_df = load_wallets(str(csv_path))
    logger.info(f"Loaded {len(wallets_df)} wallet entries")

    labeled = wallets_df[wallets_df["label"].notna()].copy()
    logger.info(f"Labeled wallets: {len(labeled)} (bot={len(labeled[labeled['label']==0])}, "
                f"human={len(labeled[labeled['label']==1])})")

    # 2. Split by chain
    mainnet_wallets = labeled[labeled["chain"].str.contains("mantle", case=False) & ~labeled["chain"].str.contains("sepolia", case=False)]
    testnet_wallets = labeled[labeled["chain"].str.contains("sepolia", case=False)]
    other_wallets = labeled[~labeled["chain"].str.contains("mantle", case=False)]

    logger.info(f"Mainnet wallets: {len(mainnet_wallets)} | Testnet: {len(testnet_wallets)} | Other: {len(other_wallets)}")

    # 3. Score mainnet wallets
    all_results = []
    all_errors = []

    if len(mainnet_wallets) > 0:
        rpc_mainnet = os.getenv("MANTLE_MAINNET_RPC", "https://rpc.mantle.xyz")
        logger.info(f"Initializing mainnet scorer: {rpc_mainnet}")
        try:
            scorer_mainnet = WalletScorer(rpc_mainnet)
            mainnet_results, mainnet_errors = score_batch(scorer_mainnet, mainnet_wallets, "Mainnet")
            all_results.extend(mainnet_results)
            all_errors.extend(mainnet_errors)
        except Exception as e:
            logger.error(f"Mainnet scorer failed: {e}")

    # 4. Score testnet wallets
    if len(testnet_wallets) > 0:
        rpc_testnet = os.getenv("MANTLE_TESTNET_RPC", "https://rpc.sepolia.mantle.xyz")
        logger.info(f"Initializing testnet scorer: {rpc_testnet}")
        try:
            scorer_testnet = WalletScorer(rpc_testnet)
            testnet_results, testnet_errors = score_batch(scorer_testnet, testnet_wallets, "Testnet")
            all_results.extend(testnet_results)
            all_errors.extend(testnet_errors)
        except Exception as e:
            logger.error(f"Testnet scorer failed: {e}")

    # 5. Save results
    if not all_results:
        logger.error("No results obtained!")
        return

    results_df = pd.DataFrame(all_results)
    results_df.to_csv(results_csv_path, index=False)
    logger.info(f"Saved per-wallet scores to {results_csv_path}")

    # 6. Compute metrics
    scorable = results_df[results_df["error"] == ""].copy()
    insufficient = results_df[results_df["error"] != ""].copy()
    fail_count = len(all_errors)

    logger.info(f"Scorable: {len(scorable)} | Insufficient history: {len(insufficient)} | Failures: {fail_count}")

    if len(scorable) < 4:
        logger.warning(f"Only {len(scorable)} scorable wallets -> insufficient for meaningful metrics.")
        metrics = {
            "auc_roc": 0.0, "accuracy": 0.0, "precision": 0.0, "recall": 0.0,
            "f1": 0.0, "threshold": 7000,
            "confusion_matrix": [[0, 0], [0, 0]],
            "fpr": [], "tpr": [],
            "n_total": len(scorable), "n_bot": 0, "n_human": 0,
            "warning": "Insufficient data for meaningful metrics",
        }
    else:
        metrics = compute_metrics(
            y_true=scorable["true_label"].tolist(),
            y_scores=scorable["hps"].tolist(),
            threshold=7000,
        )

    metrics_path = results_dir / "metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    logger.info(f"Saved metrics to {metrics_path}")

    # 7. Generate plots
    if metrics["n_total"] >= 4:
        if metrics["auc_roc"] is not None:
            save_roc_curve(metrics["fpr"], metrics["tpr"], metrics["auc_roc"], str(roc_png_path))
        save_confusion_matrix(metrics["confusion_matrix"], str(cm_png_path))

    # 8. Print summary
    print("=" * 60)
    print("  REAL-WORLD VALIDATION RESULTS")
    print("=" * 60)
    print(f"  Dataset: {metrics['n_total']} scorable wallets "
          f"({metrics['n_bot']} bots, {metrics['n_human']} humans)")
    if fail_count > 0 or len(insufficient) > 0:
        total_attempted = len(results_df) + fail_count
        print(f"  Attempted: {total_attempted} total "
              f"({len(results_df)} scored + {fail_count} failed)")
        if len(insufficient) > 0:
            print(f"  [{len(insufficient)} had insufficient history -> hps=5000 default]")
    if metrics["auc_roc"] is not None:
        print(f"  AUC-ROC:      {metrics['auc_roc']:.4f}")
    else:
        print(f"  AUC-ROC:      N/A (single class in validation set)")
    print(f"  Accuracy:     {metrics['accuracy']:.4f}")
    print(f"  Precision:    {metrics['precision']:.4f}")
    print(f"  Recall:       {metrics['recall']:.4f}")
    print(f"  F1 Score:     {metrics['f1']:.4f}")
    print(f"  Threshold:    {metrics['threshold']}")
    print(f"  Confusion Matrix:")
    cm = metrics["confusion_matrix"]
    print(f"    TN={cm[0][0]}  FP={cm[0][1]}")
    print(f"    FN={cm[1][0]}  TP={cm[1][1]}")
    print(f"  Reference synthetic AUC: 0.8968")
    print("=" * 60)

    # Per-wallet detail
    print(f"\n  {'Address':<46} {'Label':<6} {'HPS':<6} {'Pred':<6} {'Corr':<5} {'Chain':<14} {'Source'}")
    print(f"  {'-'*46} {'-'*6} {'-'*6} {'-'*6} {'-'*5} {'-'*14} {'-'*20}")
    for _, row in scorable.sort_values(["correct", "true_label"], ascending=[True, False]).iterrows():
        print(f"  {row['address'][:42]:<46} "
              f"{'HUMAN' if row['true_label']==1 else 'BOT':<6} "
              f"{row['hps']:<6} "
              f"{'H' if row['predicted_label']==1 else 'B':<6} "
              f"{'->' if row['correct'] else '->':<5} "
              f"{str(row['chain'])[:14]:<14} "
              f"{row['source'][:20]:<20}")

    return metrics


if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    metrics = main()
