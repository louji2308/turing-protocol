import numpy as np
import time
import os
from typing import Optional, Dict, Any, List
from web3 import Web3
from loguru import logger


class StrategyLayer:

    STRATEGIES = ["momentum", "reversion", "liquidity_provision", "hold"]
    STRATEGY_WEIGHTS = [0.25, 0.20, 0.15, 0.40]

    TRADING_PAIRS = [
        {"base": "MNT", "quote": "USDC", "pool": "0x...", "type": "volatile"},
        {"base": "MNT", "quote": "USDT", "pool": "0x...", "type": "volatile"},
        {"base": "USDC", "quote": "USDT", "pool": "0x...", "type": "stable"},
        {"base": "WETH", "quote": "USDC", "pool": "0x...", "type": "volatile"},
    ]

    MIN_TRADE_INTERVAL = 300

    def __init__(self, w3: Web3):
        self.w3 = w3
        self.rng = np.random.default_rng()
        self._last_trade_time = 0
        self._trade_count = 0
        self._strategy_history = []
        self._current_position = None
        self._position_entry_price = 0.0

    async def decide(self) -> Optional[Dict[str, Any]]:
        if time.time() - self._last_trade_time < self.MIN_TRADE_INTERVAL:
            return None

        strategy = self.rng.choice(self.STRATEGIES, p=self.STRATEGY_WEIGHTS)

        if strategy == "hold":
            return None
        elif strategy == "momentum":
            return self._momentum_trade()
        elif strategy == "reversion":
            return self._reversion_trade()
        elif strategy == "liquidity_provision":
            return self._liquidity_provision()

        return None

    def _momentum_trade(self) -> Dict[str, Any]:
        volatile = [p for p in self.TRADING_PAIRS if p["type"] == "volatile"]
        pair = self.rng.choice(volatile) if volatile else self.TRADING_PAIRS[0]
        size_mnt = self.rng.uniform(0.01, 0.1)
        size_wei = int(size_mnt * 1e18)

        action = {
            "type": "swap",
            "token_in": pair["base"],
            "token_out": pair["quote"],
            "amount_wei": size_wei,
            "slippage": 0.01,
            "pair": pair["pool"],
            "strategy": "momentum",
            "reason": "momentum_entry",
        }

        self._current_position = {
            "pair": pair["pool"],
            "direction": "long",
            "entry_size": size_wei,
            "entry_time": int(time.time()),
        }

        return action

    def _reversion_trade(self) -> Dict[str, Any]:
        volatile = [p for p in self.TRADING_PAIRS if p["type"] == "volatile"]
        pair = self.rng.choice(volatile) if volatile else self.TRADING_PAIRS[0]

        if self._current_position and self._current_position["pair"] == pair["pool"]:
            size_mnt = self.rng.uniform(0.02, 0.08)
        else:
            size_mnt = self.rng.uniform(0.01, 0.05)

        size_wei = int(size_mnt * 1e18)

        return {
            "type": "swap",
            "token_in": pair["base"],
            "token_out": pair["quote"],
            "amount_wei": size_wei,
            "slippage": 0.015,
            "pair": pair["pool"],
            "strategy": "reversion",
            "reason": "mean_reversion_entry",
        }

    def _liquidity_provision(self) -> Optional[Dict[str, Any]]:
        stable_pairs = [p for p in self.TRADING_PAIRS if p["type"] == "stable"]
        if not stable_pairs:
            return None

        pair = self.rng.choice(stable_pairs)
        amount_mnt = self.rng.uniform(0.005, 0.02)
        amount_wei = int(amount_mnt * 1e18)

        return {
            "type": "add_liquidity",
            "pool_address": pair["pool"],
            "token_0": pair["base"],
            "token_1": pair["quote"],
            "amount_0": amount_wei,
            "amount_1": amount_wei,
            "strategy": "liquidity_provision",
            "reason": "stable_lp_yield",
        }

    def record_result(self, action: Dict, result: Dict):
        self._last_trade_time = time.time()
        self._trade_count += 1
        self._strategy_history.append({
            "action": action,
            "result": result,
            "timestamp": int(time.time()),
        })

        if result.get("status") == "success" and action.get("type") == "swap":
            if self._current_position is None:
                self._current_position = {
                    "pair": action.get("pair"),
                    "direction": "long",
                    "entry_size": action.get("amount_wei", 0),
                    "entry_time": int(time.time()),
                }

    def get_stats(self) -> dict:
        strategy_counts = {}
        for h in self._strategy_history:
            s = h["action"].get("strategy", "unknown")
            strategy_counts[s] = strategy_counts.get(s, 0) + 1
        return {
            "total_decisions": self._trade_count,
            "strategies_used": strategy_counts,
            "has_position": self._current_position is not None,
        }
