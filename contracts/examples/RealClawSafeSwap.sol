// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "../contracts/TuringLib.sol";

/// @title RealClawSafeSwap
/// @notice Example showing how a RealClaw agent's own strategy contract can
///         gate trades on counterparty humanity score with zero off-chain
///         dependency. Demonstrates `mutual_trust_handshake` logic on-chain.
contract RealClawSafeSwap {
    address public immutable hpsOracle;
    address public immutable pobRegistry;
    uint16 public constant STANDARD_THRESHOLD = 7000;

    event TradeGated(address indexed counterparty, uint16 score, bool proceeded);
    event HandshakeResult(
        address indexed counterparty,
        uint16 selfScore,
        uint16 counterpartyScore,
        uint16 dealConfidence,
        bool proceed
    );

    constructor(address _hpsOracle, address _pobRegistry) {
        hpsOracle = _hpsOracle;
        pobRegistry = _pobRegistry;
    }

    /// @notice Mutual handshake: both this contract's owner wallet AND the
    ///         counterparty must clear the threshold for the trade to proceed.
    /// @param counterparty The wallet on the other side of the trade.
    /// @param threshold Minimum HPS required (0 = use STANDARD_THRESHOLD).
    /// @return proceed True if both sides clear the threshold.
    function safeSwap(
        address counterparty,
        uint16 threshold
    ) external returns (bool proceed) {
        uint16 effectiveThreshold = threshold == 0 ? STANDARD_THRESHOLD : threshold;

        bool counterpartyOk = _checkHuman(counterparty, effectiveThreshold);
        bool selfOk = _checkHuman(address(this), effectiveThreshold);

        proceed = counterpartyOk && selfOk;
        emit TradeGated(counterparty, effectiveThreshold, proceed);

        return proceed;
    }

    /// @notice Full mutual trust handshake returning both scores and deal confidence.
    ///         Non-reverting version — lets the calling strategy decide how to handle
    ///         low-confidence results (smaller trade, wider slippage, abort).
    function mutualTrustHandshake(
        address counterparty,
        uint16 threshold
    )
        external
        view
        returns (
            uint16 selfScore,
            uint16 counterpartyScore,
            uint16 dealConfidence,
            bool proceed
        )
    {
        uint16 effectiveThreshold = threshold == 0 ? STANDARD_THRESHOLD : threshold;

        selfScore = TuringLib.humanPercent(hpsOracle, address(this));
        counterpartyScore = TuringLib.humanPercent(hpsOracle, counterparty);
        dealConfidence = selfScore < counterpartyScore ? selfScore : counterpartyScore;

        proceed = dealConfidence >= effectiveThreshold;
        // Note: dealConfidence here is in percent (0-100) from humanPercent()
        // For full 0-10000 precision, use IHPSOracle(oracle).getScore() directly
    }

    /// @notice Returns a suggested trade size fraction based on deal confidence.
    ///         Maps to the CLI handshake logic:
    ///         - >= threshold: 1.0 (full size)
    ///         - >= threshold * 0.7: 0.5 (half size)
    ///         - < threshold * 0.7: 0.0 (abort)
    function suggestedTradeFraction(
        address counterparty,
        uint16 threshold
    ) external view returns (uint256 fractionBps) {
        uint16 effectiveThreshold = threshold == 0 ? STANDARD_THRESHOLD : threshold;

        uint16 selfScore = IHPSOracle(hpsOracle).getScore(address(this));
        uint16 counterpartyScore = IHPSOracle(hpsOracle).getScore(counterparty);
        uint16 dealConfidence = selfScore < counterpartyScore ? selfScore : counterpartyScore;

        if (dealConfidence >= effectiveThreshold) {
            return 10000; // 100% in basis points
        } else if (dealConfidence >= (effectiveThreshold * 7) / 10) {
            return 5000; // 50% in basis points
        } else {
            return 0; // abort
        }
    }

    function _checkHuman(
        address wallet,
        uint16 threshold
    ) internal view returns (bool) {
        return IHPSOracle(hpsOracle).isHuman(wallet, threshold);
    }
}
