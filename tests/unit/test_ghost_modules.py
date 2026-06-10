import pytest
import numpy as np
import time
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from ghost_agent.modules.timing_noise import TimingNoiseModule
from ghost_agent.modules.gas_selector import GasSelectionModule
from ghost_agent.modules.interaction_div import InteractionDiversificationModule
from ghost_agent.modules.portfolio_bias import PortfolioBiasModule
from ghost_agent.modules.news_reaction import NewsReactionModule
from ghost_agent.modules.param_optimizer import ParameterOptimizer
from ghost_agent.strategy_layer import StrategyLayer
from ghost_agent.behavior_layer import BehaviorLayer


class TestTimingNoise:
    def setup_method(self):
        self.module = TimingNoiseModule(seed=42)

    def test_get_delay_returns_positive_float(self):
        delay = self.module.get_delay()
        assert delay > 0
        assert isinstance(delay, float)

    def test_focused_state_has_faster_timing(self):
        focused_delays = []
        self.module._state.is_focused = True
        for _ in range(100):
            focused_delays.append(self.module.get_delay())

        self.module._state.is_focused = False
        distracted_delays = []
        for _ in range(100):
            distracted_delays.append(self.module.get_delay())

        assert np.mean(focused_delays) < np.mean(distracted_delays)

    def test_wait_async_delays_correctly(self):
        self.module._state.is_focused = True
        delay = asyncio.run(self.module.wait())
        assert delay > 0

    def test_get_stats_returns_dict(self):
        for _ in range(5):
            self.module.get_delay()
        stats = self.module.get_stats()
        assert stats["count"] == 5
        assert "mean_delay" in stats
        assert "cv" in stats


class TestGasSelection:
    def setup_method(self):
        self.module = GasSelectionModule(seed=42)

    def test_gas_price_returns_positive_int(self):
        gas = self.module.select_gas_price(1000000000)
        assert gas > 0
        assert isinstance(gas, int)

    def test_gas_price_is_reasonable(self):
        prices = []
        for _ in range(50):
            p = self.module.select_gas_price(1500000000)
            prices.append(p / 1e9)
        mean_gwei = np.mean(prices)
        assert 0.5 < mean_gwei < 50

    def test_gas_limit_rounds_to_human_values(self):
        limit = self.module.select_gas_limit(50000, buffer_type="round_10k")
        assert limit % 10000 == 0

    def test_get_stats_returns_dict(self):
        for _ in range(10):
            self.module.select_gas_price(1000000000)
        stats = self.module.get_stats()
        assert stats["count"] == 10


class TestInteractionDiversification:
    def setup_method(self):
        mock_w3 = Mock()
        self.module = InteractionDiversificationModule(
            w3=mock_w3,
            private_key="0x" + "1" * 64,
            seed=42,
        )

    def test_should_diversify_returns_bool(self):
        result_high = self.module.should_diversify(9000)
        result_low = self.module.should_diversify(4000)
        assert isinstance(result_high, bool)
        assert isinstance(result_low, bool)

    def test_generate_interaction_returns_valid_action(self):
        action = self.module.generate_interaction(5000)
        if action is not None:
            assert "type" in action
            assert "subtype" in action
            assert "reason" in action

    def test_get_stats_returns_dict(self):
        stats = self.module.get_stats()
        assert "total_interactions" in stats


class TestPortfolioBias:
    def setup_method(self):
        self.module = PortfolioBiasModule()

    def test_trade_size_modification(self):
        base_size = 1000000000000000000
        modified = self.module.modify_trade_size(base_size, "swap")
        assert modified > 0
        assert isinstance(modified, int)

    def test_win_streak_increases_size(self):
        self.module._trade_history = [
            {"outcome": 1, "type": "swap"} for _ in range(5)
        ]
        base_size = 1000000000000000000
        sizes = [
            self.module.modify_trade_size(base_size, "swap")
            for _ in range(20)
        ]
        avg_size = np.mean(sizes)
        assert avg_size > base_size * 0.5

    def test_loss_streak_decreases_size(self):
        self.module._trade_history = [
            {"outcome": -1, "type": "swap"} for _ in range(5)
        ]
        base_size = 1000000000000000000
        sizes = [self.module.modify_trade_size(base_size, "swap") for _ in range(20)]
        avg_size = np.mean(sizes)
        assert avg_size < base_size + base_size * 0.5

    def test_record_trade_tracks_history(self):
        self.module.record_trade({"timestamp": 1000, "size": 100, "outcome": 1, "type": "swap"})
        assert len(self.module._trade_history) == 1

    def test_get_params_returns_copy(self):
        params = self.module.get_params()
        assert params["disposition_effect_strength"] == 0.6


class TestNewsReaction:
    def setup_method(self):
        self.module = NewsReactionModule(seed=42)

    def test_check_for_news_returns_none_or_dict(self):
        result = self.module.check_for_news()
        assert result is None or isinstance(result, dict)

    def test_news_event_has_valid_severity(self):
        self.module.NEWS_GENERATION_PROB = 1.0
        self.module.rng = np.random.default_rng(42)

        results = []
        for _ in range(50):
            r = self.module.check_for_news()
            if r:
                results.append(r)

        if results:
            for r in results:
                assert 0 <= r["severity"] <= 1


class TestBehaviorLayer:
    def setup_method(self):
        self.timing = TimingNoiseModule(seed=42)
        self.gas = GasSelectionModule(seed=42)
        self.bias = PortfolioBiasModule()
        self.diversification = InteractionDiversificationModule(
            w3=Mock(),
            private_key="0x" + "1" * 64,
            seed=42,
        )
        self.news = NewsReactionModule(seed=42)
        self.layer = BehaviorLayer(
            timing_module=self.timing,
            gas_module=self.gas,
            diversification_module=self.diversification,
            portfolio_bias_module=self.bias,
            news_module=self.news,
        )

    def test_modify_adds_gas_fields(self):
        action = {"type": "swap", "amount_wei": 1000000000000000000}
        modified = self.layer.modify(action, current_hps=7000)
        assert "gas_price_wei" in modified
        assert "gas_limit" in modified

    def test_modify_preserves_original_fields(self):
        action = {"type": "swap", "amount_wei": 1000000000000000000, "pair": "0xpool"}
        modified = self.layer.modify(action, current_hps=7000)
        assert modified["type"] == "swap"
        assert modified["pair"] == "0xpool"

    def test_behavioral_intensity_varies_with_hps(self):
        low_intensity = self.layer._get_behavioral_intensity(4000)
        high_intensity = self.layer._get_behavioral_intensity(9000)
        assert low_intensity > high_intensity


class TestStrategyLayer:
    def setup_method(self):
        mock_w3 = Mock()
        self.layer = StrategyLayer(mock_w3)

    def test_decide_returns_none_or_dict(self):
        self.layer._last_trade_time = 0
        result = asyncio.run(self.layer.decide())
        assert result is None or isinstance(result, dict)

    def test_strategy_history_tracks(self):
        self.layer.record_result(
            {"type": "swap", "strategy": "momentum"},
            {"status": "success"}
        )
        assert self.layer._trade_count == 1
        assert "momentum" in self.layer.get_stats()["strategies_used"]


class TestParameterOptimizer:
    def setup_method(self):
        self.mock_behavior = Mock(spec=BehaviorLayer)
        self.mock_behavior.timing = Mock()
        self.mock_behavior.gas = Mock()
        self.mock_behavior.portfolio_bias = PortfolioBiasModule()
        self.mock_oracle = Mock()
        self.optimizer = ParameterOptimizer(
            behavior_layer=self.mock_behavior,
            oracle_contract=self.mock_oracle,
            wallet_address="0xdead",
        )

    def test_initial_params_are_defaults(self):
        assert self.optimizer._params["timing_focus_mu"] == 1.1
        assert self.optimizer._params["bias_disposition_strength"] == 0.6

    def test_mutation_changes_params(self):
        mutated = self.optimizer._mutate()
        diff_count = sum(
            1 for k in mutated if mutated[k] != self.optimizer._params[k]
        )
        assert diff_count >= 1

    def test_param_space_bounds(self):
        for name, (lo, hi, default, _) in self.optimizer.PARAMETER_SPACE.items():
            assert lo <= default <= hi, f"{name}: default {default} outside [{lo}, {hi}]"
            assert lo < hi, f"{name}: lo >= hi"
