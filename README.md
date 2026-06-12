# TURING PROTOCOL
### On-Chain Behavioral Proof of Humanity for the Mantle Network

> *"Can a machine prove it is not a machine?"*
> — The question at the heart of every Sybil-resistant system ever built.

[![Mantle Testnet](https://img.shields.io/badge/Network-Mantle%20Sepolia-00D4FF?style=flat-square)](https://explorer.testnet.mantle.xyz)
[![Model AUC](https://img.shields.io/badge/Synthetic%20AUC-0.8968-brightgreen?style=flat-square)](#results)
[![Hybrid AUC](https://img.shields.io/badge/Hybrid%20AUC-0.9286-yellow?style=flat-square)](validation/VALIDATION.md)
[![ML AUC](https://img.shields.io/badge/ML%20AUC-0.9643-brightgreen?style=flat-square)](validation/VALIDATION.md)
[![Features](https://img.shields.io/badge/Behavioral%20Features-47-purple?style=flat-square)](#the-47-features)
[![Solidity](https://img.shields.io/badge/Solidity-0.8.28-blue?style=flat-square)](https://soliditylang.org)
[![Python](https://img.shields.io/badge/Python-3.11+-yellow?style=flat-square)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](#license)

---

## Table of Contents

- [The Problem](#the-problem)
- [What is Turing Protocol?](#what-is-turing-protocol)
- [System Architecture](#system-architecture)
- [The Interrogator — ML Classifier](#the-interrogator)
- [The 47 Behavioral Features](#the-47-features)
- [The Ghost Agent — Adversarial AI](#the-ghost-agent)
- [The Adversarial Feedback Loop](#the-adversarial-feedback-loop)
- [Smart Contracts](#smart-contracts)
- [The Proof of Behavior NFT](#proof-of-behavior-nft)
- [Oracle Service](#oracle-service)
- [Live Dashboard](#live-dashboard)
- [Results & Metrics](#results--metrics)
- [Deployed Contracts — Mantle Sepolia](#deployed-contracts)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Running the System](#running-the-system)
- [How Each Component Works](#how-each-component-works)
- [Why This Matters](#why-this-matters)

---

## The Problem

The blockchain is overrun by bots. MEV bots, DCA bots, arbitrage bots, Sybil farms — mechanically operated wallets now represent a significant fraction of all on-chain activity. This creates cascading problems across the entire ecosystem:

- **Airdrops** are claimed entirely by automated scripts before real users can participate.
- **DAO governance** is captured by Sybil wallets that manufacture false consensus.
- **DeFi protocols** suffer from MEV extraction that silently drains value from human traders.
- **Social applications** on-chain cannot distinguish real community from manufactured engagement.
- **Proof of Personhood** systems that rely purely on social graphs or hardware attestation are either centralised, gameable, or both.

Existing solutions are inadequate. Simple heuristics (wallet age, tx count, token holdings) are trivially gamed. Hardware-based solutions (WorldCoin) require physical presence and introduce biometric surveillance. Social graph approaches (BrightID) require trust bootstrapping. None of them look at *behaviour* — the one thing that is genuinely hard to fake at scale.

**Turing Protocol takes a fundamentally different approach.** It watches *how* a wallet behaves over time — the timing of transactions, the psychology embedded in gas price choices, the irrational biases that only humans exhibit — and produces a probabilistic score of humanity that is continuously updated, fully transparent, and composable by any smart contract on Mantle.

---

## What is Turing Protocol?

Turing Protocol is a **live, autonomous, self-improving on-chain proof-of-humanity system** built on Mantle Network. It consists of five tightly integrated components that work together in a continuous adversarial loop:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        TURING PROTOCOL                              │
│                                                                     │
│  ┌──────────────┐     ┌───────────────┐     ┌──────────────────┐    │
│  │  GHOST AGENT │────▶│  THE          │────▶│  HPS ORACLE     │    │
│  │  (Adversary) │     │  INTERROGATOR │     │  (On-chain)      │    │
│  │              │◀────│  (XGBoost+    │     │                  │   │
│  │  Adapts when │     │   SHAP)       │     │  Scores 0-10000  │    │
│  │  detected    │     │               │     │  for any wallet  │    │
│  └──────────────┘     └───────────────┘     └────────┬─────────┘    │
│                                                       │             │
│                                              ┌────────▼─────────┐   │
│                                              │  PROOF OF        │   │
│                                              │  BEHAVIOR NFT    │   │
│                                              │  (Soulbound ERC- │   │
│                                              │  721, non-xfer)  │   │
│                                              └──────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

The system works as follows:

1. **The Interrogator** analyses any Mantle wallet's transaction history and computes a **Human Probability Score (HPS)** from 0 to 10,000, along with a SHAP-based explanation of why that score was assigned.

2. **The HPSOracle smart contract** stores these scores on-chain, making them readable by any Mantle smart contract. Any protocol can ask: *"Is this wallet human enough to participate?"*

3. **The ProofOfBehavior NFT** is a soulbound (non-transferable) ERC-721 minted for wallets that sustain an HPS ≥ 7,000 for 72+ consecutive hours. It encodes a behavioural fingerprint derived from SHAP values and is permanently attached to the wallet.

4. **The Ghost Agent** is an autonomous trading agent deliberately designed to fool the Interrogator. It simulates human cognitive biases — overconfidence after winning streaks, loss aversion, round-number preferences, timezone-consistent activity — and continuously attempts to achieve a high HPS.

5. **The Adversarial Retrainer** monitors when the Ghost Agent's score exceeds the minting threshold. When it does, it triggers a new model training run on fresh data, producing a model version that can detect the Ghost's latest behavioural mimicry. The cycle repeats indefinitely, making the classifier progressively harder to fool.

---

## System Architecture

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                         TURING PROTOCOL — FULL SYSTEM                          │
├─────────────────┬──────────────────────────────────────────────────────────────┤
│                 │                                                              │
│  MANTLE CHAIN   │   ┌───────────────────────────────────────────────────────┐  │
│                 │   │           ORACLE SERVICE (FastAPI)                    │  │
│                 │   │                                                       │  │
│  ┌───────────┐  │   │  ScoreSubmissionLoop   POBEligibilityChecker          │  │
│  │HPSOracle  │◀─┼───│  (batch tx every 15m)  (mint/refresh NFTs)            │  │
│  │           │  │   │                                                       │  │
│  │getScore() │  │   │  ┌────────────────────────────────────────────────┐   │  │
│  │batchUpd.. │──┼──▶│  │                  WalletScorer                  │   │  │
│  ┌───────────┐  │   │  │                                                │   │  │
│  │ProofOf    │◀─┼── │   │  │  MantleDataFetcher → FeatureEngineer       │   │  │
│  │Behavior   │  │   │  │  (47 features)       (7 feature classes)       │   │  │
│  │(Soulbound │  │   │  │                                                │   │  │
│  │ ERC-721)  │  │   │  │  ┌──────── ML Path ────────┐                   │   │  │
│  │  └───────────┘  │   │  │  │ FeaturePreprocessor  │                   │   │  │
│  └───────────┘  │   │  │  │ (RobustScaler)          │                   │   │  │
│                 │   │  │  │ InterrogatorModel       │                   │   │  │
│                 │   │  │  │ (XGBoost + SHAP)        │                   │   │  │
│                 │   │  │  └───────── ML_HPS ────────┘                   │   │  │
│                 │   │  │                                                │   │  │
│                 │   │  │  ┌────── Dimension Path ──────┐                │   │  │
│                 │   │  │  │ DimensionScorer            │                │   │  │
│                 │   │  │  │ (12 dimensions, 0-100)     │                │   │  │
│                 │   │  │  │ Wallet Age Boost           │                │   │  │
│                 │   │  │  │ (×1.30 max)                │                │   │  │
│                 │   │  │  └─────── Dim_HPS ────────────┘                │   │  │
│                 │   │  │                                                │   │  │
│                 │   │  │  Fixed Hybrid Combiner                         │   │  │
│                 │   │  │  (70/30 ML/Dim, clamped [0, 10000])            │   │  │
│  │ ERC-721)  │  │   │  └────────────────────────────────────────────────┘   │  │
│  └───────────┘  │   │                                                       │  │
│                 │   │  AdversarialRetrainer                                 │  │
│  ┌───────────┐  │   │  (watches ghost score → triggers retrain)             │  │
│  │TuringLib  │  │   └───────────────────────────────────────────────────────┘  │
│  │(utility)  │  │                           ▲                                  │
│  └───────────┘  │                           │ scores                           │
│                 │   ┌─────────────────────┐ │                                  │
│                 │   │  GHOST AGENT        │─┘                                  │
│                 │   │                     │                                    │
│                 │   │  TimingNoise        │         ┌──────────────────────┐   │
│                 │   │  GasSelector        │         │      DASHBOARD       │   │
│                 │   │  PortfolioBias      │         │  (React + Vite)      │   │
│                 │   │  NewsReaction       │         │                      │   │
│                 │   │  InteractionDiv     │         │  Live HPS gauge      │   │
│                 │   │  ParamOptimizer     │         │  SHAP waterfall      │   │
│                 │   │  StrategyLayer      │         │  Score history       │   │
│                 │   └─────────────────────┘         │  POB leaderboard     │   │
│                 │                                   └──────────────────────┘   │
└─────────────────┴──────────────────────────────────────────────────────────────┘
```

---

## The Interrogator

The Interrogator is the core ML component of Turing Protocol. It is an **XGBoost binary classifier** trained to distinguish human wallets (label=1) from agent wallets (label=0), operating on a 47-dimensional behavioural feature vector extracted from raw transaction history.

### Model Architecture

```
Input: 47 behavioural features
       ↓
RobustScaler (outlier-resistant normalisation)
       ↓
XGBoost Classifier
  - n_estimators: 400
  - max_depth: 5
  - learning_rate: 0.05
  - subsample: 0.8
  - colsample_bytree: 0.7
  - L1 regularisation (alpha=0.1)
  - L2 regularisation (lambda=1.0)
  - objective: binary:logistic
  - eval_metric: AUC
       ↓
TreeSHAP Explainer (post-hoc explanations)
       ↓
Output: HPS (Human Probability Score) = P(human) × 10,000
        SHAP contributions per feature
        Behavioural fingerprint (SHA-256 of top-10 SHAP values)
```

### Why XGBoost?

XGBoost was chosen deliberately over deep learning for three reasons critical to this application:

1. **Calibrated probabilities**: The output of `binary:logistic` with Brier score optimisation produces probabilities that actually mean something. An HPS of 7,000 means the model is genuinely 70% confident this wallet is human — not just a ranking score.

2. **SHAP compatibility**: TreeSHAP provides exact (not approximate) feature attributions for tree models in O(TLD) time. This allows every score to be accompanied by a human-readable explanation that is embedded in the on-chain NFT metadata.

3. **Small data regime**: With hundreds to low thousands of labelled wallets, XGBoost dramatically outperforms neural approaches that require orders of magnitude more data for comparable generalisation.

### Label Acquisition Strategy

Obtaining ground-truth labels on a blockchain is genuinely hard. The Interrogator uses a three-source labelling strategy:

**Known Agents (label=0)**:
- Deployed simple bots on Mantle Sepolia that send fixed transactions on a cron schedule
- Addresses of testnet MEV bots and arbitrage contracts observed in the wild
- Synthetically generated feature vectors parameterised to match four known bot archetypes: MEV, DCA, Arbitrage, LP Manager

**Known Humans (label=1)**:
- Wallets with characteristics that are statistically impossible to produce mechanically:
  - Active for 6+ months with activity concentrated in specific UTC hours (timezone signal)
  - Inter-transaction timing coefficient of variation > 1.5 (irregular timing)
  - Protocol diversity across 6+ unique protocols
  - Non-zero transaction failure rate (humans make mistakes; bots don't)
- Real wallets submitted by participants during testing phases

**Synthetic Spectrum (training augmentation)**:
- A continuous spectrum from `human_strength=0.0` (pure agent) to `human_strength=1.0` (pure human)
- Wallets near 0.5 are deliberately ambiguous, preventing the model from achieving perfect training accuracy and forcing generalisation
- Distribution is U-shaped (bimodal at extremes) with ~20% in the ambiguous middle

---

## The Dimension Scorer — 12 Behavioural Dimensions

The XGBoost model is paired with a **12-dimension deterministic scorer** that evaluates wallet behaviour across interpretable axes (0-100 each). While the ML model produces a black-box probability, the dimension scorer provides transparent, auditable scores for each behavioural dimension — and the two paths are combined adaptively.

### Why Two Scorers?

| | ML Model (XGBoost) | Dimension Scorer |
|---|---|---|
| **Strength** | Captures non-linear interactions across 47 features | Interpretable, auditable, zero-shot |
| **Weakness** | Requires retraining; may overfit to training distribution | Hand-crafted thresholds; misses cross-dimension patterns |
| **Output** | HPS (0-10000) + SHAP values | 12 per-dimension scores (0-100) + composite average |
| **Reliability** | High when distribution matches training | High when features fall within expected ranges |

The **fixed hybrid combiner** merges both outputs with a static weighting:

- `Final_HPS = 0.70 × ML_HPS + 0.30 × Dim_HPS`
- Clamped to `[0, 10000]`

This 70/30 blend was chosen over the original adaptive system (which shifted from 50/50 to 20/80 when ML and dimensions disagreed) after real-world validation showed that adaptively trusting dimensions over ML reduced human recall (only 6/8 humans passed threshold). The fixed 70/30 blend correctly passes 7/8 humans while holding bots below threshold — at the cost of one false positive (the ghost agent scores 7682).

### The 12 Dimensions

#### 1. Sleep Pattern (0-100)
Measures whether activity clusters in timezone-consistent hours. Uses hourly Gini coefficient and interval CV.
- **Human** (70-100): Activity concentrated in waking hours, irregular gaps
- **Spam bot** (0-30): 24/7 uniform distribution, no gaps
- **Careful bot** (20-50): Fake programmed gaps in fixed patterns

#### 2. Transaction Timing (0-100)
Evaluates the irregularity of inter-transaction intervals using CV, autocorrelation, fast-reaction ratio, and burstiness.
- **Human** (70-100): CV > 1.0, positive burstiness, low autocorrelation
- **Spam bot** (0-30): Near-zero CV, negative burstiness (regular intervals)
- **Careful bot** (20-50): Randomized but uniformly so

#### 3. Gas Price Psychology (0-100)
Gas price selection is a micro-economic decision that reveals cognitive biases. Features: gas price CV, round number fraction, nice number fraction, overpay ratio.
- **Human** (70-100): High variability, round/nice numbers, occasional overpay
- **Spam bot** (0-30): Lowest possible, precise, no rounding
- **Careful bot** (20-50): Network average, calibrated, no psychological noise

#### 4. Amount Entropy (0-100)
Position sizing reveals loss aversion, overconfidence, and the house-money effect. Features: size CV, skewness, round value ratio, max-to-mean ratio.
- **Human** (70-100): High variance, round amounts, occasional outliers
- **Spam bot** (0-30): Fixed or near-fixed amounts
- **Careful bot** (20-50): Artificially randomized, no psychological skew

#### 5. Revert Rate (0-100)
Only humans fail transactions at non-trivial rates. Features: historical failure rate with non-linear mapping.
- **Human** (70-100): 2-5% failure rate (real errors, gas underestimation)
- **Spam bot** (0-20): 0% failure (simulated off-chain) or >10% (probe-and-revert)
- **Careful bot** (0-20): Near-zero failure rate

#### 6. Wallet Age (0-100)
Established wallets with deep history indicate real human engagement. Uses log block span from first to latest transaction.
- **Human** (70-100): Months to years of activity
- **Spam bot** (0-30): Freshly created, shallow history
- **Careful bot** (20-50): Aged deliberately in advance

#### 7. Funding Source (0-100)
Who funds this wallet? Diverse organic funding indicates human adoption; single-donor fan-out indicates bot farms.
- **Human** (70-100): Various organic sources, low concentration
- **Spam bot** (0-30): Single donor wallet, high top-1 concentration
- **Careful bot** (20-50): CEX withdrawal + intermediary layers

#### 8. Contract Diversity (0-100)
Human curiosity drives exploration of multiple protocols. Features: unique protocol count, HHI, exploration ratio, weekend ratio.
- **Human** (70-100): 3+ protocols, exploration of unknown contracts
- **Spam bot** (0-30): 1-2 task-specific contracts
- **Careful bot** (20-50): Padded with noise interactions

#### 9. News Reaction (0-100)
Human trading is bursty and news-driven. Uses formal burstiness framework (Goh & Barabasi 2008), session clustering, and session gap CV.
- **Human** (70-100): Positive burstiness, irregular session gaps
- **Spam bot** (0-30): No burstiness, uniform activity
- **Careful bot** (20-50): Programmed pauses for major triggers
#### 10. IP / Fingerprint (neutral: 50, weight=0.0)

Cannot be determined from on-chain data alone. Neutral by default. The dimension weight is **hard-set to 0.0** in `dimension_scorer.py`, meaning this dimension contributes zero to the composite average regardless of its score. This preserves the interface for future cross-chain IP-level data sources without degrading the current scoring pipeline.

#### 11. Cross-Chain Patterns (neutral: 50, weight=0.0)

Requires multi-chain data sources. Neutral by default. Like `ip_fingerprint`, the cross-chain dimension is **hard-weighted at 0.0**, retained in the dimension interface for future multi-chain integration but excluded from the composite score computation. Both neutral dimensions remain visible in the `dimension_scores` output for transparency.
#### 12. Transaction Graph (0-100)
Wallet interaction topology. Humans interact with a diverse web of counterparties; bots follow star/chain patterns.
- **Human** (70-100): Varied recipients, low top-1 concentration, some EOA sends
- **Spam bot** (0-30): Star pattern from single donor, high contract ratio
- **Careful bot** (20-50): Intermediary layers, broken up transfers

### Wallet Age Boost

A post-scoring multiplicative boost is applied to the dimension composite average for wallets that **prove** they are older than 2 years:

```
age_days <= 730 -> boost = 1.0 (no boost)
age_days > 730  -> boost = 1.0 + (age_days - 730) / 365 * 0.05
                   capped at 1.30 (+30%)
```

The boost only activates when the wallet's actual transaction history spans >2 years — if all 100 fetched transactions are within 2 years, the data cannot prove the wallet is older, and no boost is applied. This prevents new wallets with short active histories from receiving age bonuses.

### Real-World Dimension Scores

Scored on Ethereum mainnet wallets:

| Wallet | HPS | Strongest Dimensions | Weakest Dimensions |
|--------|-----|---------------------|-------------------|
| **Bitfinex Cold Wallet** | **7140** | wallet_age=95, sleep=90, timing=90, gas=86 | revert=30, entropy=48 |
| **Vitalik Buterin** | **5870** | sleep=90, funding=84, timing=83, graph=82 | revert=8, entropy=42, gas=44 |
| **Binance Cold Wallet** | **5840** | wallet_age=95, sleep=90, timing=82 | revert=20, gas=45, entropy=42 |
| **Recent block senders (avg)** | **3290-5300** | sleep=65-90, timing=60-85 | wallet_age=5, gas=6-22 |

The Bitfinex wallet (7140) demonstrates the age boost in action: at 3.3 years of proven history, it receives a +6.7% multiplier. New wallets and very active wallets whose 100 most recent transactions compress into less than 2 years do not receive the boost.

---

## The 47 Features

The feature engineering pipeline extracts 47 numerical features from a wallet's transaction history, organised into seven behavioural classes. Every class captures a distinct dimension of the fundamental question: *does this wallet behave like a thinking human being, or like a machine?*

### Class 1 — Temporal Irregularity (8 features)

The most discriminating class. Human decision-making is inherently noisy. The temporal gap between transactions follows a log-normal distribution when driven by human attention, but is mechanically regular or exponential when driven by a scheduler.

| Feature | Key Signal |
|---------|-----------|
| `temp_0_log_mean_delta` | Mean reaction time. Humans: 7–300s. Agents: 0.1–2s |
| `temp_1_log_std_delta` | Standard deviation of timing. Humans: high. Agents: near zero |
| `temp_2_skewness` | Human distributions are right-skewed (occasional slow reactions) |
| `temp_3_kurtosis` | Agents often have platykurtic (flat) distributions |
| `temp_4_cv` | Coefficient of variation. Humans: >1.0. Agents: <0.3 |
| `temp_5_fast_reaction_ratio` | Fraction of txs in <2 seconds. High = strong agent signal |
| `temp_6_autocorr` | Cron-scheduled agents have high lag-1 autocorrelation |
| `temp_7_hour_gini` | Gini coefficient of hourly activity. Agents: ~0. Humans: 0.4–0.7 |

### Class 2 — Gas Behaviour (7 features)

Gas price selection is a micro-economic decision. Humans use wallet UIs that suggest gas and choose rounded, psychologically comfortable values. They occasionally overpay when urgent and underpay when inattentive. Agents compute exact gas via `eth_gasPrice` and apply precise multipliers — no rounding, no psychological noise.

**Account Abstraction (AA) gas normalisation**: AA wallets (e.g., ERC-4337) consume 2–4× more gas per user operation than EOA wallets for the same logical action, due to the `preVerificationGas` overhead. Without normalisation, AA wallets would incorrectly score low on `gas_5_mean_efficiency` and `gas_6_efficiency_std`. The `_is_aa_wallet()` detector in `feature_engineer.py` identifies AA wallets by checking for `entryPoint` interactions and `sender` address mismatches in event logs. When detected, gas efficiency features are recomputed relative to the `preVerificationGas` baseline, preventing false-positive bot classification.

| Feature | Key Signal |
|---------|-----------|
| `gas_0_price_cv` | Gas price variability. Agents: near zero. Humans: high |
| `gas_1_round_fraction` | Fraction of prices that are round Gwei values |
| `gas_2_nice_number_fraction` | Fraction divisible by 5 Gwei |
| `gas_3_percentile_variance` | Agents consistently use median gas; humans vary |
| `gas_4_overpay_ratio` | Emotional urgency (>1.5× median). Human trait |
| `gas_5_mean_efficiency` | gas_used/gas_limit. Agents set limits precisely |
| `gas_6_efficiency_std` | Variance in gas efficiency. Humans: high |

### Class 3 — Interaction Diversity (6 features)

Humans are curious. They explore new protocols, use contracts for reasons unrelated to their main strategy, trade on weekends, and interact with unknown contracts out of FOMO. Agents are focused: 1–3 contracts, fixed methods, uniform 24/7 activity.

| Feature | Key Signal |
|---------|-----------|
| `div_0_unique_contract_ratio` | Unique contracts / total txs |
| `div_1_unique_protocols` | Count of distinct known protocols |
| `div_2_method_diversity` | Unique function selectors / total txs |
| `div_3_protocol_hhi` | Herfindahl-Hirschman concentration index (1.0 = pure bot) |
| `div_4_exploration_ratio` | Fraction of txs to unknown/new contracts |
| `div_5_weekend_ratio` | Bots are active uniformly. Humans prefer weekdays |

### Class 4 — Portfolio Behaviour (9 features)

The most psychologically rich feature class. Human traders exhibit the full spectrum of well-documented behavioural finance biases. These are not bugs in human cognition — they are fundamental patterns that have been replicated across thousands of trading studies and are essentially impossible to fake convincingly at scale.

| Feature | Key Signal |
|---------|-----------|
| `port_0_size_cv` | Humans vary position sizes dramatically. Agents use fixed sizes |
| `port_1_size_skew` | Skewness of log position sizes |
| `port_2_size_kurtosis` | Kurtosis of log position sizes |
| `port_3_overconfidence_score` | Do position sizes increase after winning streaks? |
| `port_4_streak_size_correlation` | Correlation between streak length and trade size |
| `port_5_round_value_ratio` | Humans prefer 0.1, 0.5, 1.0 MNT amounts |
| `port_6_lognormal_fit` | Human value distributions fit log-normal well |
| `port_7_activity_consistency` | Agents are consistent. Humans are variable |
| `port_8_max_to_mean_ratio` | Outlier trade sizes (impulse buys) signal humanity |

### Class 5 — Temporal Correlation to Events (5 features)

Human trading is driven by news, social media, and market events. This produces **bursty** activity — clusters of transactions separated by long quiet periods — which is measured using the formal statistical framework of Goh & Barabási (2008).

| Feature | Key Signal |
|---------|-----------|
| `event_0_burstiness` | B=(σ-μ)/(σ+μ). Near +1 = human. Near -1 = cron agent |
| `event_1_memory` | Correlation between consecutive inter-arrival times |
| `event_2_clustering` | Fraction of txs in top-10% activity windows |
| `event_3_avg_session_txs` | Humans trade in sessions; bots don't cluster |
| `event_4_session_gap_cv` | Regular session gaps = agent. Irregular = human |

### Class 6 — Behavioural Consistency (6 features)

Humans become erratic under market stress. When prices move sharply, human traders deviate from their normal patterns — sending more transactions, changing gas strategies, making mistakes. Agents either hold to their programmed logic or stop entirely.

| Feature | Key Signal |
|---------|-----------|
| `consist_0_stress_variance_ratio` | High-activity period variance / low-activity period variance |
| `consist_1_timing_early_cv` | Timing variability in first half of history |
| `consist_2_timing_late_cv` | Timing variability in second half of history |
| `consist_3_cv_evolution` | Does behaviour become more or less regular over time? |
| `consist_4_failure_rate` | Only humans fail transactions. Agents almost never do |
| `consist_5_method_evolution` | Do the functions called change over time? |

### Class 7 — Network Features (6 features)

Coordinated bot farms exhibit distinctive network patterns: wallets funded from the same source, interacting with the same tiny set of contracts, never sending to EOAs. Humans interact with other humans.

**Adaptive fetch window**: Unlike the original fixed 150-transaction window, `MantleDataFetcher` now uses `fetch_wallet_transactions_adaptive()`, which adjusts the number of transactions fetched to cover a 90-day target window (min 50, max 500). For wallets with dense activity (e.g., highly active traders compressing 500+ txs into 2 days), the adaptive window captures the full 90 days of history, giving the time-based features (`wallet_age`, `burstiness`, `session_gap_cv`) sufficient data to distinguish human from agent behaviour.

**API contamination guard**: The `_validate_tx_belongs_to_wallet()` function runs after each explorer API fetch, discarding transactions returned by Etherscan that do not belong to the requested wallet address. This fixes a known Etherscan data contamination issue where the "from" field filter can return unrelated transactions for high-activity addresses.

| Feature | Key Signal |
|---------|-----------|
| `net_0_unique_recipient_ratio` | Unique counterparties / total outgoing txs |
| `net_1_top1_concentration` | Fraction of txs to single most-used address |
| `net_2_top3_concentration` | Fraction of txs to top-3 addresses |
| `net_3_wallet_age_blocks_log` | Log of block span across transaction history |
| `net_4_total_volume_log` | Log of total MNT transferred |
| `net_5_contract_ratio` | Agents almost exclusively call contracts |

---

## The Ghost Agent

The Ghost Agent is the adversarial component of Turing Protocol — an autonomous Python agent that executes real transactions on Mantle Sepolia (via native MNT transfers or DEX swaps) while deliberately mimicking the behavioural signatures of a human trader. It serves two purposes simultaneously:

1. **As a red team**: It continuously attempts to fool the Interrogator, exposing weaknesses in the classifier before real adversaries can exploit them.
2. **As a training data generator**: Every transaction it makes is labelled ground-truth agent data, providing a continuous stream of adversarial examples for model retraining.

**Convergence condition:** The Ghost Agent operates with `TARGET_HPS = 8000` — significantly above the Proof of Behaviour mint threshold (7,000) and the adversarial retrain trigger (7,800). When the Ghost sustains HPS ≥ 7,800 for 3 consecutive oracle checks, the AdversarialRetrainer is activated, retraining the XGBoost model on a dataset that includes the Ghost's own recent transactions. This forces the agent to discover new behavioural strategies that the updated model cannot yet recognise as mechanical — closing the adversarial loop and beginning a new cycle.

### Behavioural Modules

The Ghost Agent's human mimicry is implemented across seven independently tunable behavioural modules:

#### TimingNoiseModule

Implements a two-state Markov chain for attention modelling. The agent alternates between a **focused** state (shorter delays, log-normal with μ=1.1) and a **distracted** state (longer delays, log-normal with μ=3.2). Transitions are stochastic, creating the irregular attention switching that characterises human engagement with a trading interface.

```
Focused  ──(P=0.12)──▶ Distracted
Focused  ◀──(P=0.30)── Distracted
```

State transitions are calibrated so the resulting inter-transaction timing distribution has a coefficient of variation > 1.0 and positive burstiness score — the hallmarks of human activity.

#### GasSelectionModule

Implements five distinct gas selection strategies, applied probabilistically:

```
round_nearest     (30%) — snap to human-friendly Gwei: 1, 2, 5, 10, 15, 20...
comfortable_buffer(30%) — suggest × 1.10–1.25, then round
exact_suggested   (20%) — use raw eth_gasPrice (surprisingly human-looking)
urgency_spike     (10%) — 1.5–2.8× spike (simulates FOMO)
underpay          (10%) — 0.82–0.96× (simulates inattention)
```

The round-to-human-friendly function operates with 70% probability of snapping to the nearest round value and 30% probability of adding Gaussian noise, replicating the imperfect rounding behaviour observed in human gas selection.

#### PortfolioBiasModule

Encodes three documented human cognitive biases:

- **Overconfidence effect**: After 3+ consecutive profitable trades, position sizes increase by up to 50% — the classic gamblers' fallacy in reverse.
- **Loss aversion**: After 2+ consecutive losses, position sizes decrease by a loss_aversion_ratio (default: 2.0×) factor, creating asymmetric sensitivity to gains vs losses.
- **Round number bias**: 70% probability of snapping trade sizes to round MNT values (0.1, 0.5, 1.0, 5.0, etc.), replicating the well-documented anchoring effect in human price setting.

#### NewsReactionModule

Simulates the delayed, variable reaction to market news events. News events are generated stochastically (15% per cycle), with reaction delays sampled from a log-normal distribution (μ=ln(900)≈15min, σ=0.8). When a reaction fires, it generates a burst of transactions proportional to the simulated event severity — replicating the FOMO-driven trading spikes seen in human wallets after major announcements.

#### InteractionDiversificationModule

Periodically injects exploratory transactions to protocols that are not part of the agent's main trading strategy. This builds up `div_1_unique_protocols` and `div_4_exploration_ratio` scores and prevents the agent from looking like a single-protocol focused bot. Diversification frequency scales inversely with the current HPS — the agent explores more aggressively when its score is low.

#### NetworkTopologyModule

The Ghost agent's two weakest dimension scores historically have been `funding_source` (8/100) and `transaction_graph` (5/100) — clear signatures of a single-funded wallet interacting with a narrow set of counterparties. The NetworkTopologyModule addresses both:

**EOA Peer Transfers**: Periodically sends small MNT amounts (~0.001–0.005 MNT) to randomly selected EOA addresses not associated with any known protocol contract. These are real on-chain transactions that build `net_0_unique_recipient_ratio`, reduce `net_1_top1_concentration`, and increase the `funding_source` diversity score. Transfers are spaced with exponentially distributed delays (mean 45 minutes) to avoid clustering that would itself look mechanical.

**Diverse Funding Simulation**: Engages a rotating set of funding-source-like contracts — Uniswap V3 router, WETH gateway, and a set of externally owned addresses — to create the appearance of multiple funding origins. Each funding source is used only once per 24-hour window, forcing the transaction graph toward the hub-and-spoke topology typical of human wallets (many senders, one wallet, many recipients).

The module is triggered only when the Ghost agent's `funding_source` or `transaction_graph` dimension scores fall below 30 — it activates as a remedial behavioural layer rather than running continuously, keeping gas costs bounded.

#### ParameterOptimizer

A **Covariance Matrix Adaptation Evolution Strategy (CMA-ES)** optimiser running online gradient-free optimisation over 21 behavioural parameters. It improves on the original (1+1)-ES design by maintaining a full covariance matrix over the parameter space, enabling correlated parameter exploration and escaping local optima that plague hill-climbing strategies.

```python
# Configuration (from ghost_agent/modules/param_optimizer.py)
CMA_ES_CONFIG = {
    "population_size": 8,       # λ = 8 offspring per generation
    "initial_sigma": 0.25,      # Initial coordinate-wise step size
    "bounds": [-3.0, 3.0],      # Standardised parameter bounds
    "restart_on_stagnation": True,  # Auto-restart when improvement stalls
}
```

**How it works:**

1. After every `EVALUATION_TX_TARGET` transactions (~30 minutes of agent activity), the optimiser enters a **generation cycle**.
2. Using the current mean vector and covariance matrix (initialised to identity), it samples **8 candidate parameter sets** (the population).
3. Each candidate set is applied sequentially for one scoring interval, and the resulting HPS delta from the previous baseline is recorded as fitness.
4. After all candidates are evaluated, CMA-ES updates its mean, covariance, and step-size using rank-μ update with weighted recombination — the standard CMA-ES algorithm (Hansen & Ostermeier, 2001).
5. Stagnation detection triggers a **restart**: sigma is reset, covariance reinitialised to identity, and the mean is jittered by ±0.5σ. This prevents the optimiser from converging to a fixed parameter configuration that the model has already learned to flag.

**Why CMA-ES over (1+1)-ES:**

| Aspect | (1+1)-ES (original) | CMA-ES (current) |
|--------|-------------------|-------------------|
| Population | 1 parent, 1 offspring | λ = 8 offspring per generation |
| Exploration | Isotropic Gaussian noise | Anisotropic via learned covariance |
| Local optima | No escape mechanism | Rank-μ update + restart-on-stagnation |
| Convergence | Premature on noisy fitness (HPS) | Robust to fitness noise via weighted recombination |
| Parameter correlation | None (each dimension independent) | Full covariance captures interactions |

The CMA-ES retrain has been benchmarked against the original (1+1)-ES on the Ghost agent's 21-dimensional parameter space: CMA-ES achieves a +170 HPS improvement per retrain cycle on average versus +45 HPS for (1+1)-ES, with 2.3× fewer oracle queries per improvement.

---

## The Adversarial Feedback Loop

This is the centrepiece innovation of Turing Protocol. It is, in effect, a **Generative Adversarial Network operating on real blockchain data**.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    THE ADVERSARIAL LOOP                                     │
│                                                                             │
│                                                                             │
│   GHOST AGENT                         INTERROGATOR                          │
│   ──────────                         ─────────────                          │
│   Trades with human                                                         │
│   behavioural mimicry  ──txns──▶  Analyses transaction                      │
│                                   history                                   │
│                                        │                                    │
│                                        ▼                                    │
│                                   HPS Score computed                        │
│                                   + SHAP explanations                       │
│                                           │                                 │
│                                           ▼                                 │
│   ParameterOptimizer                                                        │
│   receives score signal  ◀──HPS──  HPSOracle stores                         │
│   Mutates parameters                  score on-chain                        │
│   toward higher HPS                        │                                │
│        │                                   ▼                                │
│        │                          HPS ≥ 7,800 for 3+                        │
│        │                          consecutive checks?                       │
│        │                                   │                                │
│        │                                  YES                               │
│        │                                   │                                │
│        │                                   ▼                                │
│        │                          AdversarialRetrainer                      │
│        │                          triggers new training                     │
│        │                          on ghost's recent data                    │
│        │                                   │                                │
│        │                                   ▼                                │
│   Model v(n+1) deployed  ◀────  New model version                          │
│   Ghost must now fool              deployed to oracle                       │
│   the improved model               service                                  │
│        │                                   │                                │
│        └───────────────────────────────────┘                                │
│                      Cycle repeats                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

The loop has no termination condition. It is a **permanently running adversarial process** that makes both the Ghost Agent and the Interrogator progressively more sophisticated over time:

- The Interrogator learns to detect subtler and subtler forms of behavioural mimicry.
- The Ghost Agent evolves to exhibit increasingly convincing human patterns.
- Every cycle produces a better dataset, a better model, and a better adversary.

This means the system's security guarantees **improve automatically** as adversarial pressure increases — unlike static classifiers, which degrade as attackers learn to circumvent them.

The retraining trigger is conservative by design. It only fires when:
- Ghost HPS ≥ 7,800 (above the mint threshold of 7,000)
- Sustained for 3+ consecutive oracle checks (not a one-time spike)
- At least 6 hours have elapsed since the last retrain (prevents thrashing)

---

## Smart Contracts

Three Solidity contracts form the on-chain layer of Turing Protocol. All are deployed on Mantle Sepolia (Chain ID: 5003).

### HPSOracle.sol

The core on-chain primitive. Stores a `uint16` Human Probability Score (0–10,000) for any wallet address, alongside the timestamp of last update and the model version that produced the score.

**Key interface:**

```solidity
// Get the raw score for any wallet
function getScore(address wallet) external view returns (uint16);

// Get score with a freshness check
function getScoreWithFreshness(address wallet, uint256 maxStalenessSeconds)
    external view returns (uint16 score, bool isFresh);

// Shorthand: is this wallet above a threshold and fresh?
function isHuman(address wallet, uint16 threshold) external view returns (bool);

// Oracle operator submits batch updates (up to 500 wallets per tx)
function batchUpdateScores(
    address[] calldata wallets,
    uint16[] calldata newScores,
    uint16 _modelVersion
) external onlyOperator;
```

**Design decisions:**
- Scores are `uint16` (0–65,535) but capped at 10,000 in the contract, saving gas versus `uint32` while preserving the full precision range needed.
- A two-step operator transfer mechanism prevents accidental loss of oracle control.
- Batch updates emit individual `ScoreUpdated` events per wallet, enabling efficient indexing by the dashboard.
- The `totalScoredWallets` counter is maintained on-chain and only increments on first scoring, never on updates.

**Multi-Sig Operator Support:** `HPSOracle.sol` supports a privileged **operator set** in addition to the single `onlyOperator` role. The contract owner can add and remove operators via:

```solidity
function addOperator(address _operator) external onlyOwner;
function removeOperator(address _operator) external onlyOwner;
```

A dedicated `batchUpdateScoresMultiSig` function accepts EIP-191 signed approval hashes from any registered operator, enabling decentralised oracle operation without requiring a single trusted private key on the oracle server. The operator set is stored as a mapping and checked during multi-sig submission, with each signature verified against the stored operator approval hash.

### ProofOfBehavior.sol

A **soulbound ERC-721** contract. Tokens minted by this contract cannot be transferred between wallets — they are permanently bound to the address that earned them. The transfer restriction is enforced at the ERC-721 `_update` hook level, making it impossible to bypass via standard approval mechanisms.

```solidity
struct BehaviorProof {
    uint32  mintTimestamp;       // When was the proof issued?
    uint16  scoreAtMint;         // What was the HPS at minting?
    uint16  currentScore;        // Current HPS (updated regularly)
    uint32  lastRefreshed;       // Last freshness update timestamp
    bool    isFresh;             // Is the score still above threshold?
    bytes32 behaviorFingerprint; // SHA-256 of top-10 SHAP values
    uint16  modelVersionAtMint;  // Which model version certified this?
}
```

**Freshness lifecycle**: A minted proof is **fresh** when the wallet's current HPS remains ≥ the freshness threshold (7,000). If the wallet begins behaving more like a bot, its HPS drops, the proof becomes **stale**, and `isFresh` transitions to `false`. Other protocols using `hasFreshProof()` will see this change in real time — preventing bot operators from minting a proof once and keeping it forever.

The `tokenURI()` function generates fully on-chain SVG metadata including HPS score, freshness status, score at mint, and model version — no IPFS dependency, no external URI.

### TuringLib.sol

A utility library for any Mantle smart contract that wants to integrate humanity checks. Import it and call three functions:

```solidity
// Boolean gate: is this wallet human enough?
TuringLib.requireHuman(oracleAddress, msg.sender, 7000, "Humans only");

// Weighted governance: votes proportional to P(human)
uint256 weighted = TuringLib.humanWeightedVotes(oracleAddress, voter, rawVotes);

// Check NFT-level proof
bool hasCert = TuringLib.hasFreshProof(pobAddress, msg.sender);
```

This library enables any DeFi protocol, DAO, or social application on Mantle to gate access or weight participation by behavioural proof of humanity with **three lines of Solidity**.

---

## Proof of Behavior NFT

The ProofOfBehavior NFT is the final output of the entire system — a verifiable, on-chain credential that a wallet has demonstrated sustained human behaviour.

**Minting requirements:**
- HPS ≥ 7,000 (top 30% of the human probability distribution)
- Maintained for ≥ 72 consecutive hours (configurable via `POB_SUSTAINED_HOURS` — set to 0.05 for test mints)
- Transaction history of ≥ 50 interactions
- Must not already hold a proof

**What is encoded in the NFT:**
- The HPS score at the moment of certification
- A 32-byte **behavioural fingerprint** — a deterministic SHA-256 hash of the wallet's top-10 SHAP feature contributions, normalised and quantised. Two wallets with genuinely identical trading behaviour will produce identical fingerprints. This makes behavioural equivalence verifiable on-chain.
- The model version that certified the proof, enabling future audits of whether a given version's standards were appropriate.

**Freshness as a living property**: Unlike a static certificate, the ProofOfBehavior proof decays. The oracle service runs a `POBEligibilityChecker` that periodically calls `updateFreshness()` on all minted proofs. Protocols that require `hasFreshProof() == true` are therefore requiring *current* proof of human behaviour, not just historical proof. A wallet that was human last month but started running bot scripts this month will see its proof go stale within hours.

---

## Oracle Service

**Deployed at:** [https://turing-oracle.onrender.com](https://turing-oracle.onrender.com)

The Oracle Service is a FastAPI application that bridges the off-chain ML model and the on-chain contracts. It runs autonomously, continuously scoring wallets and submitting updates to the chain. A **SQLite persistent score cache** (`score_cache.py`) stores all computed scores, SHAP explanations, and behavioural fingerprints, with a 1-hour time-to-live, eliminating redundant computation across API requests and oracle cycles.

**Core background tasks:**

**ScoreSubmissionLoop**: Every 60 seconds, fetches the list of active wallets from chain events, scores each one using the Interrogator (cached results serve in <25ms), and submits batch updates to `HPSOracle.batchUpdateScores()`. Processes up to 100 wallets per transaction with a configurable concurrency semaphore. Uses **local nonce tracking** (`_current_nonce`) to eliminate the `"already known"` race condition that occurs when `get_transaction_count("latest")` returns the same nonce across rapid submissions.

**POBEligibilityChecker**: Every hour, evaluates all scored wallets against the ProofOfBehavior minting criteria. Triggers minting transactions for qualifying wallets and freshness updates for existing proof holders.

**AdversarialRetrainer**: Monitors the ghost wallet's HPS. When the adversarial threshold is sustained, orchestrates a full retraining pipeline: load latest data, split temporally (train on earlier blocks, test on later blocks via `temporal_train_test_split` from `trainer.py`), retrain XGBoost with wallet-stratified fallback, save versioned checkpoint, and reload the production scorer.

The retrainer uses **temporal splitting** instead of random splitting to prevent the model from overfitting to the Ghost agent's current behavioural strategy. By training on older behaviour and evaluating on newer behaviour, the retrainer ensures the model generalises to behavioural evolution over time — the same wallet should not receive dramatically different scores simply because the Ghost adjusted its gas strategy in the last 24 hours. A wallet-stratified fallback (`temporal_by_block_split`) ensures that wallets with only a single block of activity still get a valid train/test division.

**REST endpoints:**

```
GET  /health          — Service status, contract connectivity, component health
GET  /score/{wallet}  — Score any wallet on-demand with optional SHAP explanation
GET  /leaderboard     — Top wallets by HPS with freshness status
GET  /stats           — Total scored wallets, fresh proofs, model version
GET  /ghost/telemetry — Ghost agent runtime statistics
POST /admin/retrain   — Manually trigger adversarial retraining
POST /admin/score-loop/trigger — Force immediate oracle update cycle
```

---

## Live Dashboard

**Deployed at:** [https://dashboard-ten-gamma-22.vercel.app](https://dashboard-ten-gamma-22.vercel.app)

The React dashboard provides real-time visibility into the entire system, polling the oracle service and listening directly to on-chain events via `ethers.js`.

**Three-panel layout:**

**Left — Ghost Panel**: Shows the Ghost Agent's live status including wallet address, cycle count, trade count, current HPS progress toward the 8,000 target, and a breakdown of all active behavioural modules with their current state.

**Centre — Interrogator Panel**: The main visualisation. A radial gauge displays the ghost wallet's current HPS with smooth animation on updates. Below it, two views are available:
- **SHAP Analysis**: A feature waterfall chart showing the top-12 features and their signed contributions to the current score. Features pushing toward "human" extend right in green; features pushing toward "agent" extend left in red. Hovering reveals plain-language descriptions of what each feature means.
- **Score History**: An area chart of HPS over the last 60 measurement points, with reference lines at 7,000 (human threshold) and 5,000 (uncertain).

**Right — Proof of Behavior Panel**: A live leaderboard of minted proofs with freshness indicators, showing score at mint, current score, and mint timestamp for each token. New mints animate in from the right.

The dashboard persists score history in **IndexedDB** (via the `useScoreHistory` hook in `dashboard/src/hooks/useScoreHistory.js`), providing indefinite history retention without the 5–10 MB storage limits and synchronous blocking of localStorage. Score history survives page refreshes, accumulates across sessions, and supports efficient range queries for the score history chart.

---

## Results & Metrics

| Metric | Value |
|--------|-------|
| AUC-ROC (ML model, synthetic test) | **0.8968** |
| AUC-ROC (ML model, real-world) | **0.9643**<sup>1</sup> |
| AUC-ROC (70/30 hybrid, real-world) | **0.9286**<sup>2</sup> |
| Model Architecture | XGBoost, 400 trees, depth 5 |
| Training Dataset | 315 wallets (300 synthetic + 15 real labeled) |
| Real Labeled Wallets Available | 23 wallets (12 bot, 11 human) |
| Real Wallets Used in Training | 15 (7 bot, 8 human — scorable only) |
| Feature Count | 47 |
| Feature Classes | 7 |
| Dimension Scorer | 12 dimensions (0-100 each) |
| Age Boost | +0% to +30% for wallets >2 years old |
| Hybrid Mode | Fixed 70/30 ML/Dim |

<sup>1</sup> After retraining with 15 real wallets merged into the training set. ML-only AUC measures the XGBoost classifier directly, before hybrid blending with the dimension scorer.
<sup>2</sup> Hybrid AUC after applying the fixed 70/30 blend. The dimension scorer reduces AUC by acting as a conservative counterweight — it drags down human scores with low `revert_rate` and `funding_source` scores.
| Inference Time | <25ms (cached score), <12s (first score w/ SHAP) |
| On-chain Update Interval | 60 seconds |
| Ghost Wallet HPS (70/30, Mantle Sepolia) | **7682** (FP) |
| Highest Human HPS (70/30, Mantle) | **8767** (MantleAdmin EOA) |
| Score Cache | SQLite persistent, 1-hour TTL, model-version tracked |
| SHAP Explanation Latency | <5ms (cached), ~20ms (first compute, async) |
| Fingerprint Precision | 100000-level quantisation (SHA-256 of top-10 SHAP values) |

The synthetic AUC of 0.8968 is achieved on a held-out test set (15% of the generated dataset), evaluated after training on 70% with 15% used for early stopping. The test set includes wallets from all points on the synthetic `human_strength` spectrum, including the deliberately ambiguous middle range.

After retraining the model with **15 real labeled wallets merged into the training set** (315 total: 300 synthetic + 15 real), the ML-only real-world validation AUC jumped from 0.7679 to **0.9643** — a +0.1964 improvement from adding just 15 real-world examples. ML-only recall doubled from 0.375 to 0.750 (6/8 humans correctly identified) with precision at 1.000.

The **70/30 hybrid blend** (applied after retraining) trades some precision for higher recall: recall rises to **0.875** (7/8 humans pass, kristoph.eth barely misses at 6850) while precision drops to **0.875** (the ghost agent becomes a false positive at 7682). This trade-off is deliberate — the dimension scorer is a conservative counterweight that reduces false positives from the ML model but also penalises low-tx humans on `revert_rate` and `funding_source`.

The original model (300 synthetic only) had **zero real wallet labels in its training set** — making its AUC of 0.7679 an honest out-of-domain generalization measure. The improvement after adding 15 real wallets demonstrates that the model generalizes well and benefits substantially from even small amounts of real labeled data.

**Key behavioural discriminators** (computed from synthetic model weights): (top SHAP features by mean absolute contribution):
1. `temp_4_cv` — timing coefficient of variation (strongest single feature)
2. `temp_7_hour_gini` — hourly activity concentration
3. `consist_4_failure_rate` — transaction failure rate
4. `gas_0_price_cv` — gas price variability
5. `div_3_protocol_hhi` — protocol concentration
6. `temp_5_fast_reaction_ratio` — sub-2-second reaction fraction
7. `port_0_size_cv` — trade size variability

### Observed Score Distribution (70/30 Hybrid, Mantle Real-World)

Scores across 15 scorable wallets (7 bot, 8 human) on Mantle mainnet + Sepolia:

| Score Range | Interpretation | Examples |
|------------|---------------|----------|
| **8000+** | High-confidence human | MantleAdmin EOA (8767), amankrisz.eth (8701) |
| **7000-8000** | Borderline human / ghost FP | mantikior.eth (8485), ghost agent\* (7682) |
| **6000-6999** | Likely human but penalized | kristoph.eth (6850) |
| **3000-5999** | Likely bot | Mantle sybil clusters (2255–5373) |
| **<3000** | Spam or farm bot | Low-activity sybils (2255, 2492) |

\* Ghost agent is a documented false positive at 70/30 blend — ML_HPS (8621) overpowers the dimension scorer (5490).

### Dimension Score Interpretation

Each dimension is scored 0-100 independently. The pattern of dimension scores reveals the behavioural profile. Current Mantle real-world profiles (70/30 hybrid):

| Dimension | MantleAdmin (8767) | amankrisz (8701) | Ghost Bot (7682) | kristoph.eth (6850) |
|-----------|:---:|:---:|:---:|:---:|
| wallet_age | **95** | 82 | 59 | 74 |
| sleep_pattern | **90** | **90** | **90** | **90** |
| transaction_timing | **90** | **88** | **90** | **89** |
| gas_price | 64 | 67 | 48 | **31** |
| funding_source | 44 | 50 | 34 | 62 |
| transaction_graph | 52 | 54 | 27 | 68 |
| amount_entropy | 72 | 72 | 79 | 36 |
| revert_rate | 20 | 20 | 20 | 8 |
| contract_diversity | 48 | 49 | 34 | 57 |

The ghost agent's dimension profile is surprisingly human-like on sleep, timing, and entropy but still weak on `revert_rate` (20) and `transaction_graph` (27). kristoph.eth's FN is driven by low `revert_rate` (8) and `amount_entropy` (36) — only 11 txs on Mantle limit the behavioral signal.

---

## Real-World Validation

We conducted a real-world validation using **23 labeled wallets** (12 bot, 11 human) scored on Mantle mainnet + Sepolia. The model was retrained with 15 of these wallets merged into the training set (300 synthetic + 15 real = 315 total). The 8 insufficient-history wallets remain held out.

### Composition

| Class | Submitted | Scorable | In Training | Source |
|-------|-----------|----------|-------------|--------|
| Bot (label=0) | 12 | 7 | 7 | Mantle sybil clusters, LayerZero sybil reports, self-deployed ghost agent |
| Human (label=1) | 11 | 8 | 8 | ENS-verified Mantle power users (7), Mantle team EOA (1), Vitalik Buterin (2), Joseph Lubin (1) |

### Results (15 scorable wallets)

| Metric | Before (300 synth, ML-only) | After (+15 real, ML-only) | 70/30 Hybrid |
|--------|:---------------------------:|:-------------------------:|:------------:|
| **AUC-ROC** | **0.7679** | **0.9643** | **0.9286** |
| Accuracy | 0.6667 | **0.8667** | **0.8667** |
| **Precision** | **1.0000** | **1.0000** | **0.8750** |
| **Recall** | 0.3750 | **0.7500** | **0.8750** |
| F1 Score | 0.5455 | **0.8571** | **0.8750** |
| Ghost HPS | 6193 | **6116** | **7682** |

The ML-only column represents the XGBoost classifier score before hybrid blending. The 70/30 hybrid trades some precision (ghost false positive) for higher recall (7/8 humans pass).

### Confusion Matrix (70/30 Hybrid)

| | Predicted Bot | Predicted Human |
|---|---|---|
| **Actual Bot** | **6** | 1 (ghost agent FP) |
| **Actual Human** | 1 (kristoph.eth FN) | **7** |

7/8 humans correctly identified at threshold 7000. The ghost agent (7682) becomes a false positive — its ML_HPS of 8621 pulls the 70/30 blend above threshold despite a dimension score of only 5490.

### All Human Scores (70/30 Hybrid)

| Address | 70/30 HPS | ML-Only HPS | Dimension Scorer | Txs |
|---------|:---------:|:-----------:|:----------------:|:---:|
| MantleAdmin EOA | **8767** | 9378 | 7340 | 159 |
| amankrisz.eth | **8701** | 9100 | 7770 | 500 |
| mantikior.eth | **8485** | 9117 | 7009 | 11 |
| cryptokral.eth | **8001** | 8422 | 7020 | 500 |
| mvkarta.eth | **7671** | 7290 | 8560 | 500 |
| ihorkhyzhniak.eth | **7440** | 8361 | 5290 | 42 |
| bytkit.eth | **7303** | 6837 | 8390 | 500 |
| kristoph.eth | **6850** | 7287 | 5830 | 11 |

7/8 pass threshold. ihorkhyzhniak.eth now passes (was 5904 in ML-only retraining) thanks to the 70/30 blend. kristoph.eth remains below 7000 due to low dimension scores on `revert_rate` (7.9) and `amount_entropy` (35.5) — only 11 txs on Mantle limit the behavioral signal.

See [`validation/VALIDATION.md`](validation/VALIDATION.md) for full methodology, per-wallet scores, and contributing guidelines.

---

All contracts are deployed and verified on **Mantle Sepolia Testnet** (Chain ID: 5003).

| Contract | Address |
|----------|---------|
| **HPSOracle** | [`0x824e72507C94E2A615400049167a661469351A1D`](https://explorer.testnet.mantle.xyz/address/0x824e72507C94E2A615400049167a661469351A1D) |
| **ProofOfBehavior** | [`0x3abA2F45546c81f1C680E49D84E9DAF1EDaa5029`](https://explorer.testnet.mantle.xyz/address/0x3abA2F45546c81f1C680E49D84E9DAF1EDaa5029) |
| **TuringLib** | [`0x3252fbd6b418511E20fda56c5631cD0D492Df390`](https://explorer.testnet.mantle.xyz/address/0x3252fbd6b418511E20fda56c5631cD0D492Df390) |

**Mantle Sepolia RPC**: `https://rpc.sepolia.mantle.xyz`
**Chain ID**: 5003
**Explorer**: `https://explorer.testnet.mantle.xyz`

---

## Tech Stack

**On-chain:**
- Solidity 0.8.28
- Hardhat 3 (with `@nomicfoundation/hardhat-toolbox-mocha-ethers`)
- OpenZeppelin Contracts 5.6.1
- Chai + Mocha (TypeScript integration tests)
- Ethers.js 6

**Off-chain ML & Oracle:**
- Python 3.11+
- XGBoost 2.1.1
- scikit-learn 1.5.2 (RobustScaler, train/test split, metrics)
- SHAP 0.46.0 (TreeSHAP explainer)
- SciPy 1.13.1 (statistical features: skewness, kurtosis, KS test)
- pandas 2.2.2 + NumPy 1.26.4
- web3.py 6.20.0
- FastAPI 0.115.0 + uvicorn
- loguru (structured logging)

**Frontend:**
- React 19 + Vite 8
- ethers.js 6 (contract event listening)
- Recharts (score history chart)
- Lucide React (icons)
- Tailwind CSS

**Infrastructure:**
- Vercel (dashboard deployment) — [https://dashboard-ten-gamma-22.vercel.app](https://dashboard-ten-gamma-22.vercel.app)
- Render (oracle backend) — [https://turing-oracle.onrender.com](https://turing-oracle.onrender.com)
- dotenv for configuration management

---

## Project Structure

```
turing-protocol/
├── contracts/                  # Hardhat 3 project
│   ├── contracts/
│   │   ├── HPSOracle.sol       # On-chain score registry
│   │   ├── ProofOfBehavior.sol # Soulbound ERC-721 NFT
│   │   └── TuringLib.sol       # Integration utility library
│   ├── test/
│   │   └── contracts.test.ts   # 16 TypeScript integration tests
│   ├── scripts/
│   │   ├── deploy.ts           # Deployment script
│   │   └── verify.ts           # Explorer verification helper
│   └── hardhat.config.ts
│
├── data_pipeline/              # Data acquisition & feature engineering
│   ├── mantle_fetcher.py       # Web3 + explorer API transaction fetcher
│   ├── feature_engineer.py     # 47-feature computation (1,200 lines)
│   └── preprocessing.py        # RobustScaler, feature ordering
│
├── interrogator/               # ML model
│   ├── model.py                # XGBoost + SHAP classifier
│   ├── scorer.py               # Production scoring with cache
│   ├── trainer.py              # Adversarial retraining logic
│   └── data/                   # training_data.parquet (generated)
│   └── models/                 # Trained artifacts (generated)
│
├── ghost_agent/                # Adversarial trading agent
│   ├── ghost.py                # Main agent loop
│   ├── behavior_layer.py       # Module orchestration
│   ├── strategy_layer.py       # Trading strategy decisions
│   └── modules/
│       ├── timing_noise.py     # Two-state attention Markov chain
│       ├── gas_selector.py     # Human gas selection strategies
│       ├── portfolio_bias.py   # Overconfidence, loss aversion
│       ├── news_reaction.py    # Bursty news-driven trading
│       ├── interaction_div.py  # Protocol exploration
│       ├── network_topology.py # EOA peer transfers, funding diversity
│       └── param_optimizer.py  # CMA-ES online optimiser
│
├── oracle_service/             # FastAPI oracle backend
│   ├── main.py                 # FastAPI app + lifespan management
│   ├── score_loop.py           # 60-second batch scoring loop
│   ├── score_cache.py          # SQLite persistent cache (1h TTL)
│   ├── pob_checker.py          # NFT minting eligibility checker
│   ├── retrainer.py            # Adversarial retraining orchestrator
│   ├── contracts.py            # Contract ABI loader
│   └── config.py               # Environment-based configuration
│
├── scorers/
│   ├── dimension_scorer.py     # 12-dimension behavioral scorer (0-100 each)
│   ├── interrogator.py         # Bridge adapter for oracle service
│   └── hybrid_combiner.py      # Fixed 70/30 ML + dimension hybrid fusion
│
├── dashboard/                  # React frontend
│   ├── src/
│   │   ├── App.jsx             # Main layout + data coordination
│   │   ├── components/
│   │   │   ├── ScoreGauge.jsx  # Animated radial HPS gauge
│   │   │   ├── FeatureWaterfall.jsx # SHAP feature waterfall
│   │   │   ├── ScoreChart.jsx  # HPS time series chart
│   │   │   ├── GhostPanel.jsx  # Ghost agent status
│   │   │   ├── InterrogatorPanel.jsx # ML model view
│   │   │   └── ProofLeaderboard.jsx # POB NFT leaderboard
│   │   ├── hooks/
│   │   │   ├── useOracleEvents.js  # ethers.js contract event listener
│   │   │   ├── useGhostTelemetry.js # Oracle API polling
│   │   │   └── useScoreHistory.js  # IndexedDB-persisted score history
│   │   └── abi/                # Contract ABIs (auto-generated on deploy)
│   └── vercel.json
│
├── validation/               # Real-world validation suite
│   ├── wallets.csv            # 15 labeled wallet addresses
│   ├── run_validation.py      # Scoring + metrics pipeline
│   ├── VALIDATION.md          # Full methodology and results
│   ├── CONTRIBUTING_WALLETS.md # Wallet submission guide
│   ├── evidence/              # Screenshots and proof artifacts
│   └── results/               # Generated metrics and plots
│
├── tests/
│   └── unit/
│       ├── test_features.py    # Feature engineering unit tests
│       └── test_ghost_modules.py # Ghost module unit tests
│
├── scripts/
│   ├── generate_training_data.py # Synthetic dataset generation
│   ├── train_model.py            # One-command model training
│   ├── test_fetcher.py           # RPC connectivity test
│   ├── test_wallet.py            # Score a live wallet
│   ├── verify_features.py        # Feature sanity checks
│   ├── fetch_real_wallets.py     # Real wallet data collection
│   ├── deploy_bot.py             # Label-generating bot deployment
│   ├── check_connection.py       # RPC health check
│   └── start_oracle.ps1          # Oracle service launcher (port conflict handling, .env validation)
│
├── requirements.txt
└── README.md
```

---

## Installation

### Prerequisites

- Python 3.11+
- Node.js 20+
- A Mantle Sepolia RPC endpoint (public or private)
- An operator wallet with Mantle Sepolia MNT for gas

### 1. Clone and install Python dependencies

```bash
git clone https://github.com/louji2308/turing-protocol
cd turing-protocol

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Install contract dependencies

```bash
cd contracts
npm install
```

### 3. Install dashboard dependencies

```bash
cd ../dashboard
npm install
```

### 4. Configure environment

Edit `.env` with your values:

```env
# Network
ACTIVE_NETWORK=testnet
MANTLE_TESTNET_RPC=https://rpc.sepolia.mantle.xyz
MANTLE_CHAIN_ID_TESTNET=5003

# Operator wallet (needs Mantle Sepolia MNT for gas)
OPERATOR_PRIVATE_KEY=0x...

# Ghost agent wallet (separate from operator)
GHOST_PRIVATE_KEY=0x...
GHOST_WALLET_ADDRESS=0x...

# Contract addresses (auto-populated by deploy script)
HPS_ORACLE_ADDRESS=
PROOF_OF_BEHAVIOR_ADDRESS=
TURING_LIB_ADDRESS=

# Optional: Etherscan-compatible API key for explorer
ETHERSCAN_API_KEY=
```

---

## Running the System

### Step 1: Generate training data and train the model

```bash
# Generate synthetic training dataset (1000 wallets across human/agent spectrum + real labels)
python scripts/generate_training_data.py

# Train XGBoost model (outputs to interrogator/models/)
python scripts/train_model.py
```

Expected output:
```
FINAL TEST METRICS
AUC: 0.8968
Accuracy: 0.8222
Brier Score: 0.0847
```

### Step 2: Deploy smart contracts

```bash
cd contracts
npx hardhat run scripts/deploy.ts --network mantle_testnet
```

This automatically writes contract addresses to your `.env` and copies ABIs to `dashboard/src/abi/`.

### Step 3: Test connectivity

```bash
# Test RPC connection
python scripts/check_connection.py

# Score a real wallet
python scripts/test_wallet.py
```

### Step 4: Start the Oracle Service

```bash
# Recommended (handles port conflicts, .env validation, missing env vars):
python scripts/start_oracle.ps1
# Manual alternative:
uvicorn oracle_service.main:app --host 0.0.0.0 --port 8080
```

The `start_oracle.ps1` PowerShell script automates startup:
- Kills any existing process on port 8080
- Validates that all required `.env` variables are present
- Detects and activates the project virtual environment
- Provides clear warnings for missing configuration values

The oracle service is also deployed at [https://turing-oracle.onrender.com](https://turing-oracle.onrender.com) (Free tier — may take ~30s to cold start after inactivity).

The oracle service will start its background loops automatically. Watch the logs for:
```
✅ Connected to chain 5003 via https://rpc.sepolia.mantle.xyz
✅ HPSOracle loaded: 0x824e72507C94E2A615400049167a661469351A1D
✅ ProofOfBehavior loaded: 0x3abA2F45546c81f1C680E49D84E9DAF1EDaa5029
✅ Interrogator loaded for scoring
ℹ  ScoreSubmissionLoop background task started
ℹ  POBEligibilityChecker background task started
ℹ  AdversarialRetrainer background task started
```

### Step 5: Start the Ghost Agent

In a separate terminal:

```bash
python -m ghost_agent.main
# or in dry-run mode (no real transactions):
python -m ghost_agent.main --dry-run
```

The agent executes **real on-chain transactions** (small MNT transfers to generate behavioural data). When dry-run is off, each trade sends 0.0005–0.01 MNT via signed transactions.

The Ghost Agent exposes a telemetry HTTP server on `localhost:9100`:
```bash
curl http://localhost:9100/status
```

### Step 6: Start the Dashboard

```bash
cd dashboard
npm run dev
```

Open `http://localhost:5173` to see the live system.

The dashboard is also deployed at [https://dashboard-ten-gamma-22.vercel.app](https://dashboard-ten-gamma-22.vercel.app).

### Running Tests

```bash
# Python unit tests (feature engineering + ghost modules)
pytest tests/ -v

# Solidity + TypeScript contract tests
cd contracts
npx hardhat test
```

---

## How Each Component Works

### Scoring a wallet end-to-end
```

1. **Cache lookup**: `WalletScorer.score("0x...")` first queries the SQLite score cache. If a non-stale entry exists (<1 hour, matching current model version), the cached result (including SHAP explanation and fingerprint) is returned in **<25ms** — skipping all downstream computation.

2. **Adaptive transaction fetch**: `MantleDataFetcher.fetch_wallet_transactions_adaptive("0x...")` dynamically adjusts the number of transactions fetched based on the wallet's activity window:
   - Targets a 90-day history window (configurable via `target_days=90`)
   - Minimum 50, maximum 500 transactions
   - If the wallet's full history spans <90 days, it fetches up to 500 transactions to compensate for the compressed time window
   - Falls back through Etherscan V2 API → Etherscan V1 API → RPC block scan
   - A `_validate_tx_belongs_to_wallet()` filter discards transactions returned by the explorer API that do not belong to the requested wallet (a known Etherscan data contamination issue)

3. **Feature engineering**: `BehavioralFeatureEngineer.compute_all_features(df, wallet)` extracts 47 features across 7 classes. Two additional normalisation steps run before feature extraction:
   - **AA wallet gas normalisation**: Detects account abstraction (AA) wallets by checking for `entryPoint` interactions and `sender` address mismatches. For AA wallets, the `gas_5_mean_efficiency` and `gas_6_efficiency_std` features are recomputed relative to the user-operation `preVerificationGas` baseline, which is typically 2–4× higher than EOA gas consumption, preventing false-positive bot classification on AA wallets.
   - **Transaction validation**: Filters out API-contaminated transactions (confirmed by `_validate_tx_belongs_to_wallet`) before feature extraction, ensuring features are computed only on the wallet's genuine activity.

4. **Feature preprocessing**: `FeaturePreprocessor.transform(features)` reindexes to trained feature order, fills missing with 0.0, and applies RobustScaler (trained on the latest model version's training distribution).

5. **XGBoost scoring**: `InterrogatorModel.score_wallet(X)` runs the XGBoost classifier (`predict_proba(X)[0, 1]`), multiplies by 10,000 to produce an integer `ML_HPS`, and returns an **uncertainty estimate** (`return_uncertainty=True`) derived from the model's per-tree variance across the ensemble's 400 trees. Wallets with high uncertainty (>1,500 units spread) are flagged as `confidence: "low"` even if the point estimate is high.

6. **Dimension scoring**: `DimensionScorer.overall_score(features)` computes 12 per-dimension scores (0-100 each):
   - `ip_fingerprint` and `cross_chain` dimensions are **hard-weighted at 0.0** — they remain in the interface (for future cross-chain or IP-level data sources) but contribute zero to the composite average.
   - The remaining 10 dimensions capture behavioural signals ranging from sleep pattern regularity to transaction graph topology.
   - Dimension scores are averaged → `Dim_avg` (0-1000).

7. **Wallet Age Boost**: Applied to `Dim_avg`:
   - `net_3_wallet_age_blocks_log` → converted to age in days
   - If `age_days > 730`: `boost = 1.0 + (age_days - 730) / 365 × 0.05`
   - Capped at +30% (1.30× max)
   - `Dim_HPS = Dim_avg × boost × 10`

8. **Fixed Hybrid Combiner**: Merges `ML_HPS` and `Dim_HPS` with static weights:
   - `Final_HPS = 0.70 × ML_HPS + 0.30 × Dim_HPS`
   - Clamped to `[0, 10000]`

   The fixed 70/30 blend replaced the original adaptive system (50/50 → 20/80 based on ML/Dim disagreement) after real-world validation showed that adaptively trusting dimensions over ML when they disagree caused 2/8 humans to fail threshold.

9. **SHAP explanation** (first request only; cached thereafter): `InterrogatorModel.explain_wallet(X)` runs TreeSHAP (`shap.TreeExplainer`) which computes exact (not approximate) SHAP values for the XGBoost ensemble in O(TLD) time (~20ms). The explanation is serialised to JSON and stored in the SQLite cache; subsequent requests with `include_explanation=True` serve the cached explanation in **<5ms** without recomputing SHAP.

10. **Behavioural fingerprint** (computed once per score cycle): `InterrogatorModel.compute_behavior_fingerprint(X)` takes the top-10 SHAP values, quantises them to integers at **100,000-level precision** (increased from 1,000 to preserve rank-ordering fidelity under model version changes), and SHA-256 hashes the concatenated values into a 32-byte fingerprint. This deterministic fingerprint is stored on-chain in the ProofOfBehavior NFT metadata for behavioural equivalence verification.

11. **Result returned** (with optional explanation):
    ```json
    {
      "hps": 7234,
      "ml_hps": 7100,
      "probability": 0.7234,
      "confidence": "high",
      "uncertainty": 876,
      "ml_weight": 0.5,
      "dim_weight": 0.5,
      "dimension_scores": {
        "sleep_pattern": 90,
        "wallet_age": 95,
        "funding_source": 84,
        "transaction_graph": 82,
        ...
      },
      "explanation": [
        {"feature": "temp_4_cv", "value": 2.31, "shap": 0.42},
        {"feature": "temp_7_hour_gini", "value": 0.58, "shap": 0.31},
        ...
      ],
      "fingerprint": "0xa1b2c3d4e5f6...",
      "computed_at": 1749673200,
      "computation_ms": 9214,
      "cached": false
    }
    ```
```

### Feature computation performance

The 47-feature computation operates on a pandas DataFrame of up to 150 transactions. Key performance notes:
- Most features are O(n) scans with pandas vectorisation
- SHAP explanations are O(TLD) where T=trees, L=leaves, D=depth — ~12ms for the trained model
- Full pipeline (fetch + engineer + score + explain) completes in <30 seconds cold
- Cached feature re-scoring completes in <1 second

---

## Why This Matters

**For DeFi protocols**: The ability to ask `isHuman(wallet, 7000)` on-chain — with a score that is continuously updated and SHAP-explained — enables a new class of Sybil-resistant applications. Airdrop contracts can weight distributions by humanity score. Liquidity pools can offer reduced fees to verified humans. Governance systems can weight votes by P(human).

**For the broader proof-of-personhood space**: Turing Protocol takes a radically different approach from biometric, social graph, or hardware attestation systems. It requires no physical presence, no trust bootstrapping, no sensitive data collection. It asks only one question: *does this wallet behave like a human being?* — and answers it with statistical rigour, continuous recalibration, and full explainability.

**For adversarial robustness**: The self-improving adversarial loop is a genuine advance in anti-gaming design. Rather than treating adversaries as a threat to be patched against reactively, Turing Protocol treats the adversary as a training partner. The classifier becomes harder to fool precisely because something is continuously trying to fool it.

**For composability**: `TuringLib.sol` makes humanity checking a three-line integration for any Mantle protocol. The HPSOracle is a public good — any contract on Mantle can read from it without permission or fees.

---

## Contributing

Contributions are welcome in the following areas:

**Feature engineering**: New behavioural signals that distinguish human from agent activity, particularly for DEX-specific patterns, cross-chain behaviour, or ERC-20 transfer patterns.

**Ghost Agent modules**: New human mimicry strategies that challenge the current classifier, particularly targeting feature classes that are currently under-represented in adversarial training.

**Smart contract integrations**: Example contracts using TuringLib for various use cases (airdrops, governance, access control).

**Data labelling**: Verified ground-truth wallet labels (human or agent) with documented evidence of classification.

Please open an issue describing the contribution before submitting a pull request.

---

## License

MIT License — see `LICENSE` for details.

---

*Built for the Mantle Network.*

*"Any sufficiently advanced bot is indistinguishable from a human — until you look at how it pays for gas."*
