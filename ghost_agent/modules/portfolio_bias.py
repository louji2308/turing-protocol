import numpy as np
from typing import Optional, Dict, Any, List


class PortfolioBiasModule:

    DEFAULT_PARAMS = {
        "disposition_effect_strength": 0.6,
        "overconfidence_strength": 0.5,
        "loss_aversion_ratio": 2.0,
        "recency_bias_horizon": 5,
        "size_variability": 0.4,
        "round_number_bias": 0.7,
    }

    ROUND_VALUES_MNT = [0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 25.0, 50.0, 100.0]

    def __init__(self, params: Optional[dict] = None):
        self.params = {**self.DEFAULT_PARAMS, **(params or {})}
        self.rng = np.random.default_rng()
        self._trade_history: List[dict] = []

    def modify_trade_size(self, base_size_wei: int, trade_type: str) -> int:
        recent = self._trade_history[-10:] if self._trade_history else []
        wins = sum(1 for t in recent if t.get("outcome", 0) > 0)
        losses = len(recent) - wins

        size_multiplier = 1.0
        if wins >= 3 and losses == 0:
            streak_factor = min(wins / 10, 1.0) * self.params["overconfidence_strength"]
            size_multiplier = 1.0 + (streak_factor * self.rng.uniform(0.2, 0.5))
        elif losses > wins and losses > 2:
            size_multiplier = 1.0 - (self.params["loss_aversion_ratio"] * self.rng.uniform(0.05, 0.15))

        variability = 1.0 + self.rng.uniform(
            -self.params["size_variability"],
            self.params["size_variability"]
        )
        modified_size = int(base_size_wei * size_multiplier * variability)

        if self.rng.random() < self.params["round_number_bias"]:
            modified_size_mnt = modified_size / 1e18
            nearest_round = min(
                self.ROUND_VALUES_MNT,
                key=lambda x: abs(x - modified_size_mnt)
            )
            modified_size = int(nearest_round * 1e18)

        return max(modified_size, 1)

    def record_trade(self, trade: Dict):
        self._trade_history.append({
            "timestamp": trade.get("timestamp"),
            "size": trade.get("size", 0),
            "outcome": trade.get("outcome", 0),
            "type": trade.get("type", "unknown"),
        })
        if len(self._trade_history) > 100:
            self._trade_history = self._trade_history[-100:]

    def get_recent_outcomes(self, n: int = 5) -> List[float]:
        recent = self._trade_history[-n:] if self._trade_history else []
        return [t.get("outcome", 0) for t in recent]

    def get_params(self) -> dict:
        return dict(self.params)

    def set_params(self, params: dict):
        self.params.update(params)

    def get_stats(self) -> dict:
        if not self._trade_history:
            return {"total_trades": 0}
        outcomes = [t.get("outcome", 0) for t in self._trade_history]
        return {
            "total_trades": len(self._trade_history),
            "win_rate": float(sum(1 for o in outcomes if o > 0) / len(outcomes)),
            "avg_outcome": float(np.mean(outcomes)),
            "recent_outcomes": self.get_recent_outcomes(5),
        }
