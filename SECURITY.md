# Turing Protocol — Security

## Smart Contract Audit

Manual review performed against `HPSOracle.sol`, `ProofOfBehavior.sol`,
and `TuringLib.sol`. Automated static analysis (Slither) is currently
blocked — the project uses Hardhat 3, whose artifact format
(`hh3-sol-build-info-1`) is not supported by `crytic-compile` 0.3.11.

All three contracts are built on OpenZeppelin audited v5 base implementations.

Summary:

- **0 High severity findings**
- **0 Medium severity findings**
- **3 Low severity findings** (see [SECURITY_REPORT.md](SECURITY_REPORT.md) for details)

Full manual analysis: [SECURITY_REPORT.md](SECURITY_REPORT.md).

## Model Security

- **Adversarial robustness**: the Ghost Agent (CMA-ES, 21 parameters) cannot exceed
  7,800 HPS after 90-Day Shield deployment. Current Ghost HPS: **4,641**.
- **Uncertainty quantification**: low-confidence scores
  (`uncertainty_hps >= 1500`) are flagged `investable: false` and should be excluded
  from automated decision-making by API consumers.
- **Temporal splitting**: the model is evaluated on data chronologically AFTER its
  training window, preventing overfitting to the current-generation strategies.
- **Model versioning**: every retrain produces a versioned checkpoint
  (`interrogator/models/v{N}/`). Rollback to any prior version is possible in under
  60 seconds via `POST /admin/rollback/{version}` (bearer-token protected).

## Operational Security

See the README's "Security" section for API authentication (`ADMIN_API_KEY`
bearer-token requirements), on-chain access control (`HPSOracle` operator/multi-sig,
`ProofOfBehavior` soulbound transfer restrictions), and private key management
(`OPERATOR_PRIVATE_KEY`, `GHOST_PRIVATE_KEY`, `ETHERSCAN_API_KEY` — all
`sync: false` in `render.yaml`, injected at deploy time, never written to disk or logs).
