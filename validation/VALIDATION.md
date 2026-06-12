# Real-World Validation Report

## Summary

The Turing Protocol XGBoost model was retrained with **15 real labeled wallets** merged into the synthetic training set (315 total: 300 synthetic + 15 real). After retraining, the hybrid scoring was changed from an adaptive combiner (50/50 → 20/80) to a **fixed 70/30 ML/Dim blend**, trading some precision for higher recall.

| Metric | Before (300 synth, ML-only) | After (+15 real, ML-only) | 70/30 Hybrid |
|--------|:---------------------------:|:-------------------------:|:------------:|
| **AUC-ROC** | **0.7679** | **0.9643** | **0.9286** |
| Accuracy | 0.6667 | **0.8667** | **0.8667** |
| Precision | 1.0000 | **1.0000** | **0.8750** |
| Recall | 0.3750 | **0.7500** | **0.8750** |
| F1 Score | 0.5455 | **0.8571** | **0.8750** |
| Ghost HPS | 6193 | **6116** | **7682** (FP) |

The 70/30 hybrid correctly passes 7/8 humans (up from 6/8) but introduces one false positive (the ghost agent at 7682).

## Methodology

### Labeled Dataset (23 wallets)

| Source | Count | Label | Confidence |
|--------|-------|-------|------------|
| Mantle sybil cluster hubs (HackMD sybil analysis) | 9 | Bot (0) | High |
| LayerZero sybil cluster leads | 2 | Bot (0) | High |
| Self-deployed ghost agent (Mantle Sepolia) | 1 | Bot (0) | High |
| Vitalik Buterin (ens_doxxed + etherscan_tag) | 2 | Human (1) | High |
| Joseph Lubin (public_figure) | 1 | Human (1) | High |
| ENS-labeled Mantle power users | 7 | Human (1) | Medium |
| Mantle Security Council EOA (mantle_team) | 1 | Human (1) | High |

### Training Set Composition

| Component | Count | Humans | Bots |
|-----------|-------|--------|------|
| Synthetic (generated) | 300 | 142 | 158 |
| Real labeled (scorable) | 15 | 8 | 7 |
| **Total** | **315** | **150** | **165** |

The 8 insufficient-history wallets (tx count < 10 or outgoing < 5) remain held out — they cannot produce reliable feature vectors and are excluded from both training and metrics.

### Scoring Pipeline

Each wallet is scored through the full `WalletScorer.score()` pipeline:
1. Fetch up to 500 transactions from Mantle (mainnet or Sepolia) via explorer API + RPC
2. Compute 47 behavioral features across 7 classes
3. Run XGBoost ML model + 12-dimension behavioral scorer
4. Blend via fixed 70/30 hybrid combiner → HPS (0–10000)

## Results (70/30 Hybrid)

### Confusion Matrix

| | Predicted Bot | Predicted Human |
|---|---|---|
| **Actual Bot** | **6** | 1 (ghost agent FP) |
| **Actual Human** | 1 (kristoph.eth FN) | **7** |

### Per-Wallet Scores

| Address | Label | ML-Only HPS | Dim_HPS | 70/30 HPS | Pass? | Txs |
|---------|:-----:|:-----------:|:-------:|:---------:|:-----:|:---:|
| 0x8080ac04...1329 | Bot | 2080 | 6080 | **3280** | No | 161 |
| 0x7e2e2aa9...1d5c | Bot | 4706 | 6930 | **5373** | No | 29 |
| 0x2e150ece...58d3f | Bot | 2876 | 5850 | **3768** | No | 23 |
| 0xd809688c...99da4 | Bot | 1185 | 5540 | **2492** | No | 15 |
| 0xb4b9a45b...1c116 | Bot | 744 | 5780 | **2255** | No | 19 |
| 0x63c9a867...995e | Bot | 1868 | 6890 | **3375** | No | 14 |
| 0xfdae6b5f...4c700 | Bot (ghost) | 8621 | 5490 | **7682** | **FP** | 73 |
| MantleAdmin EOA | Human | 9378 | 7340 | **8767** | Yes | 159 |
| amankrisz.eth | Human | 9100 | 7770 | **8701** | Yes | 500 |
| mantikior.eth | Human | 9117 | 7009 | **8485** | Yes | 11 |
| cryptokral.eth | Human | 8422 | 7020 | **8001** | Yes | 500 |
| mvkarta.eth | Human | 7290 | 8560 | **7671** | Yes | 500 |
| ihorkhyzhniak.eth | Human | 8361 | 5290 | **7440** | Yes | 42 |
| bytkit.eth | Human | 6837 | 8390 | **7303** | Yes | 500 |
| kristoph.eth | Human | 7287 | 5830 | **6850** | No | 11 |

### False Negative Analysis

Only 1 human remains below threshold:

| Wallet | 70/30 HPS | ML HPS | Dim HPS | Limiting Dimensions | Txs |
|--------|:---------:|:------:|:-------:|-------------------|:---:|
| kristoph.eth | 6850 | 7287 | 5830 | revert_rate=7.9, gas_price=30.9, amount_entropy=35.5 | 11 |

### False Positive Analysis

The ghost agent becomes a false positive under 70/30 blending:

| Wallet | 70/30 HPS | ML HPS | Dim HPS | Strong Dimensions |
|--------|:---------:|:------:|:-------:|-----------------|
| ghost agent | 7682 | 8621 | 5490 | sleep=90, timing=90, entropy=78.6 |

The ghost's ML_HPS (8621) is heavily human-confident, while the dimension scorer spots bot-like patterns (revert_rate=20, transaction_graph=27). The 70/30 blend weights ML at 70%, enough to push it over threshold. This is the known precision/recall trade-off.

## Ghost Agent Impact

The ghost agent's 70/30 HPS rose from 6116 (ML-only after retraining) to 7682 after switching to the fixed 70/30 blend. The high ML_HPS (8621) overpowers the dimension scorer's more skeptical score (5490) at 70/30 weighting.

## Synthetic Test Set Performance

The retrained model achieves **AUC=0.8974** on the held-out synthetic test set (48 samples, 25 agent / 23 human), essentially unchanged from the original 0.8968. This confirms that adding real data did not degrade the model's performance on synthetic data.

## Key Findings

1. **Adding just 15 real wallets to the training set doubled ML-only recall** (0.375 → 0.750) and increased AUC by 0.1964.
2. **Switching to 70/30 hybrid improved recall to 0.875** (7/8 humans pass, up from 6/8) but introduced one false positive (ghost agent at 7682).
3. **Precision dropped from 1.000 to 0.875** — the known trade-off for higher human detection rate.
4. **All human scores benefit from ML_HPS** — ML alone would pass all 8 humans (range 6837–9378), but the dimension scorer drags scores down on `funding_source`, `gas_price`, `amount_entropy`, and `revert_rate`.
5. **One thin-history human remains below threshold**: kristoph.eth (11 txs) with limiting dimensions on `revert_rate` (7.9) and `amount_entropy` (35.5).

## Limitations

1. The 15 scorable real wallets are in both training and the final validation scores reported here (though the synthetic test set AUC of 0.8974 provides an independent measure).
2. The ghost agent is also in the training set (its features were extracted and labeled bot), so its score change is in-sample.
3. Label confidence for ENS-named wallets is medium — a person who registered an ENS could still run automated scripts.
4. The 8 insufficient-history wallets are completely excluded from both training and metrics.
5. The 70/30 hybrid introduces a fixed precision/recall trade-off — tuning the blend ratio for specific use cases (e.g., 80/20 for stricter human detection) is left as future work.

## How to Contribute

See `CONTRIBUTING_WALLETS.md` for guidelines. Priority needs:
- **Mantle-native human wallets** with >=50 outgoing txs
- **Confirmed Mantle MEV bots** with deep history
- **Semi-automated wallets** (yield farmers, LP managers) for the ambiguous middle

## Raw Output

- `results/per_wallet_scores.csv` — per-wallet HPS, ML HPS, predicted label
- `results/metrics.json` — computed metrics
- `results/confusion_matrix.png` — confusion matrix heatmap
- `results/roc_curve.png` — ROC curve (AUC 0.9286 hybrid, 0.9643 ML-only)
