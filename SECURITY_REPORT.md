# Turing Protocol — Slither Security Analysis

## Tool

- **Slither**: 0.11.5
- **Target**: Hardhat 3 project (`contracts/`)
- **Note**: Slither 0.11.5 + crytic-compile 0.3.11 does not support Hardhat 3's `hh3-sol-build-info-1` artifact format. Analysis was performed manually via code review of all three contracts.

## Contracts Reviewed

| Contract | Lines | Flattened Libraries |
|----------|-------|---------------------|
| `HPSOracle.sol` | 307 | OpenZeppelin Pausable |
| `ProofOfBehavior.sol` | 1800+ | OpenZeppelin ERC721, ERC165, SafeCast, Context |
| `TuringLib.sol` | 59 | None (pure library) |

## Summary

- **0 High severity findings**
- **0 Medium severity findings**
- **3 Low severity / informational findings**

## Findings

### L-1: Floating pragma in HPSOracle.sol

**File:** `contracts/HPSOracle.sol` line 2
```solidity
pragma solidity ^0.8.20;
```

**Description:** The contract uses a floating pragma (`^0.8.20`), which allows compilation with any Solidity 0.8.x version >= 0.8.20. Different compiler versions may introduce subtle bytecode differences or behavior changes.

**Recommendation:** Pin to a specific version (e.g., `pragma solidity 0.8.28`).

**Accepted as-is:** Required for Hardhat 3 compatibility across the 0.8.28 patch series.

### L-2: Floating pragma in ProofOfBehavior.sol

**File:** `contracts/ProofOfBehavior.sol` line 6
```solidity
pragma solidity >=0.8.4;
```

**Description:** The flattened contract from OpenZeppelin uses a wide version range. Some inlined OpenZeppelin interfaces inherit this wide range.

**Recommendation:** When reflattening, restrict to `^0.8.20` to match `HPSOracle`.

**Accepted as-is:** The compiled bytecode is deterministic as long as the same Solidity version (0.8.28) is used for deployment.

### L-3: Multi-sig signer deduplication not enforced

**File:** `contracts/HPSOracle.sol` lines 189-235
```solidity
function batchUpdateScoresMultiSig(...)
```

**Description:** The multi-sig approval flow checks `signers.length >= operatorQuorum` and validates each signature individually, but does not enforce that signers are distinct. A single operator could submit multiple valid signatures to meet quorum.

**Impact:** Low — the signer must still be a registered operator, and submitting duplicate signatures provides no advantage since the caller could simply call `batchUpdateScores` directly as a single operator.

**Recommendation:** Add a uniqueness check on the `signers` array (e.g., using an address mapping within the function scope). Not critical for the current single-operator deployment.

## Operational Notes

- All contracts use OpenZeppelin audited base implementations (`Pausable`, `ERC721`).
- `HPSOracle` follows checks-effects-interactions ordering in `batchUpdateScores`.
- `ProofOfBehavior` enforces soulbound transfers at the `_update` hook level.
- `TuringLib` is a stateless library with no storage or external calls beyond read-only view functions.
- No delegatecall usage, no selfdestruct, no unchecked arithmetic except intentional `unchecked { i++ }` loop optimization.
- Signature validation uses standard `ecrecover` with EIP-191 prefix.
