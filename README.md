# TURING PROTOCOL
### On-Chain Behavioral Proof of Humanity for the Mantle Network

> *"Can a machine prove it is not a machine?"*
> — The question at the heart of every Sybil-resistant system ever built.

[![Mantle Testnet](https://img.shields.io/badge/Network-Mantle%20Sepolia-00D4FF?style=flat-square)](https://explorer.testnet.mantle.xyz)
[![Model AUC](https://img.shields.io/badge/Model%20AUC-0.8968-brightgreen?style=flat-square)](#results)
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
│  ┌──────────────┐     ┌───────────────┐     ┌──────────────────┐   │
│  │  GHOST AGENT │────▶│  THE          │────▶│  HPS ORACLE      │   │
│  │  (Adversary) │     │  INTERROGATOR │     │  (On-chain)      │   │
│  │              │◀────│  (XGBoost+    │     │                  │   │
│  │  Adapts when │     │   SHAP)       │     │  Scores 0-10000  │   │
│  │  detected    │     │               │     │  for any wallet  │   │
│  └──────────────┘     └───────────────┘     └────────┬─────────┘   │
│                                                       │             │
│                                              ┌────────▼─────────┐  │
│                                              │  PROOF OF        │  │
│                                              │  BEHAVIOR NFT    │  │
│                                              │  (Soulbound ERC- │  │
│                                              │  721, non-xfer)  │  │
│                                              └──────────────────┘  │
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
│  └───────────┘  │   │  │                                                │   │  │
│                 │   │  │  MantleDataFetcher → FeatureEngineer           │   │  │
│  ┌───────────┐  │   │  │  (47 features)       (7 feature classes)       │   │  │
│  │ProofOf    │◀─┼── │  │                                                │   │  │
│  │Behavior   │  │   │  │  FeaturePreprocessor → InterrogatorModel       │   │  │
│  │(Soulbound │  │   │  │  (RobustScaler)       (XGBoost + SHAP)         │   │  │
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

The Ghost Agent is the adversarial component of Turing Protocol — an autonomous Python agent that executes real transactions on Mantle Sepolia while deliberately mimicking the behavioural signatures of a human trader. It serves two purposes simultaneously:

1. **As a red team**: It continuously attempts to fool the Interrogator, exposing weaknesses in the classifier before real adversaries can exploit them.
2. **As a training data generator**: Every transaction it makes is labelled ground-truth agent data, providing a continuous stream of adversarial examples for model retraining.

### Behavioural Modules

The Ghost Agent's human mimicry is implemented across six independently tunable behavioural modules:

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

#### ParameterOptimizer

An evolutionary optimiser running online gradient-free optimisation over 21 behavioural parameters. It works as follows:

1. Every `EVALUATION_TX_TARGET` transactions, it generates a **mutated copy** of the current parameter set (1–3 parameters perturbed by Gaussian noise).
2. It applies the mutation and waits for the oracle to rescore the wallet.
3. If the new HPS improves by ≥ 50 points over the previous best, the mutation is **accepted**.
4. Otherwise, the agent **reverts** to the previous best parameters.

This is effectively a (1+1)-ES (Evolution Strategy) operating on the HPS signal, continuously hill-climbing toward a more convincingly human parameter configuration.

---

## The Adversarial Feedback Loop

This is the centrepiece innovation of Turing Protocol. It is, in effect, a **Generative Adversarial Network operating on real blockchain data**.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    THE ADVERSARIAL LOOP                                     │
│                                                                             │
│                                                                             │
│   GHOST AGENT                         INTERROGATOR                         │
│   ──────────                         ─────────────                         │
│   Trades with human                                                         │
│   behavioural mimicry  ──txns──▶  Analyses transaction                     │
│                                   history                                   │
│                                        │                                    │
│                                        ▼                                    │
│                                   HPS Score computed                        │
│                                   + SHAP explanations                       │
│                                        │                                    │
│                                        ▼                                    │
│   ParameterOptimizer                                                        │
│   receives score signal  ◀──HPS──  HPSOracle stores                        │
│   Mutates parameters                  score on-chain                        │
│   toward higher HPS                        │                                │
│        │                                   ▼                                │
│        │                          HPS ≥ 7,800 for 3+                       │
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
│   Ghost must now fool              deployed to oracle                        │
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
- Maintained for ≥ 72 consecutive hours
- Transaction history of ≥ 50 interactions
- Must not already hold a proof

**What is encoded in the NFT:**
- The HPS score at the moment of certification
- A 32-byte **behavioural fingerprint** — a deterministic SHA-256 hash of the wallet's top-10 SHAP feature contributions, normalised and quantised. Two wallets with genuinely identical trading behaviour will produce identical fingerprints. This makes behavioural equivalence verifiable on-chain.
- The model version that certified the proof, enabling future audits of whether a given version's standards were appropriate.

**Freshness as a living property**: Unlike a static certificate, the ProofOfBehavior proof decays. The oracle service runs a `POBEligibilityChecker` that periodically calls `updateFreshness()` on all minted proofs. Protocols that require `hasFreshProof() == true` are therefore requiring *current* proof of human behaviour, not just historical proof. A wallet that was human last month but started running bot scripts this month will see its proof go stale within hours.

---

## Oracle Service

The Oracle Service is a FastAPI application that bridges the off-chain ML model and the on-chain contracts. It runs autonomously, continuously scoring wallets and submitting updates to the chain.

**Core background tasks:**

**ScoreSubmissionLoop**: Every 15 minutes, fetches the list of active wallets from chain events, scores each one using the Interrogator, and submits batch updates to `HPSOracle.batchUpdateScores()`. Processes up to 100 wallets per transaction with a configurable concurrency semaphore.

**POBEligibilityChecker**: Every hour, evaluates all scored wallets against the ProofOfBehavior minting criteria. Triggers minting transactions for qualifying wallets and freshness updates for existing proof holders.

**AdversarialRetrainer**: Monitors the ghost wallet's HPS. When the adversarial threshold is sustained, orchestrates a full retraining pipeline: load latest data, retrain XGBoost, save versioned checkpoint, reload the production scorer.

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

The React dashboard provides real-time visibility into the entire system, polling the oracle service and listening directly to on-chain events via `ethers.js`.

**Three-panel layout:**

**Left — Ghost Panel**: Shows the Ghost Agent's live status including wallet address, cycle count, trade count, current HPS progress toward the 7,200 target, and a breakdown of all active behavioural modules with their current state.

**Centre — Interrogator Panel**: The main visualisation. A radial gauge displays the ghost wallet's current HPS with smooth animation on updates. Below it, two views are available:
- **SHAP Analysis**: A feature waterfall chart showing the top-12 features and their signed contributions to the current score. Features pushing toward "human" extend right in green; features pushing toward "agent" extend left in red. Hovering reveals plain-language descriptions of what each feature means.
- **Score History**: An area chart of HPS over the last 60 measurement points, with reference lines at 7,000 (human threshold) and 5,000 (uncertain).

**Right — Proof of Behavior Panel**: A live leaderboard of minted proofs with freshness indicators, showing score at mint, current score, and mint timestamp for each token. New mints animate in from the right.

The dashboard persists score history in localStorage (24-hour rolling window) so history survives page refreshes and accumulates between sessions.

---

## Results & Metrics

| Metric | Value |
|--------|-------|
| AUC-ROC | **0.8968** |
| Model Architecture | XGBoost, 400 trees, depth 5 |
| Training Dataset | 300 wallets (synthetic spectrum) |
| Feature Count | 47 |
| Feature Classes | 7 |
| Inference Time | <30s (first score), <1s (cached) |
| On-chain Update Interval | 15 minutes |
| Ghost Agent Adversarial Target | HPS 7,200 |
| Minting Threshold | HPS ≥ 7,000 for ≥ 72 hours |

The AUC of 0.8968 is achieved on a held-out test set (15% of dataset), evaluated after training on 70% with 15% used for early stopping. The test set includes wallets from all points on the synthetic `human_strength` spectrum, including the deliberately ambiguous middle range.

**Key behavioural discriminators** (top SHAP features by mean absolute contribution):
1. `temp_4_cv` — timing coefficient of variation (strongest single feature)
2. `temp_7_hour_gini` — hourly activity concentration
3. `consist_4_failure_rate` — transaction failure rate
4. `gas_0_price_cv` — gas price variability
5. `div_3_protocol_hhi` — protocol concentration
6. `temp_5_fast_reaction_ratio` — sub-2-second reaction fraction
7. `port_0_size_cv` — trade size variability

---

## Deployed Contracts

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
- Vercel (dashboard deployment)
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
│       └── param_optimizer.py  # (1+1)-ES online optimiser
│
├── oracle_service/             # FastAPI oracle backend
│   ├── main.py                 # FastAPI app + lifespan management
│   ├── score_loop.py           # 15-minute batch scoring loop
│   ├── pob_checker.py          # NFT minting eligibility checker
│   ├── retrainer.py            # Adversarial retraining orchestrator
│   ├── contracts.py            # Contract ABI loader
│   └── config.py               # Environment-based configuration
│
├── scorers/
│   └── interrogator.py         # Bridge adapter for oracle service
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
│   │   │   └── useScoreHistory.js  # localStorage-persisted history
│   │   └── abi/                # Contract ABIs (auto-generated on deploy)
│   └── vercel.json
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
│   └── check_connection.py       # RPC health check
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
git clone https://github.com/your-org/turing-protocol
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
# Generate synthetic training dataset (300 wallets across human/agent spectrum)
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
uvicorn oracle_service.main:app --host 0.0.0.0 --port 8080
```

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
1. WalletScorer.score("0x...") called by oracle service

2. MantleDataFetcher.fetch_wallet_transactions("0x...", max_txs=150)
   → Tries Etherscan V2 API (with chain ID)
   → Falls back to Etherscan V1 API
   → Falls back to RPC block scan if both unavailable

3. BehavioralFeatureEngineer.compute_all_features(df, wallet)
   → Extracts 47 features across 7 classes
   → Returns Dict[str, float]

4. FeaturePreprocessor.transform(features)
   → Reindex to trained feature order
   → Fill missing with 0.0
   → Apply RobustScaler

5. InterrogatorModel.score_wallet(X)
   → XGBoost.predict_proba(X)[0, 1]
   → Multiply by 10,000 → HPS integer

6. (if return_explanation=True)
   InterrogatorModel.explain_wallet(X)
   → TreeSHAP.shap_values(X)
   → Sort by |contribution|
   → Return top features with direction

7. (if return_explanation=True)
   InterrogatorModel.compute_behavior_fingerprint(X)
   → Take top-10 SHAP values
   → Quantise to integers (×1000)
   → SHA-256 hash → bytes32

8. Result returned:
   { hps: 7234, probability: 0.7234, confidence: "high",
     explanation: [...], fingerprint: "0x..." }
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
