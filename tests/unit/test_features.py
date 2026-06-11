import pandas as pd
import numpy as np
import pytest
from data_pipeline.feature_engineer import BehavioralFeatureEngineer


def make_bot_df(n=100):
    """Synthetic dataframe mimicking agent-like trading behavior."""
    np.random.seed(42)
    base_ts = 1700000000
    half = max(1, n // 2)
    to_addrs = ["0xcontract_a"] * half + ["0xcontract_b"] * (n - half)
    return pd.DataFrame({
        "from_addr": ["0xbot"] * n,
        "to_addr": to_addrs,
        "is_sender": [True] * n,
        "value_mnt": [0.5] * n,
        "gas_price": [50_000_000_000] * n,
        "gas_efficiency": [0.95] * n,
        "timestamp": [base_ts + i * 60 for i in range(n)],
        "block_number": [1000 + i for i in range(n)],
        "time_since_prev_tx": [1.0] * n,
        "hour_of_day": (list(range(24)) * (n // 24 + 1))[:n],
        "day_of_week": [1] * n,
        "protocol": ["merchant_moe"] * n,
        "is_known_protocol": [True] * n,
        "method_id": ["0x12345678"] * n,
        "failed": [0] * n,
        "is_contract_call": [True] * n,
    })


def make_human_df(n=100):
    """Synthetic dataframe mimicking human-like trading behavior."""
    np.random.seed(42)
    base_ts = 1700000000

    humans = [
        "0xdead000000000000000000000000000000000001",
        "0xdead000000000000000000000000000000000002",
    ]

    protocols = [
        "merchant_moe", "agni_finance", "fluxion",
        "unknown_defi", "another_defi",
    ]

    method_ids = [
        "0x12345678", "0x87654321", "0xaabbccdd",
        "0xdeadbeef", "0x11112222", "0x33334444",
    ]

    deltas = np.random.exponential(scale=300, size=n).clip(1, 86400)
    timestamps = [base_ts + int(deltas[:i+1].sum()) for i in range(n)]
    time_since = [60.0] + [timestamps[i] - timestamps[i-1] for i in range(1, n)]

    hour_probs = [0.01] * 24
    hour_probs[14] = 0.20
    hour_probs[15] = 0.15
    hour_probs[16] = 0.10
    hour_probs[10] = 0.08
    hour_probs[11] = 0.08
    hour_probs[20] = 0.06
    s = sum(hour_probs)
    hour_probs = [p / s for p in hour_probs]
    hours = np.random.choice(range(24), size=n, p=hour_probs).tolist()

    return pd.DataFrame({
        "from_addr": [np.random.choice(humans) for _ in range(n)],
        "to_addr": [np.random.choice(
            ["0xcontract_a", "0xcontract_b", "0xcontract_c",
             "0xcontract_d", "0xuser_eoa"],
            p=[0.3, 0.3, 0.2, 0.1, 0.1]
        ) for _ in range(n)],
        "is_sender": [True] * n,
        "value_mnt": np.random.lognormal(mean=-1, sigma=1, size=n).clip(0.001, 100),
        "gas_price": np.random.lognormal(mean=3.9, sigma=0.3, size=n) * 1e9,
        "gas_efficiency": np.random.beta(a=5, b=1.5, size=n).clip(0.1, 1.0),
        "timestamp": timestamps,
        "block_number": [1000 + i for i in range(n)],
        "time_since_prev_tx": time_since,
        "hour_of_day": hours,
        "day_of_week": np.random.choice(range(7), size=n).tolist(),
        "protocol": [np.random.choice(protocols) for _ in range(n)],
        "is_known_protocol": [np.random.random() > 0.2 for _ in range(n)],
        "method_id": [np.random.choice(method_ids) for _ in range(n)],
        "failed": np.random.binomial(1, 0.05, size=n).tolist(),
        "is_contract_call": [np.random.random() > 0.15 for _ in range(n)],
    })


class TestTemporalFeatures:
    """Bot vs Human timing pattern discrimination."""

    def test_bot_has_low_timing_cv(self):
        engineer = BehavioralFeatureEngineer()
        df_bot = make_bot_df()
        feats = engineer._temporal_irregularity_features(df_bot)
        assert feats["temp_4_cv"] < 0.5, (
            f"Bot CV should be low, got {feats['temp_4_cv']}"
        )

    def test_human_has_high_timing_cv(self):
        engineer = BehavioralFeatureEngineer()
        df_human = make_human_df()
        feats = engineer._temporal_irregularity_features(df_human)
        assert feats["temp_4_cv"] > 0.5, (
            f"Human CV should be high, got {feats['temp_4_cv']}"
        )

    def test_bot_has_high_fast_reaction(self):
        engineer = BehavioralFeatureEngineer()
        df_bot = make_bot_df()
        feats = engineer._temporal_irregularity_features(df_bot)
        assert feats["temp_5_fast_reaction_ratio"] > 0.5, (
            f"Bot fast reaction ratio should be high, got {feats['temp_5_fast_reaction_ratio']}"
        )

    def test_bot_has_low_hour_gini(self):
        engineer = BehavioralFeatureEngineer()
        df_bot = make_bot_df()
        feats = engineer._temporal_irregularity_features(df_bot)
        assert feats["temp_7_hour_gini"] < 0.3, (
            f"Bot hour Gini should be low, got {feats['temp_7_hour_gini']}"
        )

    def test_human_has_high_hour_gini(self):
        engineer = BehavioralFeatureEngineer()
        df_human = make_human_df()
        feats = engineer._temporal_irregularity_features(df_human)
        assert feats["temp_7_hour_gini"] > 0.3, (
            f"Human hour Gini should be high, got {feats['temp_7_hour_gini']}"
        )


class TestGasFeatures:
    """Gas behavior discrimination."""

    def test_bot_gas_cv_is_low(self):
        engineer = BehavioralFeatureEngineer()
        df_bot = make_bot_df()
        feats = engineer._gas_behavior_features(df_bot)
        assert feats["gas_0_price_cv"] < 0.3, (
            f"Bot gas CV should be low, got {feats['gas_0_price_cv']}"
        )


class TestDiversityFeatures:
    """Interaction diversity discrimination."""

    def test_bot_diversity_is_low(self):
        engineer = BehavioralFeatureEngineer()
        df_bot = make_bot_df()
        feats = engineer._interaction_diversity_features(df_bot)
        assert feats["div_0_unique_contract_ratio"] < 0.1, (
            f"Bot unique contract ratio should be low, got {feats['div_0_unique_contract_ratio']}"
        )

    def test_human_diversity_is_higher(self):
        engineer = BehavioralFeatureEngineer()
        df_bot = make_bot_df()
        df_human = make_human_df()
        feats_bot = engineer._interaction_diversity_features(df_bot)
        feats_human = engineer._interaction_diversity_features(df_human)
        assert feats_human["div_0_unique_contract_ratio"] > feats_bot["div_0_unique_contract_ratio"]
        assert feats_human["div_2_method_diversity"] > feats_bot["div_2_method_diversity"]


class TestFeatureCount:
    """The 47-feature invariant."""

    def test_always_47_features(self):
        engineer = BehavioralFeatureEngineer()
        df_bot = make_bot_df()
        feats = engineer.compute_all_features(df_bot, "0xbot")
        assert len(feats) == 47, (
            f"Expected 47 features, got {len(feats)}"
        )

    def test_human_also_47_features(self):
        engineer = BehavioralFeatureEngineer()
        df_human = make_human_df()
        feats = engineer.compute_all_features(df_human, df_human["from_addr"].iloc[0])
        assert len(feats) == 47, (
            f"Expected 47 features, got {len(feats)}"
        )

    def test_temporal_has_8_features(self):
        engineer = BehavioralFeatureEngineer()
        df_bot = make_bot_df()
        feats = engineer._temporal_irregularity_features(df_bot)
        assert len(feats) == 8

    def test_gas_has_7_features(self):
        engineer = BehavioralFeatureEngineer()
        df_bot = make_bot_df()
        feats = engineer._gas_behavior_features(df_bot)
        assert len(feats) == 7

    def test_diversity_has_6_features(self):
        engineer = BehavioralFeatureEngineer()
        df_bot = make_bot_df()
        feats = engineer._interaction_diversity_features(df_bot)
        assert len(feats) == 6

    def test_portfolio_has_9_features(self):
        engineer = BehavioralFeatureEngineer()
        df_bot = make_bot_df()
        feats = engineer._portfolio_behavior_features(df_bot)
        assert len(feats) == 9

    def test_temporal_correlation_has_5_features(self):
        engineer = BehavioralFeatureEngineer()
        df_bot = make_bot_df()
        feats = engineer._temporal_correlation_features(df_bot)
        assert len(feats) == 5

    def test_consistency_has_6_features(self):
        engineer = BehavioralFeatureEngineer()
        df_bot = make_bot_df()
        feats = engineer._behavioral_consistency_features(df_bot)
        assert len(feats) == 6

    def test_network_has_6_features(self):
        engineer = BehavioralFeatureEngineer()
        df_bot = make_bot_df()
        feats = engineer._network_features(df_bot, "0xbot")
        assert len(feats) == 6


class TestEdgeCases:
    """Edge case handling."""

    def test_insufficient_txs_raises(self):
        engineer = BehavioralFeatureEngineer()
        df_small = make_bot_df(n=3)
        with pytest.raises(ValueError, match="Insufficient transaction history"):
            engineer.compute_all_features(df_small, "0xbot")

    def test_no_sender_txs_raises(self):
        engineer = BehavioralFeatureEngineer()
        df = make_bot_df(n=10)
        df["is_sender"] = False
        with pytest.raises(ValueError, match="fewer than 5 outgoing"):
            engineer.compute_all_features(df, "0xbot")

    def test_fallback_returns_mid_values(self):
        engineer = BehavioralFeatureEngineer()
        df = make_bot_df(n=10)
        df["gas_price"] = 0
        feats = engineer._gas_behavior_features(df)
        for v in feats.values():
            assert v == 0.5
