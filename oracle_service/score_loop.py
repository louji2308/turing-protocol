import asyncio
import os
import time
from typing import List, Dict, Optional
from web3 import Web3
from web3.types import TxReceipt
from eth_account import Account
from eth_account.signers.local import LocalAccount
from loguru import logger
from dotenv import load_dotenv

from oracle_service.config import OracleConfig

load_dotenv()


def _create_web3_with_fallback(rpc_urls: List[str], timeout: int = 30) -> Web3:
    primary = rpc_urls[0]
    w3 = Web3(Web3.HTTPProvider(primary, request_kwargs={"timeout": timeout}))
    w3._fallback_urls = rpc_urls[1:]
    w3._current_fallback_idx = 0
    return w3


def _rotate_rpc(w3: Web3, rpc_urls: List[str]) -> Web3:
    if not rpc_urls:
        return w3
    current = rpc_urls[0]
    rotated = rpc_urls[1:] + [current]
    new_w3 = Web3(Web3.HTTPProvider(rotated[0], request_kwargs={"timeout": 30}))
    new_w3._fallback_urls = rotated[1:]
    new_w3._current_fallback_idx = 0
    logger.warning(f"RPC rotated: {current[:40]}... -> {rotated[0][:40]}...")
    return new_w3


class ScoreSubmissionLoop:

    def __init__(
        self,
        scorer,
        w3: Web3,
        oracle_contract,
        config: OracleConfig,
    ):
        self.scorer = scorer
        self.w3 = w3
        self._rpc_urls = config.rpc_urls
        self.oracle_contract = oracle_contract
        self.config = config

        private_key = config.operator_private_key
        self.operator_account: LocalAccount = Account.from_key(private_key)
        self.operator_address = self.operator_account.address

        self.update_interval = config.update_interval
        self.model_version = config.model_version

        self._last_update_time = 0.0
        self._total_updates = 0
        self._total_wallets_updated = 0
        self._update_history: List[dict] = []
        self._is_running = False
        self._consecutive_failures = 0
        self._max_consecutive_failures = 10
        self._current_nonce: Optional[int] = None

    async def _health_check(self) -> bool:
        try:
            paused = await asyncio.to_thread(
                lambda: self.oracle_contract.functions.paused().call()
            )
            if paused:
                logger.critical("HPSOracle contract is PAUSED — no submissions will be made")
                return False
            logger.info("Health check OK — contract is not paused")
            return True
        except AttributeError:
            logger.warning("Contract has no paused() function (testnet deployment)")
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def _maybe_reconnect(self):
        if not self.w3.is_connected():
            logger.warning("Web3 disconnected. Rotating RPC...")
            self.w3 = _rotate_rpc(self.w3, self._rpc_urls)

    async def run(self):
        self._is_running = True
        logger.info(f"ScoreSubmissionLoop started | interval={self.update_interval}s | operator={self.operator_address}")

        if not await self._health_check():
            logger.critical("Contract health check failed — entering safe mode (no submissions)")

        while self._is_running:
            try:
                await self._run_update_cycle()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._consecutive_failures += 1
                backoff = min(60 * self._consecutive_failures, 900)
                logger.error(f"Score loop error (x{self._consecutive_failures}): {e}")
                if self._consecutive_failures >= self._max_consecutive_failures:
                    logger.critical(f"{self._consecutive_failures} consecutive failures. Entering safe mode.")
                    self.w3 = _rotate_rpc(self.w3, self._rpc_urls)
                    self._consecutive_failures = 0
                await asyncio.sleep(backoff)

            await asyncio.sleep(self.update_interval)

    def stop(self):
        self._is_running = False

    async def _run_update_cycle(self):
        cycle_start = time.time()
        logger.info("Starting oracle update cycle...")
        self._maybe_reconnect()

        active_wallets = await self._get_active_wallets()
        if not active_wallets:
            logger.info("No active wallets. Skipping cycle.")
            self._consecutive_failures = 0
            return

        scores_map = await self._compute_scores_batch(active_wallets)
        if not scores_map:
            logger.warning("No valid scores computed. Skipping submission.")
            self._consecutive_failures = 0
            return

        wallets = list(scores_map.keys())
        scores = [scores_map[w] for w in wallets]

        tx_hash = await self._submit_batch_to_oracle(wallets, scores)

        cycle_duration = time.time() - cycle_start
        self._last_update_time = time.time()
        self._total_updates += 1
        self._total_wallets_updated += len(wallets)
        self._consecutive_failures = 0

        self._update_history.append({
            "timestamp": int(time.time()),
            "wallets_updated": len(wallets),
            "tx_hash": tx_hash,
            "duration_seconds": round(cycle_duration, 2),
        })

        status = "SUCCESS" if tx_hash else "SKIPPED"
        logger.success(
            f"Oracle cycle {self._total_updates} | "
            f"{len(wallets)} wallets | "
            f"TX: {(tx_hash or 'NONE')[:16]}... | "
            f"{cycle_duration:.1f}s | {status}"
        )

    async def get_active_wallets(self) -> List[str]:
        return await self._get_active_wallets()

    async def _get_active_wallets(self) -> List[str]:
        active: set = set()
        try:
            ghost_addr = self.config.ghost_wallet
            if ghost_addr:
                active.add(Web3.to_checksum_address(ghost_addr))
        except Exception as e:
            logger.debug(f"Could not add ghost wallet: {e}")

        try:
            current_block = await asyncio.to_thread(
                lambda: self.w3.eth.block_number
            )
            from_block = max(0, current_block - 5000)
            events = await asyncio.to_thread(
                lambda: self.oracle_contract.events.ScoreUpdated.get_logs(
                    fromBlock=from_block,
                    toBlock="latest"
                )
            )
            for event in events:
                try:
                    active.add(Web3.to_checksum_address(event["args"]["wallet"]))
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"Could not query oracle events: {e}")

        return list(active)

    async def _compute_scores_batch(self, wallet_addresses: List[str]) -> Dict[str, int]:
        scores: Dict[str, int] = {}
        semaphore = asyncio.Semaphore(self.config.max_concurrent_scores)

        async def score_one(addr: str):
            async with semaphore:
                try:
                    result = await asyncio.to_thread(
                        self.scorer.score, addr, True
                    )
                    error = result.get("error")
                    if error and error == "insufficient_history":
                        return
                    scores[addr] = int(result["hps"])
                except Exception as e:
                    logger.debug(f"Scoring failed for {addr[:10]}: {e}")

        tasks = [score_one(addr) for addr in wallet_addresses]
        await asyncio.gather(*tasks, return_exceptions=True)
        return scores

    async def _submit_batch_to_oracle(
        self,
        wallets: List[str],
        scores: List[int]
    ) -> Optional[str]:
        if not wallets:
            return None

        chunk_size = self.config.batch_chunk_size
        last_tx_hash: Optional[str] = None

        for i in range(0, len(wallets), chunk_size):
            chunk_wallets = wallets[i:i + chunk_size]
            chunk_scores = [int(s) for s in scores[i:i + chunk_size]]

            try:
                tx_hash = await self._submit_single_chunk(chunk_wallets, chunk_scores)
                if tx_hash:
                    last_tx_hash = tx_hash
                    logger.success(
                        f"Chunk {i // chunk_size + 1}: "
                        f"{len(chunk_wallets)} wallets | "
                        f"{tx_hash[:16]}..."
                    )
                else:
                    logger.error(f"Chunk {i // chunk_size + 1}: submission returned no hash")
            except Exception as e:
                logger.error(f"Chunk {i // chunk_size + 1} failed: {e}")

        return last_tx_hash

    async def _submit_single_chunk(
        self,
        wallets: List[str],
        scores: List[int]
    ) -> Optional[str]:
        def build_and_send() -> Optional[str]:
            self._maybe_reconnect()
            if self._current_nonce is None:
                self._current_nonce = self.w3.eth.get_transaction_count(
                    self.operator_address, "pending"
                )

            nonce = self._current_nonce
            gas_price = self.w3.eth.gas_price

            tx = self.oracle_contract.functions.batchUpdateScores(
                wallets, scores, self.model_version
            ).build_transaction({
                "from": self.operator_address,
                "nonce": nonce,
                "gasPrice": int(gas_price * 1.1),
                "gas": 500000 + len(wallets) * 30000,
            })

            try:
                estimated = self.w3.eth.estimate_gas(tx)
                tx["gas"] = int(estimated * 1.2)
            except Exception as e:
                logger.debug(f"Gas estimation failed, using default: {e}")

            signed = self.w3.eth.account.sign_transaction(
                tx, private_key=self.config.operator_private_key
            )

            try:
                tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
            except ValueError as e:
                err_msg = str(e)
                if "already known" in err_msg:
                    logger.warning(f"Nonce {nonce} already submitted, incrementing")
                    self._current_nonce += 1
                    nonce = self._current_nonce
                    tx.update({"nonce": nonce})
                    signed = self.w3.eth.account.sign_transaction(
                        tx, private_key=self.config.operator_private_key
                    )
                    tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
                else:
                    raise

            tx_hash_hex = tx_hash.hex()
            self._current_nonce += 1

            try:
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                if receipt["status"] != 1:
                    logger.error(f"Transaction reverted: {tx_hash_hex}")
                    return None
            except Exception as e:
                logger.error(f"Receipt wait failed for {tx_hash_hex}: {e}")
                return tx_hash_hex

            return tx_hash_hex

        return await asyncio.to_thread(build_and_send)

    def get_stats(self) -> dict:
        return {
            "total_updates": self._total_updates,
            "total_wallets_updated": self._total_wallets_updated,
            "last_update_timestamp": int(self._last_update_time),
            "next_update_in_seconds": max(0, int(
                self._last_update_time + self.update_interval - time.time()
            )),
            "model_version": self.model_version,
            "operator": self.operator_address,
            "is_running": self._is_running,
            "consecutive_failures": self._consecutive_failures,
            "recent_cycles": self._update_history[-5:],
        }
