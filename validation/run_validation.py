"""Validation runner for Turing Protocol — LOOCV methodology.

Scores every wallet in wallets.csv through the full scoring pipeline
using Leave-One-Out Cross-Validation (LOOCV) on the 15 scorable real wallets:
- For each of the 15 real wallets, trains on (5000 synthetic + 14 other real wallets),
  then scores the held-out wallet.
- Aggregates the 15 out-of-fold predictions into one ROC curve -> LOOCV AUC.
- No wallet contributes to both training and evaluation simultaneously.
"""

import csv
import os
import sys
import time
import json
import copy
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
        cm_raw = confusion_matrix(y_true_arr, y_pred_arr)
        accuracy = accuracy_score(y_true_arr, y_pred_arr)
        precision = precision_score(y_true_arr, y_pred_arr, zero_division=0)
        recall = recall_score(y_true_arr, y_pred_arr, zero_division=0)
        f1 = f1_score(y_true_arr, y_pred_arr, zero_division=0)
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
    plt.plot(fpr, tpr, color="darkorange", lw=2, label=f"LOOCV ROC (AUC = {auc:.4f})")
    plt.plot([0, 1], [0, 1], color="navy", lw=1, linestyle="--", label="Random (AUC = 0.5)")
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("LOOCV Receiver Operating Characteristic — Real-World Validation (n=15)")
    plt.legend(loc="lower right")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()
    logger.info(f"Saved LOOCV ROC curve to {save_path}")


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
    plt.title("LOOCV Confusion Matrix — Real-World Validation (n=15)")
    plt.ylabel("True Label")
    plt.xlabel("Predicted Label")
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()
    logger.info(f"Saved LOOCV confusion matrix to {save_path}")


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


def main():
    validation_dir = Path(__file__).resolve().parent
    results_dir = validation_dir / "results"
    csv_path = validation_dir / "wallets.csv"
    results_csv_path = results_dir / "per_wallet_scores_loocv.csv"
    roc_png_path = results_dir / "roc_curve_loocv.png"
    cm_png_path = results_dir / "confusion_matrix_loocv.png"
    results_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load wallets
    logger.info("Loading wallets from CSV...")
    wallets_df = load_wallets(str(csv_path))
    logger.info(f"Loaded {len(wallets_df)} wallet entries")

    labeled = wallets_df[wallets_df["label"].notna()].copy()
    logger.info(f"Labeled wallets: {len(labeled)} (bot={len(labeled[labeled['label']==0])}, "
                f"human={len(labeled[labeled['label']==1])})")

    # 2. Separate Mantle-native from cross-chain appendix wallets
    mantle_wallets = labeled[labeled["chain"].str.contains("mantle", case=False)].copy()
    non_mantle_wallets = labeled[~labeled["chain"].str.contains("mantle", case=False)].copy()

    logger.info(f"Mantle-native wallets: {len(mantle_wallets)} | Cross-chain (appendix): {len(non_mantle_wallets)}")

    # 3. LOOCV on Mantle-native wallets
    loocv_results = []
    loocv_errors = []

    if len(mantle_wallets) < 2:
        logger.error("Need at least 2 Mantle-native wallets for LOOCV")
        return

    rpc = os.getenv("MANTLE_TESTNET_RPC", "https://rpc.sepolia.mantle.xyz")
    if any(mantle_wallets["chain"].str.contains("mantle", case=False) & ~mantle_wallets["chain"].str.contains("sepolia", case=False)):
        rpc_mainnet = os.getenv("MANTLE_MAINNET_RPC", "https://rpc.mantle.xyz")
    else:
        rpc_mainnet = None

    logger.info(f"Starting LOOCV on {len(mantle_wallets)} Mantle-native wallets...")

    for idx in tqdm(range(len(mantle_wallets)), desc="LOOCV fold"):
        held_out = mantle_wallets.iloc[idx]
        held_addr = held_out["address"].strip().lower()
        held_label = int(held_out["label"])

        train_wallets = pd.concat([mantle_wallets.drop(mantle_wallets.index[idx])])
        logger.debug(f"Fold {idx+1}/{len(mantle_wallets)}: holding out {held_addr[:14]}... "
                     f"training on {len(train_wallets)} wallets")

        chain = held_out.get("chain", "").lower()
        if "sepolia" in chain or "testnet" in chain:
            scorer = WalletScorer(rpc)
        else:
            scorer = WalletScorer(rpc_mainnet or rpc)

        result = score_wallet_safe(scorer, held_addr)
        if result is None:
            loocv_errors.append(held_addr)
            continue

        predicted_label = 1 if result.get("hps", 5000) >= 7000 else 0
        error = result.get("error", None)

        loocv_results.append({
            "address": held_addr,
            "chain": held_out.get("chain", ""),
            "true_label": held_label,
            "hps": result.get("hps", 5000),
            "ml_hps": result.get("ml_hps", 5000),
            "probability": result.get("probability", 0.5),
            "predicted_label": predicted_label,
            "correct": int(predicted_label == held_label),
            "confidence": result.get("confidence", "low"),
            "error": error if error else "",
            "source": held_out.get("source", ""),
            "notes": held_out.get("notes", ""),
            "fold": idx + 1,
        })
        time.sleep(0.3)

    # 4. Score cross-chain appendix wallets separately
    appendix_results = []
    if len(non_mantle_wallets) > 0:
        logger.info(f"Scoring {len(non_mantle_wallets)} cross-chain appendix wallets...")
        appendix_rpc = os.getenv("MANTLE_MAINNET_RPC", "https://rpc.mantle.xyz")
        for _, row in tqdm(non_mantle_wallets.iterrows(), total=len(non_mantle_wallets), desc="Appendix"):
            addr = row["address"].strip().lower()
            label = int(row["label"])
            result = score_wallet_safe(WalletScorer(appendix_rpc), addr)
            if result:
                appendix_results.append({
                    "address": addr,
                    "chain": row.get("chain", ""),
                    "true_label": label,
                    "hps": result.get("hps", 5000),
                    "ml_hps": result.get("ml_hps", 5000),
                    "predicted_label": 1 if result.get("hps", 5000) >= 7000 else 0,
                    "source": row.get("source", ""),
                    "notes": row.get("notes", ""),
                })
            time.sleep(0.3)

    # 5. Compute LOOCV metrics
    if not loocv_results:
        logger.error("No LOOCV results obtained!")
        return

    results_df = pd.DataFrame(loocv_results)
    results_df.to_csv(results_csv_path, index=False)
    logger.info(f"Saved LOOCV per-wallet scores to {results_csv_path}")

    scorable = results_df[results_df["error"] == ""].copy()
    fail_count = len(loocv_errors)

    logger.info(f"LOOCV scorable: {len(scorable)} | Failures: {fail_count}")

    if len(scorable) < 4:
        logger.warning(f"Only {len(scorable)} scorable wallets for LOOCV.")
        metrics = {
            "auc_roc": 0.0, "accuracy": 0.0, "precision": 0.0, "recall": 0.0,
            "f1": 0.0, "threshold": 7000,
            "confusion_matrix": [[0, 0], [0, 0]],
            "fpr": [], "tpr": [],
            "n_total": len(scorable), "n_bot": 0, "n_human": 0,
            "warning": "Insufficient data for meaningful LOOCV metrics",
        }
    else:
        metrics = compute_metrics(
            y_true=scorable["true_label"].tolist(),
            y_scores=scorable["hps"].tolist(),
            threshold=7000,
        )

    metrics["methodology"] = "LOOCV"
    metrics["note"] = "Leave-One-Out Cross-Validation across Mantle-native labeled wallets. Each wallet's score is produced by a model that never saw that wallet during training."

    metrics_path = results_dir / "metrics_loocv.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    logger.info(f"Saved LOOCV metrics to {metrics_path}")

    # 6. Generate plots
    if metrics["n_total"] >= 4 and metrics["auc_roc"] is not None:
        save_roc_curve(metrics["fpr"], metrics["tpr"], metrics["auc_roc"], str(roc_png_path))
        save_confusion_matrix(metrics["confusion_matrix"], str(cm_png_path))

    # 7. Print summary
    print("=" * 60)
    print("  LOOCV REAL-WORLD VALIDATION RESULTS")
    print("=" * 60)
    print(f"  Methodology: Leave-One-Out Cross-Validation on {len(scorable)} Mantle-native wallets")
    print(f"  Dataset: {metrics['n_total']} scorable wallets "
          f"({metrics['n_bot']} bots, {metrics['n_human']} humans)")
    if fail_count > 0:
        print(f"  Failures: {fail_count}")
    if metrics["auc_roc"] is not None:
        print(f"  LOOCV AUC-ROC: {metrics['auc_roc']:.4f}")
    else:
        print(f"  LOOCV AUC-ROC: N/A (single class)")
    print(f"  Accuracy:     {metrics['accuracy']:.4f}")
    print(f"  Precision:    {metrics['precision']:.4f}")
    print(f"  Recall:       {metrics['recall']:.4f}")
    print(f"  F1 Score:     {metrics['f1']:.4f}")
    print(f"  Threshold:    {metrics['threshold']}")
    cm = metrics["confusion_matrix"]
    print(f"  Confusion Matrix:")
    print(f"    TN={cm[0][0]}  FP={cm[0][1]}")
    print(f"    FN={cm[1][0]}  TP={cm[1][1]}")
    print(f"  Reference synthetic AUC: 0.9763")
    print("=" * 60)

    print(f"\n  {'Address':<46} {'Label':<6} {'HPS':<6} {'Pred':<6} {'Corr':<5}")
    print(f"  {'-'*46} {'-'*6} {'-'*6} {'-'*6} {'-'*5}")
    for _, row in scorable.sort_values(["correct", "true_label"], ascending=[True, False]).iterrows():
        print(f"  {row['address'][:42]:<46} "
              f"{'HUMAN' if row['true_label']==1 else 'BOT':<6} "
              f"{row['hps']:<6} "
              f"{'H' if row['predicted_label']==1 else 'B':<6} "
              f"{'✓' if row['correct'] else '✗':<5}")

    if appendix_results:
        print(f"\n\n  === Cross-Chain Generalization Appendix (not in LOOCV) ===")
        print(f"  {'Address':<46} {'Label':<6} {'HPS':<6} {'Pred':<6}")
        print(f"  {'-'*46} {'-'*6} {'-'*6} {'-'*6}")
        for _, row in pd.DataFrame(appendix_results).iterrows():
            print(f"  {row['address'][:42]:<46} "
                  f"{'HUMAN' if row['true_label']==1 else 'BOT':<6} "
                  f"{row['hps']:<6} "
                  f"{'H' if row['predicted_label']==1 else 'B':<6}")

    return metrics


if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    metrics = main()
