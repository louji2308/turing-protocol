// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IHPSOracle {
    function getScore(address wallet) external view returns (uint16);
    function getScoreWithFreshness(address wallet, uint256 maxStaleness)
        external view returns (uint16 score, bool isFresh);
    function isHuman(address wallet, uint16 threshold)
        external view returns (bool);
}

interface IProofOfBehavior {
    function hasFreshProof(address wallet) external view returns (bool);
    function walletToTokenId(address wallet) external view returns (uint256);
}

library TuringLib {

    function isHuman(
        address oracle,
        address wallet,
        uint16 threshold
    ) internal view returns (bool) {
        return IHPSOracle(oracle).isHuman(wallet, threshold);
    }

    function hasFreshProof(
        address pobRegistry,
        address wallet
    ) internal view returns (bool) {
        return IProofOfBehavior(pobRegistry).hasFreshProof(wallet);
    }

    function humanWeightedVotes(
        address oracle,
        address wallet,
        uint256 rawVotes
    ) internal view returns (uint256 humanWeighted) {
        uint16 hps = IHPSOracle(oracle).getScore(wallet);
        if (hps == 0) return rawVotes / 2;
        return (rawVotes * hps) / 10000;
    }

    function requireHuman(
        address oracle,
        address wallet,
        uint16 threshold,
        string memory errorMessage
    ) internal view {
        require(isHuman(oracle, wallet, threshold), errorMessage);
    }

    function humanPercent(
        address oracle,
        address wallet
    ) internal view returns (uint8) {
        return uint8(IHPSOracle(oracle).getScore(wallet) / 100);
    }
}
