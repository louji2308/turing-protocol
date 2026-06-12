import numpy as np
import cma
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

        self._param_names = list(self.PARAMETER_SPACE.keys())
        self._param_bounds = [
            (lo, hi)
            for name, (lo, hi, _, _) in self.PARAMETER_SPACE.items()
        ]

        self._generation = 0
        self._best_hps = 5000
        self._tx_since_update = 0
        self._current_trial_params = None
        self._trial_direction = 1
        self._eval_history = []

        self._es = None
        self._es_initialized = False

    def _init_cma_es(self, direction: int):
        x0 = np.array([self._params[name] for name in self._param_names])
        bounds_low = np.array([b[0] for b in self._param_bounds])
        bounds_high = np.array([b[1] for b in self._param_bounds])
        sigma0 = 0.3 * np.mean(bounds_high - bounds_low)

        inopts = {
            'bounds': [bounds_low.tolist(), bounds_high.tolist()],
            'maxiter': 1000,
            'popsize': 8,
            'verbose': -9,
            'CMA_diagonal': True,
            'tolx': 1e-4,
            'tolfun': 1e-4,
        }

        self._es = cma.CMAEvolutionStrategy(x0, sigma0, inopts)
        self._es_initialized = True
        self._trial_direction = direction

    def _params_to_dict(self, x: np.ndarray) -> Dict[str, float]:
        return {
            name: float(np.clip(x[i], self._param_bounds[i][0], self._param_bounds[i][1]))
            for i, name in enumerate(self._param_names)
        }

    async def optimize_async(self, current_hps: int, target_hps: int = 7200, direction: int = 1) -> Dict[str, Any]:
        if self._current_trial_params is not None:
            return await self._complete_evaluation(current_hps)

        if not self._es_initialized:
            self._init_cma_es(direction)

        self._trial_direction = direction

        if self._es.stop():
            logger.warning(f"CMA-ES converged. Resetting with new initial point.")
            self._init_cma_es(direction)

        x_trial = self._es.ask()
        trial = self._params_to_dict(x_trial[0])
        self._current_trial_params = trial
        self._current_x_trial = x_trial[0]
        self._tx_since_update = 0

        mode_label = "IMPROVE" if direction >= 0 else "REDUCE"
        logger.info(
            f"CMA-ES Optimizer: {mode_label} Gen {self._generation} | "
            f"Current best HPS: {self._best_hps}"
        )

        self._apply_params(trial)

        return {
            "status": "evaluating",
            "generation": self._generation,
            "trial_params": trial,
            "current_hps": current_hps,
            "direction": direction,
        }

    async def _complete_evaluation(self, current_hps: int) -> Dict[str, Any]:
        if self._trial_direction >= 0:
            improvement = current_hps - self._best_hps
        else:
            improvement = self._best_hps - current_hps

        self._eval_history.append({
            "generation": self._generation,
            "trial_params": dict(self._current_trial_params),
            "hps_before": self._best_hps,
            "hps_after": current_hps,
            "improvement": improvement,
            "accepted": improvement >= self.MIN_IMPROVEMENT,
            "direction": self._trial_direction,
            "timestamp": int(time.time()),
        })

        fval = -current_hps if self._trial_direction >= 0 else current_hps
        self._es.tell([self._current_x_trial], [fval])

        if improvement >= self.MIN_IMPROVEMENT:
            self._best_hps = current_hps
            self._params = dict(self._current_trial_params)
            self._generation += 1
            self._current_trial_params = None

            logger.success(
                f"CMA-ES: ACCEPTED | "
                f"HPS {self._best_hps - improvement if self._trial_direction >= 0 else self._best_hps + improvement} -> {self._best_hps} | "
                f"Gen {self._generation}"
            )

            return {
                "status": "accepted",
                "new_best_hps": self._best_hps,
                "improvement": improvement,
                "direction": self._trial_direction,
            }
        else:
            self._apply_params(self._params)
            self._generation += 1
            self._current_trial_params = None

            logger.info(
                f"CMA-ES: REJECTED | "
                f"Improvement {improvement} < {self.MIN_IMPROVEMENT} | "
                f"Best HPS: {self._best_hps}"
            )

            return {
                "status": "rejected",
                "best_hps": self._best_hps,
                "improvement": improvement,
                "direction": self._trial_direction,
            }

    def _apply_params(self, params: Dict[str, float]):
        timing = self.behavior.timing
        gas = self.behavior.gas
        portfolio = self.behavior.portfolio_bias

        if timing is not None:
            timing.clear_overrides()
            timing.set_override("FOCUSED_MU", params.get("timing_focus_mu", timing.FOCUSED_MU))
            timing.set_override("FOCUSED_SIGMA", params.get("timing_focus_sigma", timing.FOCUSED_SIGMA))
            timing.set_override("DISTRACTED_MU", params.get("timing_distract_mu", timing.DISTRACTED_MU))
            timing.set_override("DISTRACTED_SIGMA", params.get("timing_distract_sigma", timing.DISTRACTED_SIGMA))
            timing.set_override("P_FOCUS_TO_DISTRACT", params.get("timing_p_focus_to_distract", timing.P_FOCUS_TO_DISTRACT))
            timing.set_override("P_DISTRACT_TO_FOCUS", params.get("timing_p_distract_to_focus", timing.P_DISTRACT_TO_FOCUS))

        if hasattr(gas, 'STRATEGY_WEIGHTS'):
            round_w = params.get("gas_round_weight", 0.30)
            buffer_w = params.get("gas_buffer_weight", 0.30)
            urgency_w = params.get("gas_urgency_weight", 0.10)
            underpay_w = params.get("gas_underpay_weight", 0.10)
            exact_w = 1.0 - round_w - buffer_w - urgency_w - underpay_w
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
            "optimizer_type": "cma-es",
            "popsize": 8,
        }
