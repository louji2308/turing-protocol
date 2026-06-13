from __future__ import annotations

from collections import defaultdict

import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler


FEATURE_NAMES = [
    "temp_0_log_mean_delta", "temp_1_log_std_delta", "temp_2_skewness",
    "temp_3_kurtosis", "temp_4_cv", "temp_5_fast_reaction_ratio",
    "temp_6_autocorr", "temp_7_hour_gini",
    "gas_0_price_cv", "gas_1_round_fraction", "gas_2_nice_number_fraction",
    "gas_3_percentile_variance", "gas_4_overpay_ratio",
    "gas_5_mean_efficiency", "gas_6_efficiency_std",
    "div_0_unique_contract_ratio", "div_1_unique_protocols",
    "div_2_method_diversity", "div_3_protocol_hhi",
    "div_4_exploration_ratio", "div_5_weekend_ratio",
    "port_0_size_cv", "port_1_size_skew", "port_2_size_kurtosis",
    "port_3_overconfidence_score", "port_4_streak_size_correlation",
    "port_5_round_value_ratio", "port_6_lognormal_fit",
    "port_7_activity_consistency", "port_8_max_to_mean_ratio",
    "event_0_burstiness", "event_1_memory", "event_2_clustering",
    "event_3_avg_session_txs", "event_4_session_gap_cv",
    "consist_0_stress_variance_ratio", "consist_1_timing_early_cv",
    "consist_2_timing_late_cv", "consist_3_cv_evolution",
    "consist_4_failure_rate", "consist_5_method_evolution",
    "net_0_unique_recipient_ratio", "net_1_top1_concentration",
    "net_2_top3_concentration", "net_3_wallet_age_blocks_log",
    "net_4_total_volume_log", "net_5_contract_ratio",
    "mantle_48_staking_duration_days", "mantle_49_bridge_cv",
]

FUNDING_CONCENTRATION_IDX = FEATURE_NAMES.index("net_1_top1_concentration")
TIMING_CV_IDX = FEATURE_NAMES.index("temp_4_cv")
PROTOCOL_HHI_IDX = FEATURE_NAMES.index("div_3_protocol_hhi")


class SybilClusterDetector:
    def __init__(self, eps: float = 0.35, min_samples: int = 3):
        self.eps = eps
        self.min_samples = min_samples

    def detect_clusters(self, wallet_features: dict[str, np.ndarray]) -> dict:
        if len(wallet_features) < self.min_samples:
            return {"noise": list(wallet_features.keys()), "clusters": {}}

        addresses = list(wallet_features.keys())
        X = np.array([wallet_features[a] for a in addresses])
        X_scaled = StandardScaler().fit_transform(X)

        db = DBSCAN(eps=self.eps, min_samples=self.min_samples, metric="cosine")
        labels = db.fit_predict(X_scaled)

        grouped: dict[int, list[str]] = defaultdict(list)
        for addr, label in zip(addresses, labels):
            grouped[label].append(addr)

        result: dict = {"noise": grouped.pop(-1, []), "clusters": {}}
        for cluster_id, members in grouped.items():
            vectors = [wallet_features[m] for m in members]
            result["clusters"][f"cluster_{cluster_id}"] = {
                "members": members,
                "size": len(members),
                "avg_hps": round(float(np.mean([self._hps_from_features(f) for f in vectors]))),
                "sybil_probability": self._compute_sybil_prob(vectors),
                "coordinator": self._find_coordinator(members, vectors),
                "risk_level": self._risk_level(vectors),
            }
        return result

    def _hps_from_features(self, feature_vector: np.ndarray) -> float:
        funding = feature_vector[FUNDING_CONCENTRATION_IDX]
        timing_cv = feature_vector[TIMING_CV_IDX]
        proxy = (1 - funding) * 0.5 + min(timing_cv, 1.0) * 0.5
        return float(np.clip(proxy * 10000, 0, 10000))

    def _compute_sybil_prob(self, vectors: list[np.ndarray]) -> float:
        funding_conc = float(np.mean([v[FUNDING_CONCENTRATION_IDX] for v in vectors]))
        timing_std = float(np.std([v[TIMING_CV_IDX] for v in vectors]))
        hhi = float(np.mean([v[PROTOCOL_HHI_IDX] for v in vectors]))

        prob = (
            funding_conc * 0.40
            + max(0.0, 1 - timing_std * 5) * 0.35
            + hhi * 0.25
        )
        return round(float(np.clip(prob, 0.0, 1.0)), 3)

    def _find_coordinator(self, members: list[str], vectors: list[np.ndarray]) -> str | None:
        if not members:
            return None
        idx = int(np.argmax([v[FUNDING_CONCENTRATION_IDX] for v in vectors]))
        return members[idx]

    def _risk_level(self, vectors: list[np.ndarray]) -> str:
        avg_hps = float(np.mean([self._hps_from_features(v) for v in vectors]))
        return "high" if avg_hps < 5000 else "medium"
