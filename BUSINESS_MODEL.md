# Turing Protocol — Business Model

## Revenue Streams

### 1. API Subscription Tiers (Primary)

Protocol teams and VC funds pay for access to the Investment Intelligence Layer.

| Tier       | Price      | Queries/mo | Features                                             |
|------------|------------|------------|-------------------------------------------------------|
| Free       | $0         | 100/mo     | Single wallet HPS lookup (hackathon period: unlimited) |
| Protocol   | $299/mo    | 10,000     | Protocol Humanness Score, airdrop exposure calculator |
| Fund       | $999/mo    | Unlimited  | Smart money flows, Sybil clusters, real-time alerts   |
| Enterprise | Custom     | Unlimited  | White-label data feed, custom HPS thresholds          |

**Year 1 target**: 20 Protocol-tier + 5 Fund-tier subscribers = **$11,940/mo recurring**
($5,980 from Protocol tier + $4,995 from Fund tier + buffer for upgrades/overages).

### 2. Gating-as-a-Service (Secondary)

Protocols pay a flat integration fee ($2,000–$5,000) for `TuringLib` deployment and
airdrop/governance contract configuration for humanity-gated distribution.

**Year 1 target**: 8 integrations × $3,000 avg = **$24,000 one-time** + ongoing API revenue
from those same protocols upgrading to Protocol/Fund tiers.

### 3. Data Licensing (Year 2)

The continuously-growing adversarially-generated labeled dataset has standalone value to:
- Academic researchers studying on-chain behavioral economics
- Other Sybil-detection systems seeking behavioral ground truth
- The Mantle Foundation, as ecosystem intelligence infrastructure

Licensing price: **$5,000–$15,000/year per licensee**.

## Total Addressable Market

The airdrop industry distributed **>$4B** in 2024. Industry estimates put Sybil capture
at **15–40%** of all airdrop value — Turing Protocol addresses a **$600M–$1.6B annual
value-leakage problem** across all EVM chains.

On Mantle specifically: 3–5 major protocol TGEs are expected in 2025–2026, with average
airdrop sizes of $20M–$80M. At 25% Sybil capture, that is **$5M–$20M per protocol**
flowing to bots. Turing Protocol's fee (a $5,000 integration plus $3,588/year in API
costs) represents **0.01–0.07% of the value it protects** — a 1,400x–200,000x ROI
range for the protocol team, even at the conservative end.

## Go-to-Market Strategy

### Phase 1 (0–3 months): Hackathon → Pilot
- Win the Mirana track to secure introductions to Mantle portfolio protocols.
- Approach Init Capital, Aurelius, and Lendle for pilot integrations.
- Offer a free 30-day pilot: integrate `TuringLib`, score their wallets, and report
  bot-exposure reduction.
- Collect testimonials and before/after data for case studies.

### Phase 2 (3–6 months): Protocol Expansion
- Expand coverage to 10 Mantle protocols.
- Launch Stripe-based API subscription billing.
- Publish a monthly "Mantle Ecosystem Bot Report" as free, high-visibility marketing
  content (drives inbound Fund-tier interest).
- Target 2 VC fund data subscriptions, approaching Mirana directly first.

### Phase 3 (6–12 months): Multi-Chain
- Port the feature pipeline to Arbitrum, Base, and Optimism (~6 weeks engineering —
  see `ARCHITECTURE.md` for the per-chain extension pathway).
- Sell cross-chain Sybil detection to protocols deploying on multiple chains
  simultaneously.
- Explore a Mantle Foundation grant for ecosystem-intelligence infrastructure,
  positioning Turing Protocol as a public good with a sustainable commercial layer.

## Tokenomics (Optional, Phase 3+)

A `TURING` ERC-20 token is **not required for v1** — the system is fully functional
without it. In Phase 3 it could optionally:
- Decentralize the oracle operator set (stake `TURING` to run an oracle node, building
  on the existing multi-sig `addOperator`/`removeOperator` mechanism in `HPSOracle.sol`).
- Reward ground-truth wallet labels (stake `TURING`, submit a labeled wallet + evidence
  via `validation/CONTRIBUTING_WALLETS.md`, earn rewards on acceptance).
- Introduce governance over retraining parameters and HPS thresholds.

This is explicitly framed as an enhancement, not a dependency — avoiding any perception
of a premature token launch while leaving a credible decentralization path documented.
