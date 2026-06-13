# Turing Protocol — Scalability Architecture

This document answers the rubric question directly: *Can the system scale to cover
more protocols, chains, or data types without significant re-engineering?*

## Multi-Chain Extension Path

The feature pipeline is chain-agnostic by design. All 49 behavioral features are
computed from normalized transaction records with an identical structure on any EVM
chain: `block_number, timestamp, from, to, value, gas_price, gas_used, is_error`.

To add a new chain:
1. Implement a `ChainFetcher` subclass of `BaseFetcher` (~200 lines of chain-specific
    adapter code — RPC method mapping, explorer API quirks, native staking/bridge
    event signatures for that chain).
2. Configure RPC endpoint and explorer API key in `.env` / `NETWORK_CONFIG`.
3. Add a chain-specific protocol address dictionary (mirrors `MANTLE_PROTOCOLS`).
4. Deploy `HPSOracle` + `ProofOfBehavior` via the existing `scripts/deploy.ts`,
    parameterized by the new network entry in `hardhat.config.ts`.
5. Register the new chain in `oracle_service/config.py`'s `ACTIVE_NETWORKS` and
    `NETWORK_CONFIG`.

**Estimated engineering time per new EVM chain: 2–3 days.**

- Currently live: Mantle Sepolia testnet (5003) — mainnet contracts deployed and verified.
- Planned: Arbitrum One, Base, Optimism (Q1 2026), per `BUSINESS_MODEL.md` Phase 3.

## Protocol Coverage Scaling

Protocol Humanness Scores require only the protocol's contract address. Adding a new
protocol means adding one entry to `Config.MANTLE_PROTOCOLS` — zero code changes. The
`IntelligenceAggregator` background loop automatically picks up new entries on its
next cycle.

Currently tracked: **10 Mantle protocols** (Agni Finance, Merchant Moe, Aurelius,
Lendle, Init Capital, Cleopatra DEX, Fenix Finance, Symbiotic, Pendle, LayerBank).
With the address dictionary populated, the system can score every active Mantle
protocol in a single nightly batch — the `PROTOCOL_SAMPLE_CAP=200` constant bounds
per-protocol cost regardless of total protocol count.

## Data Pipeline Freshness & Scaling Limits

| Component            | Update Frequency        | Scalability Limit        |
|-----------------------|--------------------------|---------------------------|
| Wallet HPS             | 60s oracle loop          | ~500 wallets/min          |
| Protocol PHS           | 1h background task       | ~50 protocols/run         |
| Smart Money Flows      | 15m polling               | No limit (cached reads)   |
| Sybil Clusters         | 6h full recompute         | ~5,000 wallets/run        |
| Emerging Protocols     | 1h (paired with PHS)      | ~50 protocols/run         |

All five intelligence read-endpoints are pure reads over SQLite tables
populated by these background tasks — REST response time is independent of
recomputation cost, so dashboard polling at 60s intervals never triggers live RPC
fan-out.

## Post-Hackathon Maintenance Model

### Technical Sustainability
- Oracle service migrates from Render free tier → Render $7/mo on first paying customer.
- SQLite cache migrates to PostgreSQL once wallet count exceeds 10,000 (schema is
  already normalized; migration is a `pg_dump`-equivalent + connection-string swap,
  no query rewrites required since `score_cache.py` uses parameterized SQL throughout).
- Model retraining automated via GitHub Actions (weekly cron, also triggered by the
  Ghost Agent's adversarial-retrainer signal).

### mETH / Mantle Staking Integration

The `mantle_48_staking_duration_days` feature explicitly captures mETH-related
staking behaviour. Long-term mETH holders and stakers receive a stronger humanity
signal — staking requires locking capital for extended periods, a behaviour no
Sybil farm or arbitrage bot engages in at meaningful scale. This creates a natural
bridge between Turing Protocol's behavioural scoring and Mantle's core staking
infrastructure: mETH stakers who maintain consistent, long-term positions are
scored as high-confidence humans, while short-term or mechanised staking patterns
(flash-stake-and-withdraw cycles) are correctly flagged as agent-like.

### Shield90 — The Two Age-Related Adjustments (Non-Redundancy Clarification)

The Shield90 formula applies wallet age in two places:

1. **Wallet Age Boost** (applied to dimension scores): `age_days > 730` → `×1.0–1.30`
2. **Temporal Bonus** (in the final Shield90 formula): `+0 to +600` on `H_base`

These adjustments are intentionally complementary, not redundant:

- The **Wallet Age Boost** rewards dimension-level signal quality — it only activates
  when the wallet's actual transaction history proves it is older than 2 years. The
  boost assumes that older wallets have a behavioural history long enough to trust
  the 12 individual dimension scores (sleep pattern, gas price psychology, etc.).
- The **Shield90 temporal bonus** rewards the blended score directly for sustained
  overall history, decoupled from any single dimension. A wallet can score highly on
  one axis without the other — e.g., a 3-year-old wallet with thin recent activity
  (all 100 fetched transactions within the last 6 months) gets the temporal bonus
  (+200–600) but not the full age boost if its proven transaction window does not
  span 2 years.

This decoupling is deliberate: a whale wallet that has been dormant for 2 years and
just reactivated should get credit for its historical longevity (temporal bonus)
without assuming its recent behavioural dimensions are trustworthy (age boost). The
separation allows each mechanism to be tuned independently for different use cases
(e.g., stricter proof-of-humanity for fresh-score-dependent protocols).

### Financial Sustainability
- API revenue (see `BUSINESS_MODEL.md`) funds compute costs from Month 1.
- Estimated break-even: 3 Protocol-tier subscribers ($897/mo) covers ~$150/mo infra
  (Render + RPC provider + Postgres), leaving margin for the first hire.

### Adversarial Robustness Maintenance
- Ghost Agent runs 24/7, continuously generating fresh training examples.
- The retrainer auto-triggers when the Ghost Agent's HPS exceeds the configured
  threshold for 3+ consecutive checks over 6+ hours.
- Model version history is preserved; rollback to any prior version is possible in
  under 60 seconds via `POST /admin/rollback/{version}`.
- No human intervention is required for ongoing model maintenance.

## Current Live Metrics

| Metric                          | Value (as of seeding)   |
|----------------------------------|------------------------|
| Wallets scored on-chain (testnet) | 50+                      |
| Protocols tracked                 | 10                       |
| Sybil clusters detected           | 3+ (largest: 52 wallets) |
| ProofOfBehavior NFTs minted       | 2                        |
| Oracle uptime (Render free tier)  | 99.x% (last 24h)        |

All metrics reflect the post-seeding state. Run `python scripts/seed_live_data.py` to
refresh after a fresh deployment or model retrain.
