import numpy as np
import os
import time
from typing import Optional, Dict, Any
from web3 import Web3
from eth_account import Account
from loguru import logger


class InteractionDiversificationModule:

    EXPLORATION_TARGETS = [
        {
            "name": "agni_finance",
            "address": "0x...",
            "interaction_type": "balance_query",
            "gas_estimate": 35000,
        },
        {
            "name": "fluxion_finance",
            "address": "0x...",
            "interaction_type": "pool_info",
            "gas_estimate": 40000,
        },
        {
            "name": "merchant_moe",
            "address": "0x...",
            "interaction_type": "quote",
            "gas_estimate": 30000,
        },
    ]

    DIVERSION_METHODS = [
        "0x70a08231",
        "0x18160ddd",
        "0x95d89b41",
        "0x06fdde03",
        "0x313ce567",
    ]

    TOKENS = {
        "WETH": "0xdeaddeaddeaddeaddeaddeaddeaddeaddead0000",
        "USDC": "0x09Bc4E0d864704c0a0Bda8e0eA20b4b9Dc0b1c3",
        "USDT": "0x201EBa5CC46D216Ce6DC03F6E759e8E766e12aE7",
        "mETH": "0xcDA86A272531e8640cD7F1a92c01839911B90bb0",
    }

    def __init__(self, w3: Web3, private_key: str, seed: Optional[int] = None):
        self.w3 = w3
        self.account = Account.from_key(private_key)
        self.rng = np.random.default_rng(seed)
        self._interaction_history = []
        self._explored_protocols = set()
        self._last_exploration_time = 0

    def should_diversify(self, current_hps: int) -> bool:
        base_prob = 0.20
        if current_hps < 6000:
            base_prob = 0.40
        elif current_hps < 7000:
            base_prob = 0.30
        if time.time() - self._last_exploration_time < 3600:
            base_prob *= 0.3
        return self.rng.random() < base_prob

    def generate_interaction(self, current_hps: int) -> Optional[Dict[str, Any]]:
        if not self.should_diversify(current_hps):
            return None

        interaction_type = self.rng.choice(
            ["protocol_explore", "method_diversify", "weekend_activity"],
            p=[0.50, 0.35, 0.15]
        )

        if interaction_type == "protocol_explore":
            return self._generate_explore_action()
        elif interaction_type == "method_diversify":
            return self._generate_method_diversify_action()
        else:
            return self._generate_weekend_action()

    def _generate_explore_action(self) -> Dict[str, Any]:
        target = self.rng.choice(self.EXPLORATION_TARGETS)
        return {
            "type": "diversification",
            "subtype": "protocol_explore",
            "target_contract": target["address"],
            "target_name": target["name"],
            "interaction_type": target["interaction_type"],
            "value_wei": 0,
            "gas_estimate": target["gas_estimate"],
            "reason": "exploration",
        }

    def _generate_method_diversify_action(self) -> Dict[str, Any]:
        method = self.rng.choice(self.DIVERSION_METHODS)
        token = self.rng.choice(list(self.TOKENS.keys()))
        return {
            "type": "diversification",
            "subtype": "method_diversify",
            "target_contract": self.TOKENS[token],
            "method_signature": method,
            "value_wei": 0,
            "gas_estimate": 35000,
            "reason": "method_diversity",
        }

    def _generate_weekend_action(self) -> Dict[str, Any]:
        target = self.rng.choice(self.EXPLORATION_TARGETS)
        return {
            "type": "diversification",
            "subtype": "weekend_activity",
            "target_contract": target["address"],
            "target_name": target["name"],
            "value_wei": 0,
            "gas_estimate": 30000,
            "reason": "weekend_diversity",
        }

    def record_execution(self, interaction: Dict, result: Dict):
        self._interaction_history.append({
            **interaction,
            "result": result,
            "timestamp": int(time.time()),
        })
        self._last_exploration_time = time.time()
        if interaction.get("target_name"):
            self._explored_protocols.add(interaction["target_name"])

    def get_stats(self) -> dict:
        return {
            "total_interactions": len(self._interaction_history),
            "unique_protocols_explored": len(self._explored_protocols),
            "last_exploration": self._last_exploration_time,
        }
