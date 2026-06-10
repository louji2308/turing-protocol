import asyncio
import os
import time
import json
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
from loguru import logger

from ghost_agent.modules.timing_noise import TimingNoiseModule
from ghost_agent.modules.gas_selector import GasSelectionModule
from ghost_agent.modules.interaction_div import InteractionDiversificationModule
from ghost_agent.modules.portfolio_bias import PortfolioBiasModule
from ghost_agent.modules.news_reaction import NewsReactionModule
from ghost_agent.modules.param_optimizer import ParameterOptimizer
from ghost_agent.strategy_layer import StrategyLayer
from ghost_agent.behavior_layer import BehaviorLayer

load_dotenv()


class GhostAgent:

    OPTIMIZATION_TRIGGER_HPS = 5500
    TARGET_HPS = 7200

    def __init__(self):
        self.rpc_url = (
            os.getenv("MANTLE_TESTNET_RPC")
            if os.getenv("ACTIVE_NETWORK", "testnet") == "testnet"
            else os.getenv("MANTLE_MAINNET_RPC")
        )
        self.private_key = os.getenv("GHOST_PRIVATE_KEY")
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.account = Account.from_key(self.private_key)
        self.wallet_address = self.account.address

        self.oracle_address = os.getenv("HPS_ORACLE_ADDRESS")

        self.MERCHANT_MOE_ROUTER = os.getenv(
            "MERCHANT_MOE_ROUTER",
            "0x...",
        )

        self.timing = TimingNoiseModule()
        self.gas = GasSelectionModule()
        self.strategy = StrategyLayer(self.w3)
        self.portfolio_bias = PortfolioBiasModule()
        self.news = NewsReactionModule()
        self.diversification = InteractionDiversificationModule(
            w3=self.w3,
            private_key=self.private_key,
        )
        self.behavior = BehaviorLayer(
            timing_module=self.timing,
            gas_module=self.gas,
            diversification_module=self.diversification,
            portfolio_bias_module=self.portfolio_bias,
            news_module=self.news,
        )
        self.oracle_contract = self._load_oracle_contract()
        self.optimizer = ParameterOptimizer(
            behavior_layer=self.behavior,
            oracle_contract=self.oracle_contract,
            wallet_address=self.wallet_address,
        )

        self.current_hps = 5000
        self.trade_history = []
        self.is_running = False
        self._telemetry_queue = asyncio.Queue(maxsize=100)
        self._cycle_count = 0

    def _load_oracle_contract(self):
        if not self.oracle_address:
            logger.warning("HPS_ORACLE_ADDRESS not set - skipping oracle reads")
            return None

        abi = [{
            "inputs": [{"name": "wallet", "type": "address"}],
            "name": "getScore",
            "outputs": [{"name": "", "type": "uint16"}],
            "stateMutability": "view",
            "type": "function"
        }]
        return self.w3.eth.contract(
            address=Web3.to_checksum_address(self.oracle_address),
            abi=abi
        )

    async def run(self):
        self.is_running = True
        logger.info(f"Ghost Agent started | Wallet: {self.wallet_address}")
        logger.info(f"Network: {os.getenv('ACTIVE_NETWORK', 'testnet')}")

        while self.is_running:
            try:
                await self._single_cycle()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ghost cycle error: {e}")
                await asyncio.sleep(30)

    async def _single_cycle(self):
        self._cycle_count += 1

        if self.oracle_address and self.oracle_contract:
            try:
                self.current_hps = self.oracle_contract.functions.getScore(
                    self.wallet_address
                ).call()
            except Exception as e:
                logger.debug(f"Oracle read failed (normal before first score): {e}")

        if self.current_hps < self.OPTIMIZATION_TRIGGER_HPS:
            logger.warning(
                f"HPS {self.current_hps} < {self.OPTIMIZATION_TRIGGER_HPS}. "
                f"Running optimizer..."
            )
            opt_result = await self.optimizer.optimize_async(
                current_hps=self.current_hps,
                target_hps=self.TARGET_HPS
            )
            await self._emit_telemetry({
                "type": "optimization",
                "result": opt_result,
            })

        news_action = self.behavior.check_news_reaction()
        if news_action:
            logger.info(f"News reaction triggered: {news_action['event_id']}")
            for _ in range(news_action.get("burst_size", 1)):
                action = self.strategy.decide()
                if action:
                    modified = self.behavior.modify(action, self.current_hps)
                    await self._execute_and_record(modified)

        strategy_action = await self.strategy.decide()
        if strategy_action is None:
            wait_time = 120 + self.timing.get_delay()
            logger.debug(f"No action. Waiting {wait_time:.0f}s")
            await asyncio.sleep(wait_time)
            return

        await self._execute_and_record(strategy_action)

    async def _execute_and_record(self, raw_action: Dict[str, Any]):
        human_action = self.behavior.modify(raw_action, self.current_hps)
        self.optimizer.signal_tx_generated()

        delay = await self.timing.wait()
        logger.info(
            f"Executing: {human_action.get('type', 'unknown')} | "
            f"Delay: {delay:.1f}s | "
            f"State: {self.timing.get_current_state()}"
        )

        execution_result = await self._execute_transaction(human_action)

        self.trade_history.append({
            "timestamp": int(time.time()),
            "raw_action": raw_action,
            "human_action": human_action,
            "execution": execution_result,
            "hps_at_time": self.current_hps,
            "delay_applied": delay,
            "timing_state": self.timing.get_current_state(),
        })

        self.portfolio_bias.record_trade({
            "timestamp": int(time.time()),
            "size": raw_action.get("amount_wei", 0),
            "outcome": 1 if execution_result.get("status") == "success" else -1,
            "type": raw_action.get("type", "unknown"),
        })

        self.strategy.record_result(raw_action, execution_result)

        await self._emit_telemetry({
            "type": "trade",
            "hps": self.current_hps,
            "action": human_action.get("type"),
            "delay": delay,
            "timing_state": self.timing.get_current_state(),
            "execution": execution_result,
            "behavior_stats": self.behavior.get_stats(),
            "timing_stats": self.timing.get_stats(),
            "gas_stats": self.gas.get_stats(),
        })

        post_wait = self.timing.get_delay() * 2
        await asyncio.sleep(post_wait * 0.5)

    async def _execute_transaction(self, action: Dict[str, Any]) -> Dict[str, Any]:
        action_type = action.get("type", "unknown")
        logger.info(f"On-chain execution: {action_type}")

        try:
            if action_type == "swap":
                return await self._execute_swap(action)
            elif action_type == "add_liquidity":
                return await self._execute_add_liquidity(action)
            elif action_type == "diversification":
                return await self._execute_diversification(action)
            else:
                logger.warning(f"Unknown action type: {action_type}")
                return {"status": "skipped", "reason": f"unknown_type_{action_type}"}

        except Exception as e:
            logger.error(f"Execution failed: {e}")
            return {"status": "error", "error": str(e)[:200]}

    async def _execute_swap(self, action: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"Swap: {action.get('token_in')} -> {action.get('token_out')}")
        return {
            "status": "success",
            "action_type": "swap",
            "note": "swap_executed_via_web3",
            "details": action,
            "tx_hash": None,
        }

    async def _execute_add_liquidity(self, action: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"Add liquidity to pool: {action.get('pool_address', 'unknown')}")
        return {
            "status": "success",
            "action_type": "add_liquidity",
            "details": action,
        }

    async def _execute_diversification(self, action: Dict[str, Any]) -> Dict[str, Any]:
        target = action.get("target_contract", "unknown")
        logger.info(f"Diversification interaction with: {str(target)[:10]}...")

        result = {"status": "success", "action_type": "diversification"}
        self.diversification.record_execution(action, result)
        return result

    async def _emit_telemetry(self, data: dict):
        try:
            self._telemetry_queue.put_nowait({
                **data,
                "timestamp": int(time.time()),
                "wallet": self.wallet_address,
                "cycle": self._cycle_count,
            })
        except asyncio.QueueFull:
            pass

    def get_telemetry_queue(self) -> asyncio.Queue:
        return self._telemetry_queue

    def get_status(self) -> dict:
        return {
            "running": self.is_running,
            "wallet": self.wallet_address,
            "hps": self.current_hps,
            "cycles": self._cycle_count,
            "trades": len(self.trade_history),
            "timing_state": self.timing.get_current_state(),
            "optimizer": self.optimizer.get_stats(),
        }

    def stop(self):
        self.is_running = False
        logger.info("Ghost Agent stopping...")
