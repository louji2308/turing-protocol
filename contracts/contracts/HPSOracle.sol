// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract HPSOracle {

    address public operator;

    address public pendingOperator;

    mapping(address => uint16) public scores;

    mapping(address => uint32) public lastUpdated;

    uint256 public totalScoredWallets;

    uint16 public modelVersion;

    event ScoreUpdated(
        address indexed wallet,
        uint16 oldScore,
        uint16 newScore,
        uint32 timestamp
    );

    event BatchScoresUpdated(
        uint256 walletCount,
        uint32 timestamp,
        uint16 modelVersion
    );

    event OperatorTransferInitiated(
        address indexed currentOperator,
        address indexed pendingOperator
    );

    event OperatorTransferCompleted(
        address indexed newOperator
    );

    modifier onlyOperator() {
        require(msg.sender == operator, "HPSOracle: caller is not the operator");
        _;
    }

    constructor(address _operator, uint16 _initialModelVersion) {
        require(_operator != address(0), "HPSOracle: zero address operator");
        operator = _operator;
        modelVersion = _initialModelVersion;
    }

    function batchUpdateScores(
        address[] calldata wallets,
        uint16[] calldata newScores,
        uint16 _modelVersion
    ) external onlyOperator {
        require(
            wallets.length == newScores.length,
            "HPSOracle: length mismatch"
        );
        require(
            wallets.length <= 500,
            "HPSOracle: batch too large (max 500)"
        );

        uint32 timestamp = uint32(block.timestamp);

        for (uint256 i = 0; i < wallets.length; ) {
            address wallet = wallets[i];
            uint16 newScore = newScores[i];

            require(newScore <= 10000, "HPSOracle: score exceeds maximum");

            if (scores[wallet] == 0 && lastUpdated[wallet] == 0) {
                totalScoredWallets++;
            }

            uint16 oldScore = scores[wallet];
            scores[wallet] = newScore;
            lastUpdated[wallet] = timestamp;

            emit ScoreUpdated(wallet, oldScore, newScore, timestamp);

            unchecked { i++; }
        }

        modelVersion = _modelVersion;

        emit BatchScoresUpdated(
            wallets.length,
            timestamp,
            _modelVersion
        );
    }

    function getScore(address wallet) external view returns (uint16) {
        return scores[wallet];
    }

    function getScoreWithFreshness(
        address wallet,
        uint256 maxStalenessSeconds
    ) external view returns (uint16 score, bool isFresh) {
        score = scores[wallet];
        isFresh = (
            lastUpdated[wallet] != 0 &&
            block.timestamp - lastUpdated[wallet] <= maxStalenessSeconds
        );
    }

    function isHuman(
        address wallet,
        uint16 threshold
    ) external view returns (bool) {
        return (
            scores[wallet] >= threshold &&
            lastUpdated[wallet] != 0 &&
            block.timestamp - lastUpdated[wallet] <= 86400
        );
    }

    function getScoreFraction(
        address wallet
    ) external view returns (uint16 numerator, uint16 denominator) {
        return (scores[wallet], 10000);
    }

    function initiateOperatorTransfer(
        address newOperator
    ) external onlyOperator {
        require(newOperator != address(0), "HPSOracle: zero address");
        pendingOperator = newOperator;
        emit OperatorTransferInitiated(operator, newOperator);
    }

    function acceptOperatorTransfer() external {
        require(
            msg.sender == pendingOperator,
            "HPSOracle: caller is not pending operator"
        );
        operator = pendingOperator;
        pendingOperator = address(0);
        emit OperatorTransferCompleted(operator);
    }
}
