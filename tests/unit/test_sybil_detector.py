import numpy as np
import pytest
from interrogator.sybil_detector import (
    SybilClusterDetector, FEATURE_NAMES,
    FUNDING_CONCENTRATION_IDX, TIMING_CV_IDX, PROTOCOL_HHI_IDX,
)


NUM_FEATURES = len(FEATURE_NAMES)


def _make_vector(overrides: dict | None = None) -> np.ndarray:
    v = np.zeros(NUM_FEATURES, dtype=float)
    v[FEATURE_NAMES.index("temp_4_cv")] = 0.2
    v[FEATURE_NAMES.index("net_1_top1_concentration")] = 0.9
    v[FEATURE_NAMES.index("div_3_protocol_hhi")] = 0.8
    if overrides:
        for k, val in overrides.items():
            v[FEATURE_NAMES.index(k)] = val
    return v


@pytest.fixture
def detector():
    return SybilClusterDetector(eps=0.35, min_samples=3)


class TestDetectClusters:
    def test_fewer_wallets_than_min_samples_returns_all_noise(self, detector):
        wallets = {
            "0xaaa": _make_vector({"temp_4_cv": 0.1}),
            "0xbbb": _make_vector({"temp_4_cv": 0.2}),
        }
        result = detector.detect_clusters(wallets)
        assert "noise" in result
        assert "clusters" in result
        assert len(result["noise"]) == 2
        assert result["clusters"] == {}

    def test_wallet_not_in_any_cluster_returns_in_cluster_false(self, detector):
        wallets = {
            "0xhuman_1": _make_vector({"temp_4_cv": 2.0, "net_1_top1_concentration": 0.2}),
            "0xhuman_2": _make_vector({"temp_4_cv": 1.5, "net_1_top1_concentration": 0.3}),
        }
        result = detector.detect_clusters(wallets)
        assert "0xhuman_1" in result["noise"]
        assert "0xhuman_2" in result["noise"]
        assert result["clusters"] == {}


class TestAnalyticalMethods:
    def test_hps_from_features(self, detector):
        v = _make_vector()
        hps = detector._hps_from_features(v)
        assert 0 <= hps <= 10000
        # high concentration + low timing CV = low hps
        low_hps = detector._hps_from_features(
            _make_vector({"net_1_top1_concentration": 0.99, "temp_4_cv": 0.01})
        )
        high_hps = detector._hps_from_features(
            _make_vector({"net_1_top1_concentration": 0.1, "temp_4_cv": 2.0})
        )
        assert low_hps < high_hps

    def test_compute_sybil_prob_in_range(self, detector):
        vectors = [_make_vector() for _ in range(3)]
        prob = detector._compute_sybil_prob(vectors)
        assert 0.0 <= prob <= 1.0

    def test_compute_sybil_prob_high_concentration(self, detector):
        vectors = [
            _make_vector({"net_1_top1_concentration": 0.99, "temp_4_cv": 0.01})
            for _ in range(3)
        ]
        prob = detector._compute_sybil_prob(vectors)
        assert prob > 0.5

    def test_find_coordinator(self, detector):
        members = ["0xlow", "0xmid", "0xhigh"]
        vectors = [
            _make_vector({"net_1_top1_concentration": 0.3}),
            _make_vector({"net_1_top1_concentration": 0.6}),
            _make_vector({"net_1_top1_concentration": 0.9}),
        ]
        coord = detector._find_coordinator(members, vectors)
        assert coord == "0xhigh"

    def test_find_coordinator_empty(self, detector):
        assert detector._find_coordinator([], []) is None

    def test_risk_level_high_for_low_avg_hps(self, detector):
        vectors = [
            _make_vector({"net_1_top1_concentration": 0.99, "temp_4_cv": 0.01})
            for _ in range(3)
        ]
        assert detector._risk_level(vectors) == "high"

    def test_risk_level_medium_for_high_avg_hps(self, detector):
        vectors = [
            _make_vector({"net_1_top1_concentration": 0.1, "temp_4_cv": 2.0})
            for _ in range(3)
        ]
        assert detector._risk_level(vectors) == "medium"
