import time as time_module
from typing import Optional, Dict, Any
import numpy as np
from web3 import Web3
from loguru import logger

from ghost_agent.modules.timing_noise import TimingNoiseModule
from ghost_agent.modules.gas_selector import GasSelectionModule
from ghost_agent.modules.interaction_div import InteractionDiversificationModule
from ghost_agent.modules.portfolio_bias import PortfolioBiasModule
from ghost_agent.modules.news_reaction import NewsReactionModule
from ghost_agent.modules.network_topology import NetworkTopologyModule


class BehaviorLayer:

    def __init__(
        self,
        timing_module: TimingNoiseModule,
        gas_module: GasSelectionModule,
        diversification_module: Optional[InteractionDiversificationModule] = None,
        portfolio_bias_module: Optional[PortfolioBiasModule] = None,
        news_module: Optional[NewsReactionModule] = None,
        network_module: Optional[NetworkTopologyModule] = None,
        w3: Optional[Any] = None,
    ):
        self.timing = timing_module
        self.gas = gas_module
        self.diversification = diversification_module
        self.portfolio_bias = portfolio_bias_module
        self.news = news_module
        self.network = network_module
        self.w3 = w3

        self._hps_low_threshold = 4500
        self._hps_high_threshold = 6000
        self._modifications_history = []

    def modify(self, action: Dict[str, Any], current_hps: int) -> Dict[str, Any]:
        modified = dict(action)
        intensity = self._get_behavioral_intensity(current_hps)
        _rng = np.random.default_rng()

        network_priority = current_hps < 6000 and self.network is not None
        if network_priority and self.network.should_send_eoa_transfer(self._get_total_tx_count()):
            eoa_action = self.network.generate_eoa_transfer()
            if eoa_action:
                logger.info("BehaviorLayer: Injecting EOA peer transfer (network topology)")
                self._record_modification("eoa_transfer", eoa_action)
                return self._finalize(eoa_action)

        if self.diversification and _rng.random() < intensity * 0.3:
            div_action = self.diversification.generate_interaction(current_hps)
            if div_action:
                logger.info("BehaviorLayer: Injecting diversification interaction")
                self._record_modification("diversification", div_action)
                return self._finalize(div_action)

        if self.portfolio_bias and action.get("amount_wei"):
            old_size = modified.get("amount_wei", 0)
            new_size = self.portfolio_bias.modify_trade_size(
                old_size, action.get("type", "unknown")
            )
            if new_size != old_size:
                modified["amount_wei"] = new_size
                modified["_bias_applied"] = True
                self._record_modification("portfolio_bias", {
                    "old_size": old_size, "new_size": new_size
                })

        suggested_gas = self._get_suggested_gas_price()
        human_gas = self.gas.select_gas_price(suggested_gas)
        modified["gas_price_wei"] = human_gas

        estimated_gas = modified.get("gas_estimate", 21000)
        human_gas_limit = self.gas.select_gas_limit(estimated_gas)
        modified["gas_limit"] = human_gas_limit

        self._record_modification("gas_behavior", {
            "suggested_gwei": suggested_gas / 1e9,
            "selected_gwei": human_gas / 1e9,
            "gas_limit": human_gas_limit,
        })

        return self._finalize(modified)

    def check_news_reaction(self) -> Optional[Dict[str, Any]]:
        if not self.news:
            return None
        return self.news.check_for_news()

    def _get_behavioral_intensity(self, hps: int) -> float:
        if hps < self._hps_low_threshold:
            return 1.5
        elif hps > self._hps_high_threshold:
            return 0.7
        else:
            return 1.0

    def _get_suggested_gas_price(self) -> int:
        if self.w3 is not None:
            try:
                return int(self.w3.eth.gas_price)
            except Exception:
                pass
        return 1000000000

    def _finalize(self, action: Dict[str, Any]) -> Dict[str, Any]:
        action["_behavior_version"] = "4.0"
        return action

    def _record_modification(self, mod_type: str, details: dict):
        self._modifications_history.append({
            "type": mod_type,
            "details": details,
            "timestamp": time_module.time(),
        })

    def _get_total_tx_count(self) -> int:
        return len(self._modifications_history)

    def get_stats(self) -> dict:
        mod_types = {}
        for m in self._modifications_history[-100:]:
            t = m["type"]
            mod_types[t] = mod_types.get(t, 0) + 1
        result = {
            "total_modifications": len(self._modifications_history),
            "recent_types": mod_types,
        }
        if self.network:
            result["network"] = self.network.get_stats()
        return result
