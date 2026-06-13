---
name: turing-trust
description: >
  Behavioral proof-of-humanity trust gate for Mantle wallets. Given a wallet
  address, returns a Human Probability Score (0-10000), a trust/no-trust
  decision against a configurable threshold or tier, an optional plain-English
  explanation of the score, and a mutual trust handshake primitive for
  agent-to-agent trades. Backed by Turing Protocol's HPSOracle (live on
  Mantle Sepolia) and a 47-feature XGBoost behavioral classifier with SHAP
  explainability.
triggers:
  - "before trading with an unknown counterparty wallet"
  - "checking if a wallet qualifies for a Sybil-resistant airdrop/whitelist"
  - "auditing my own agent fleet for Sybil-like behavioral signatures"
commands:
  - turing-trust check <address> [--tier standard|strict|lenient] [--threshold N] [--explain] [--enrich]
  - turing-trust handshake --me <address> --counterparty <address> [--tier standard]
  - turing-trust self-audit --addresses-file <path>
output_format: json
exit_codes:
  0: proceed (trusted)
  1: reject (untrusted)
  2: insufficient_data (manual decision required)
  3: error (RPC/API failure)
requires:
  - network: mantle-sepolia (read-only RPC)
  - optional_env: NANSEN_API_KEY (for --enrich)
---

# Turing Trust Layer

Read-only, non-custodial trust gate. Never signs transactions, never holds
keys. Wraps `HPSOracle.sol` / `TuringLib.sol` (already deployed and verified
on Mantle Sepolia) plus the Turing Protocol oracle API for SHAP-explainable
behavioral scoring.

## Architecture

```
RealClaw Agent
     │
     ▼
Turing Trust Layer Skill
     │
     ├── CLI:     turing-trust check <address> [flags]
     ├── HTTP:    POST /skill/check_wallet_trust
     └── On-chain: TuringLib.requireHuman(oracle, addr, threshold)
```

## Example

```bash
# Check a wallet
turing-trust check 0xE0E216283eef00895b6ABAa73848448596B85724 --tier standard --explain

# Mutual handshake before a trade
turing-trust handshake --me 0xAGENT... --counterparty 0xPEER... --tier standard

# Self-audit your agent fleet
turing-trust self-audit --addresses-file fleet.txt
```
