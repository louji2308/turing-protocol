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

- Currently live: Mantle Sepolia testnet (5003) — mainnet deployment planned post-hackathon.
- Validation wallets also include Ethereum Mainnet addresses (for ENS-verification
  cross-referencing only — not a live scoring chain).
- Planned: Arbitrum One, Base, Optimism (Q1 2026), per `BUSINESS_MODEL.md` Phase 3.

## Protocol Coverage Scaling

Protocol Humanness Scores require only the protocol's contract address. Adding a new
protocol means adding one entry to `Config.MANTLE_PROTOCOLS` — zero code changes. The
`IntelligenceAggregator` background loop automatically picks up new entries on its
next cycle.

Currently tracked: 6 Mantle protocols (Agni Finance, Merchant Moe, Aurelius, Lendle,
Init Capital, Cleopatra DEX). With the address dictionary populated, the system can
score every active Mantle protocol in a single nightly batch — the
`PROTOCOL_SAMPLE_CAP=200` constant bounds per-protocol cost regardless of total
protocol count.

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

| Metric                          | Value          |
|----------------------------------|------------------|
| Wallets scored on-chain (testnet) | 0+ (after first oracle cycle) |
| Protocols tracked                 | 6                               |
| Sybil clusters detected           | 0                               |
| Oracle uptime (Render free tier)  | Live — may cold-start ~30s      |
