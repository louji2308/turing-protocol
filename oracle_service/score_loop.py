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

    async def run(self):
        self._is_running = True
        logger.info(f"ScoreSubmissionLoop started | interval={self.update_interval}s | operator={self.operator_address}")

        while self._is_running:
            try:
                await self._run_update_cycle()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._consecutive_failures += 1
                backoff = min(60 * self._consecutive_failures, 900)
                logger.error(f"Score loop error (x{self._consecutive_failures}): {e}")
                await asyncio.sleep(backoff)

            await asyncio.sleep(self.update_interval)

    def stop(self):
        self._is_running = False

    async def _run_update_cycle(self):
        cycle_start = time.time()
        logger.info("Starting oracle update cycle...")

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
            events = await asyncio.to_thread(
                lambda: self.oracle_contract.events.ScoreUpdated.get_logs(
                    fromBlock=max(0, current_block - 5000),
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
            nonce = self.w3.eth.get_transaction_count(
                self.operator_address, "latest"
            )
            gas_price = self.w3.eth.gas_price

            tx = self.oracle_contract.functions.batchUpdateScores(
                wallets, scores, self.model_version
            ).build_transaction({
                "from": self.operator_address,
                "nonce": nonce,
                "gasPrice": int(gas_price * 1.1),
                "gas": 500000 + len(wallets) * 30000,
            })

            estimated = self.w3.eth.estimate_gas(tx)
            tx["gas"] = int(estimated * 1.2)

            signed = self.w3.eth.account.sign_transaction(
                tx, private_key=self.config.operator_private_key
            )
            tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
            tx_hash_hex = tx_hash.hex()

            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            if receipt["status"] != 1:
                logger.error(f"Transaction reverted: {tx_hash_hex}")
                return None

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
