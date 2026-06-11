import numpy as np
import time
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from web3 import Web3
from loguru import logger


class ParameterOptimizer:

    PARAMETER_SPACE = {
        "timing_focus_mu": (0.5, 2.5, 1.1, 0.2),
        "timing_focus_sigma": (0.2, 0.8, 0.45, 0.1),
        "timing_distract_mu": (2.0, 4.5, 3.2, 0.3),
        "timing_distract_sigma": (0.5, 1.5, 0.9, 0.15),
        "timing_p_focus_to_distract": (0.05, 0.30, 0.12, 0.03),
        "timing_p_distract_to_focus": (0.15, 0.50, 0.30, 0.05),

        "gas_round_weight": (0.10, 0.50, 0.30, 0.05),
        "gas_buffer_weight": (0.10, 0.50, 0.30, 0.05),
        "gas_urgency_weight": (0.02, 0.25, 0.10, 0.03),
        "gas_underpay_weight": (0.02, 0.25, 0.10, 0.03),

        "div_frequency": (0.05, 0.50, 0.20, 0.05),
        "div_protocol_explore_weight": (0.20, 0.80, 0.50, 0.10),

        "bias_disposition_strength": (0.2, 1.0, 0.6, 0.1),
        "bias_overconfidence_strength": (0.2, 1.0, 0.5, 0.1),
        "bias_loss_aversion_ratio": (1.0, 4.0, 2.0, 0.3),
        "bias_size_variability": (0.1, 0.8, 0.4, 0.1),
        "bias_round_number": (0.3, 1.0, 0.7, 0.1),

        "strategy_momentum_weight": (0.10, 0.50, 0.25, 0.05),
        "strategy_reversion_weight": (0.10, 0.40, 0.20, 0.05),
        "strategy_lp_weight": (0.05, 0.30, 0.15, 0.04),
        "strategy_hold_weight": (0.20, 0.60, 0.40, 0.05),
    }

    EVALUATION_TX_TARGET = 25
    MIN_IMPROVEMENT = 100

    def __init__(self, behavior_layer, oracle_contract, wallet_address: str):
        self.behavior = behavior_layer
        self.oracle = oracle_contract
        self.wallet = wallet_address

        self.rng = np.random.default_rng()

        self._params = {
            name: default
            for name, (_, _, default, _) in self.PARAMETER_SPACE.items()
        }

        self._generation = 0
        self._best_hps = 5000
        self._tx_since_update = 0
        self._current_trial_params = None
        self._eval_history = []

    async def optimize_async(self, current_hps: int, target_hps: int = 7200) -> Dict[str, Any]:
        if self._current_trial_params is not None:
            return await self._complete_evaluation(current_hps)

        trial = self._mutate()
        self._current_trial_params = trial
        self._tx_since_update = 0

        logger.info(
            f"Parameter Optimizer: Generation {self._generation} | "
            f"Starting trial (current best HPS: {self._best_hps})"
        )

        self._apply_params(trial)

        return {
            "status": "evaluating",
            "generation": self._generation,
            "trial_params": trial,
            "current_hps": current_hps,
        }

    async def _complete_evaluation(self, current_hps: int) -> Dict[str, Any]:
        improvement = current_hps - self._best_hps

        self._eval_history.append({
            "generation": self._generation,
            "trial_params": dict(self._current_trial_params),
            "hps_before": self._best_hps,
            "hps_after": current_hps,
            "improvement": improvement,
            "accepted": improvement >= self.MIN_IMPROVEMENT,
            "timestamp": int(time.time()),
        })

        if improvement >= self.MIN_IMPROVEMENT:
            self._best_hps = current_hps
            self._params = dict(self._current_trial_params)
            self._generation += 1
            self._current_trial_params = None

            logger.success(
                f"Optimizer: ACCEPTED mutation | "
                f"HPS {self._best_hps - improvement} -> {self._best_hps} | "
                f"Generation {self._generation}"
            )

            return {
                "status": "accepted",
                "new_best_hps": self._best_hps,
                "improvement": improvement,
            }
        else:
            self._apply_params(self._params)
            self._generation += 1
            self._current_trial_params = None

            logger.info(
                f"Optimizer: REJECTED mutation | "
                f"Improvement {improvement} < {self.MIN_IMPROVEMENT} | "
                f"Reverted to best (HPS: {self._best_hps})"
            )

            return {
                "status": "rejected",
                "best_hps": self._best_hps,
                "improvement": improvement,
            }

    def _mutate(self) -> Dict[str, float]:
        trial = dict(self._params)
        n_mutations = int(self.rng.integers(1, 4))
        param_names = list(self.PARAMETER_SPACE.keys())
        targets = self.rng.choice(param_names, size=n_mutations, replace=False)

        for name in targets:
            lo, hi, _default, sigma = self.PARAMETER_SPACE[name]
            current = trial[name]
            noise = self.rng.normal(0, sigma * (hi - lo))
            mutated = current + noise
            mutated = float(np.clip(mutated, lo, hi))
            trial[name] = round(mutated, 4)

        return trial

    def _apply_params(self, params: Dict[str, float]):
        timing = self.behavior.timing
        gas = self.behavior.gas
        portfolio = self.behavior.portfolio_bias

        if hasattr(timing, 'FOCUSED_MU') and hasattr(timing.__class__, 'FOCUSED_MU'):
            timing.__class__.FOCUSED_MU = params.get("timing_focus_mu", timing.FOCUSED_MU)
            timing.__class__.FOCUSED_SIGMA = params.get("timing_focus_sigma", timing.FOCUSED_SIGMA)
            timing.__class__.DISTRACTED_MU = params.get("timing_distract_mu", timing.DISTRACTED_MU)
            timing.__class__.DISTRACTED_SIGMA = params.get("timing_distract_sigma", timing.DISTRACTED_SIGMA)
            timing.__class__.P_FOCUS_TO_DISTRACT = params.get("timing_p_focus_to_distract", timing.P_FOCUS_TO_DISTRACT)
            timing.__class__.P_DISTRACT_TO_FOCUS = params.get("timing_p_distract_to_focus", timing.P_DISTRACT_TO_FOCUS)

        if hasattr(gas, 'STRATEGY_WEIGHTS'):
            round_w = params.get("gas_round_weight", 0.30)
            buffer_w = params.get("gas_buffer_weight", 0.30)
            exact_w = 1.0 - round_w - buffer_w - 0.20
            urgency_w = params.get("gas_urgency_weight", 0.10)
            underpay_w = params.get("gas_underpay_weight", 0.10)
            total = round_w + buffer_w + exact_w + urgency_w + underpay_w
            gas.__class__.STRATEGY_WEIGHTS = [
                round_w / total, buffer_w / total,
                exact_w / total, urgency_w / total, underpay_w / total
            ]

        if portfolio:
            portfolio.set_params({
                "disposition_effect_strength": params.get("bias_disposition_strength", 0.6),
                "overconfidence_strength": params.get("bias_overconfidence_strength", 0.5),
                "loss_aversion_ratio": params.get("bias_loss_aversion_ratio", 2.0),
                "size_variability": params.get("bias_size_variability", 0.4),
                "round_number_bias": params.get("bias_round_number", 0.7),
            })

    def signal_tx_generated(self):
        self._tx_since_update += 1

    def get_stats(self) -> dict:
        return {
            "generation": self._generation,
            "best_hps": self._best_hps,
            "eval_count": len(self._eval_history),
            "acceptance_rate": float(
                sum(1 for e in self._eval_history if e["accepted"]) / len(self._eval_history)
                if self._eval_history else 0
            ),
            "current_params": dict(self._params),
        }
