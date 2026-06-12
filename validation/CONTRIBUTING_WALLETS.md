# Contributing Labeled Wallets

We need more labeled wallets — especially **human wallets active on Mantle mainnet** — to produce a statistically meaningful AUC measurement.

## Submission Checklist

- [ ] The wallet has **>=10 total transactions AND >=5 outgoing transactions** on **Mantle mainnet** (Chain ID: 5000). Use `_precheck_wallet(readme)` or run a manual query at `https://explorer.mantle.xyz/address/{wallet}?tab=tx`.
- [ ] The label is **honest**. Use confidence levels to express uncertainty.
- [ ] **Evidence is verifiable.** Include a URL a skeptic could independently check.
- [ ] The submission follows the CSV format below.

## How to Submit

1. Fork this repository.
2. Add a row to `validation/wallets.csv` using the format described below.
3. If applicable, add supporting evidence to `validation/evidence/` (screenshots, explorer links, analysis reports).
4. Open a Pull Request.

## CSV Format

```
address,chain,label,confidence,source,evidence_link,notes
0xdead0000000000000000000000000000000000000,mantle,0,high,etherscan_mev_bot,https://etherscan.io/address/0xdead...,Known MEV bot labeled by Etherscan
```

### Fields

| Field | Values | Description |
|-------|--------|-------------|
| `address` | `0x...` (42 chars, lowercase) | Wallet address |
| `chain` | `mantle`, `mantle_sepolia`, or `ethereum` | Chain where label applies |
| `label` | `0` (bot/agent), `1` (human), or empty (ambiguous) | Ground truth |
| `confidence` | `high`, `medium`, `low` | How sure you are about the label |
| `source` | one of the recognized source tags | How the label was determined |
| `evidence_link` | URL | Working link supporting the label |
| `notes` | free text | Context, cluster membership, transaction count |

### Recognized Source Tags

For **bot** labels:
- `etherscan_mev_bot` — MEV bot labeled on Etherscan
- `etherscan_label` — General Etherscan label indicating bot/contract
- `sybil_report` — Identified in a published sybil detection report
- `mantle_sybil` — Mantle-specific sybil cluster analysis
- `self_deployed` — Wallet we deployed and control
- `flashbots` — Identified via Flashbots MEV data
- `public_bot_list` — Listed in a community-maintained bot directory

For **human** labels:
- `ens_doxxed` — Wallet name resolves to a known individual via ENS
- `etherscan_tag` — Tagged by a known individual on Etherscan
- `dao_voter` — Participated in DAO governance with verified identity
- `public_figure` — Publicly known crypto figure
- `self_submit` — Wallet owner self-certified as human (with proof)

## Labeling Guidelines

### Confident Bot (high confidence)
- Address deployed and controlled by the submitter with source code showing automation
- Address flagged as MEV bot by Etherscan with community corroboration
- Address identified as a sybil cluster hub in a methodologically sound analysis

### Confident Human (high confidence)
- Address linked to a known public figure via ENS or verified social media
- Wallet owner provides cryptographic proof of control and self-identifies as human

### Uncertain (medium/low confidence)
- Address shows both human and bot-like characteristics
- Sybil cluster member (not hub) — may be a real human within a sybil farm
- Address belongs to a known figure but behavior patterns are unusual

## Priority Wallets

These wallet types would most improve our validation:

1. **Mantle-native human wallets** — Humans who primarily use Mantle mainnet with >=10 txs and >=5 outgoing txs
2. **Cross-chain users** — Same human identity active on both Ethereum and Mantle
3. **MEV bots on Mantle** — Known bot operators who have migrated to Mantle
4. **LP position managers** — Semi-automated wallets (ambiguous middle)
5. **Verified DAO delegates** — Mantle DAO delegates who can prove their identity

## What Happens After Submission

1. The address is pre-screened for Mantle activity (if `chain=mantle`)
2. If it passes pre-screen (>=10 txs, >=5 outgoing), it's scored by the pipeline
3. Results are added to the next validation run
4. The submitter is credited in VALIDATION.md and (optionally) in the README
