import numpy as np
from typing import Optional


class GasSelectionModule:

    ROUND_GWEI_VALUES = [
        0.5, 1, 1.5, 2, 2.5, 3, 4, 5, 6, 7, 8, 9, 10,
        12, 15, 20, 25, 30, 40, 50, 75, 100
    ]

    STRATEGIES = ["round_nearest", "comfortable_buffer", "exact_suggested", "urgency_spike", "underpay"]
    STRATEGY_WEIGHTS = [0.30, 0.30, 0.20, 0.10, 0.10]

    def __init__(self, seed: Optional[int] = None):
        self.rng = np.random.default_rng(seed)
        self._gas_history = []

    def select_gas_price(self, suggested_gas_wei: int) -> int:
        suggested_gwei = suggested_gas_wei / 1e9
        strategy = self.rng.choice(self.STRATEGIES, p=self.STRATEGY_WEIGHTS)

        if strategy == "round_nearest":
            gas_gwei = self._round_to_human_friendly(suggested_gwei)
        elif strategy == "comfortable_buffer":
            buffer = self.rng.uniform(1.10, 1.25)
            gas_gwei = self._round_to_human_friendly(suggested_gwei * buffer)
        elif strategy == "exact_suggested":
            gas_gwei = suggested_gwei
        elif strategy == "urgency_spike":
            spike = self.rng.uniform(1.5, 2.8)
            gas_gwei = self._round_to_human_friendly(suggested_gwei * spike)
        elif strategy == "underpay":
            discount = self.rng.uniform(0.82, 0.96)
            gas_gwei = self._round_to_human_friendly(suggested_gwei * discount)

        gas_wei = int(gas_gwei * 1e9)
        self._gas_history.append({
            "suggested_gwei": suggested_gwei,
            "selected_gwei": gas_gwei,
            "strategy": strategy,
            "ratio": gas_gwei / (suggested_gwei + 1e-9)
        })
        return gas_wei

    def _round_to_human_friendly(self, gwei: float) -> float:
        if gwei <= 0:
            return 1.0
        distances = [abs(gwei - r) for r in self.ROUND_GWEI_VALUES]
        nearest_round = self.ROUND_GWEI_VALUES[int(np.argmin(distances))]
        if self.rng.random() < 0.70:
            return nearest_round
        else:
            noise = self.rng.normal(0, 0.1)
            return max(0.1, nearest_round + noise)

    def select_gas_limit(self, estimated_gas: int, buffer_type: str = "auto") -> int:
        if buffer_type == "auto":
            strategy = self.rng.choice(
                ["round_10k", "round_1k", "50pct_buffer", "100pct_buffer"],
                p=[0.25, 0.35, 0.25, 0.15]
            )
        else:
            strategy = buffer_type

        if strategy == "round_10k":
            return int(np.ceil(estimated_gas * 1.2 / 10000) * 10000)
        elif strategy == "round_1k":
            return int(np.ceil(estimated_gas * 1.3 / 1000) * 1000)
        elif strategy == "50pct_buffer":
            return int(estimated_gas * 1.5)
        elif strategy == "100pct_buffer":
            return int(estimated_gas * 2.0)
        else:
            return int(estimated_gas * 1.5)

    def get_stats(self) -> dict:
        if not self._gas_history:
            return {"count": 0}
        ratios = [h["ratio"] for h in self._gas_history]
        round_fraction = sum(
            1 for h in self._gas_history if abs(h["selected_gwei"] % 1) < 0.05
        ) / len(self._gas_history)
        return {
            "count": len(ratios),
            "mean_ratio": float(np.mean(ratios)),
            "std_ratio": float(np.std(ratios)),
            "cv_ratio": float(np.std(ratios) / (np.mean(ratios) + 1e-9)),
            "round_fraction": float(round_fraction),
            "strategies": {
                s: sum(1 for h in self._gas_history if h["strategy"] == s)
                for s in self.STRATEGIES
            }
        }
