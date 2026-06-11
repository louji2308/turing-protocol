// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract HPSOracle {

    address public operator;

    address public pendingOperator;

    mapping(address => uint16) public scores;

    mapping(address => uint32) public lastUpdated;

    uint256 public totalScoredWallets;

    uint16 public modelVersion;

    uint256 public operatorCount;

    uint256 public operatorQuorum;

    mapping(address => bool) public isOperator;

    address[] public operatorList;

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

    event OperatorAdded(address indexed operator);

    event OperatorRemoved(address indexed operator);

    modifier onlyOperator() {
        require(isOperator[msg.sender], "HPSOracle: caller is not an operator");
        _;
    }

    constructor(address _operator, uint16 _initialModelVersion) {
        require(_operator != address(0), "HPSOracle: zero address operator");
        operator = _operator;
        modelVersion = _initialModelVersion;
        isOperator[_operator] = true;
        operatorList.push(_operator);
        operatorCount = 1;
        operatorQuorum = 1;
    }

    function addOperator(address _newOperator) external onlyOperator {
        require(_newOperator != address(0), "HPSOracle: zero address");
        require(!isOperator[_newOperator], "HPSOracle: already operator");
        isOperator[_newOperator] = true;
        operatorList.push(_newOperator);
        operatorCount++;
        _updateQuorum();
        emit OperatorAdded(_newOperator);
    }

    function removeOperator(address _operatorToRemove) external onlyOperator {
        require(isOperator[_operatorToRemove], "HPSOracle: not an operator");
        require(operatorCount > 1, "HPSOracle: cannot remove last operator");
        isOperator[_operatorToRemove] = false;
        for (uint256 i = 0; i < operatorList.length; i++) {
            if (operatorList[i] == _operatorToRemove) {
                operatorList[i] = operatorList[operatorList.length - 1];
                operatorList.pop();
                break;
            }
        }
        operatorCount--;
        _updateQuorum();
        emit OperatorRemoved(_operatorToRemove);
    }

    function _updateQuorum() internal {
        if (operatorCount <= 3) {
            operatorQuorum = 1;
        } else if (operatorCount <= 5) {
            operatorQuorum = 2;
        } else {
            operatorQuorum = operatorCount / 2;
        }
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

    function batchUpdateScoresMultiSig(
        address[] calldata wallets,
        uint16[] calldata newScores,
        uint16 _modelVersion,
        address[] calldata signers,
        bytes[] calldata signatures
    ) external {
        require(wallets.length == newScores.length, "HPSOracle: length mismatch");
        require(wallets.length <= 500, "HPSOracle: batch too large (max 500)");
        require(signers.length >= operatorQuorum, "HPSOracle: quorum not met");
        require(signers.length == signatures.length, "HPSOracle: signer/sig mismatch");

        bytes32 messageHash = keccak256(abi.encodePacked(wallets, newScores, _modelVersion));

        for (uint256 i = 0; i < signers.length; i++) {
            require(isOperator[signers[i]], "HPSOracle: invalid signer");
            bytes32 ethSignedHash = keccak256(
                abi.encodePacked("\x19Ethereum Signed Message:\n32", messageHash)
            );
            address recovered = _recoverSigner(ethSignedHash, signatures[i]);
            require(recovered == signers[i], "HPSOracle: invalid signature");
        }

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
        emit BatchScoresUpdated(wallets.length, timestamp, _modelVersion);
    }

    function _recoverSigner(bytes32 ethSignedHash, bytes memory signature) internal pure returns (address) {
        (bytes32 r, bytes32 s, uint8 v) = _splitSignature(signature);
        return ecrecover(ethSignedHash, v, r, s);
    }

    function _splitSignature(bytes memory signature) internal pure returns (bytes32 r, bytes32 s, uint8 v) {
        require(signature.length == 65, "HPSOracle: invalid signature length");
        assembly {
            r := mload(add(signature, 32))
            s := mload(add(signature, 64))
            v := byte(0, mload(add(signature, 96)))
        }
        if (v < 27) {
            v += 27;
        }
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

    function getOperators() external view returns (address[] memory) {
        return operatorList;
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
