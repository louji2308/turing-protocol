import asyncio
import os
import time
from typing import Dict, List, Optional, Set
from web3 import Web3
from web3.contract import Contract
from eth_account import Account
from eth_account.signers.local import LocalAccount
from loguru import logger
from dotenv import load_dotenv

from oracle_service.config import OracleConfig

load_dotenv()


class POBEligibilityChecker:

    def __init__(
        self,
        scorer,
        oracle_contract: Contract,
        pob_contract: Contract,
        w3: Web3,
        config: OracleConfig,
    ):
        self.scorer = scorer
        self.oracle_contract = oracle_contract
        self.pob_contract = pob_contract
        self.w3 = w3
        self.config = config

        private_key = config.operator_private_key
        self.operator_account: LocalAccount = Account.from_key(private_key)
        self.operator_address = self.operator_account.address

        self.threshold = config.pob_threshold
        self.sustained_hours = config.pob_sustained_hours
        self.min_tx_history = config.min_tx_history

        self.check_interval = 3600

        self._is_running = False
        self._total_mints_triggered = 0
        self._total_freshness_updates = 0
        self._tracked_wallets: Dict[str, dict] = {}
        self._last_check_time = 0.0

    async def run(self):
        self._is_running = True
        logger.info(f"POBEligibilityChecker started | threshold={self.threshold} | sustain={self.sustained_hours}h")

        while self._is_running:
            try:
                await self._check_cycle()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"POB checker error: {e}")

            await asyncio.sleep(self.check_interval)

    def stop(self):
        self._is_running = False

    async def _check_cycle(self):
        cycle_start = time.time()
        logger.info("Starting POB eligibility check cycle...")

        scored_wallets = await self._get_scored_wallets()
        if not scored_wallets:
            logger.debug("No scored wallets to check.")
            return

        for wallet in scored_wallets:
            try:
                await self._evaluate_wallet(wallet)
            except Exception as e:
                logger.debug(f"Evaluation failed for {wallet[:10]}: {e}")

        self._last_check_time = time.time()
        logger.info(
            f"POB check complete | "
            f"{len(scored_wallets)} wallets evaluated | "
            f"{self._total_mints_triggered} total mints | "
            f"{time.time() - cycle_start:.1f}s"
        )

    async def _get_scored_wallets(self) -> List[str]:
        wallets: Set[str] = set()

        try:
            current_block = await asyncio.to_thread(
                lambda: self.w3.eth.block_number
            )

            score_events = await asyncio.to_thread(
                lambda: self.oracle_contract.events.ScoreUpdated.get_logs(
                    from_block=max(0, current_block - 20000),
                    to_block="latest"
                )
            )
            for event in score_events:
                try:
                    wallets.add(Web3.to_checksum_address(event["args"]["wallet"]))
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"Could not query ScoreUpdated events: {e}")

        ghost = self.config.ghost_wallet
        if ghost:
            wallets.add(Web3.to_checksum_address(ghost))

        mint_events = await self._get_pob_mint_events()
        for event in mint_events:
            try:
                wallets.add(Web3.to_checksum_address(event["args"]["wallet"]))
            except Exception:
                continue

        return list(wallets)

    async def _get_pob_mint_events(self) -> list:
        try:
            return await asyncio.to_thread(
                lambda: self.pob_contract.events.ProofMinted.get_logs(
                    from_block=0,
                    to_block="latest"
                )
            )
        except Exception as e:
            logger.debug(f"Could not query ProofMinted events: {e}")
            return []

    async def _evaluate_wallet(self, wallet: str):
        wallet_lower = wallet.lower()
        now = time.time()

        score_data = await asyncio.to_thread(
            lambda: self.oracle_contract.functions.getScore(wallet).call()
        )
        current_score = score_data if isinstance(score_data, int) else 0

        if current_score < self.threshold:
            return

        last_updated = await asyncio.to_thread(
            lambda: self.oracle_contract.functions.lastUpdated(wallet).call()
        )

        if wallet_lower not in self._tracked_wallets:
            self._tracked_wallets[wallet_lower] = {
                "first_observed_score": current_score,
                "first_observed_time": now,
                "highest_score": current_score,
                "last_score": current_score,
                "last_update": now,
                "consecutive_checks_above_threshold": 1,
            }
        else:
            tracked = self._tracked_wallets[wallet_lower]
            tracked["last_score"] = current_score
            tracked["highest_score"] = max(tracked["highest_score"], current_score)
            tracked["last_update"] = now

            if current_score >= self.threshold:
                tracked["consecutive_checks_above_threshold"] += 1
            else:
                tracked["consecutive_checks_above_threshold"] = 0

        tracked = self._tracked_wallets[wallet_lower]
        sustained_seconds = now - tracked["first_observed_time"]
        sustained_hours_actual = sustained_seconds / 3600

        has_existing_proof = await asyncio.to_thread(
            lambda: self.pob_contract.functions.walletToTokenId(wallet).call()
        )
        has_existing_proof = bool(has_existing_proof and has_existing_proof > 0)

        if has_existing_proof:
            await self._update_existing_proof(wallet, current_score, tracked)
            return

        qualifies = (
            current_score >= self.threshold
            and sustained_hours_actual >= self.sustained_hours
            and tracked["consecutive_checks_above_threshold"] >= 3
        )

        if qualifies:
            await self._trigger_mint(wallet, current_score, tracked)

    async def _trigger_mint(self, wallet: str, score: int, tracked: dict):
        logger.info(f"Wallet qualifies for POB mint: {wallet[:10]}... (HPS={score})")

        try:
            fingerprint = await self._compute_fingerprint(wallet)

            def mint_tx():
                nonce = self.w3.eth.get_transaction_count(
                    self.operator_address, "latest"
                )
                gas_price = self.w3.eth.gas_price

                tx = self.pob_contract.functions.mint(
                    wallet,
                    score,
                    fingerprint,
                    self.config.model_version,
                ).build_transaction({
                    "from": self.operator_address,
                    "nonce": nonce,
                    "gasPrice": int(gas_price * 1.1),
                    "gas": 300000,
                })

                estimated = self.w3.eth.estimate_gas(tx)
                tx["gas"] = int(estimated * 1.2)

                signed = self.w3.eth.account.sign_transaction(
                    tx, private_key=self.config.operator_private_key
                )
                tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
                receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

                if receipt["status"] == 1:
                    return tx_hash.hex()
                logger.error(f"Mint reverted: {tx_hash.hex()}")
                return None

            tx_hash = await asyncio.to_thread(mint_tx)

            if tx_hash:
                self._total_mints_triggered += 1
                tracked["mint_tx"] = tx_hash
                tracked["mint_time"] = time.time()
                logger.success(
                    f"ProofOfBehavior minted for {wallet[:10]}... | "
                    f"HPS={score} | TX: {tx_hash[:16]}..."
                )
            else:
                logger.error(f"Failed to mint POB for {wallet[:10]}...")

        except Exception as e:
            logger.error(f"Mint transaction failed for {wallet[:10]}...: {e}")

    async def _update_existing_proof(self, wallet: str, current_score: int, tracked: dict):
        try:
            def update():
                nonce = self.w3.eth.get_transaction_count(
                    self.operator_address, "latest"
                )
                gas_price = self.w3.eth.gas_price

                tx = self.pob_contract.functions.updateFreshness(
                    wallet, current_score
                ).build_transaction({
                    "from": self.operator_address,
                    "nonce": nonce,
                    "gasPrice": int(gas_price * 1.1),
                    "gas": 100000,
                })

                signed = self.w3.eth.account.sign_transaction(
                    tx, private_key=self.config.operator_private_key
                )
                tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
                self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
                return tx_hash.hex()

            tx_hash = await asyncio.to_thread(update)
            self._total_freshness_updates += 1
            logger.debug(f"Freshness updated for {wallet[:10]}: {tx_hash[:16]}...")

        except Exception as e:
            logger.debug(f"Freshness update failed for {wallet[:10]}: {e}")

    async def _compute_fingerprint(self, wallet: str) -> bytes:
        try:
            result = self.scorer.score(wallet, use_cache=True, return_explanation=True)
            if "fingerprint" in result:
                return bytes.fromhex(result["fingerprint"][2:])
        except Exception:
            pass
        return b"\x00" * 32

    def get_stats(self) -> dict:
        return {
            "total_mints_triggered": self._total_mints_triggered,
            "total_freshness_updates": self._total_freshness_updates,
            "tracked_wallets": len(self._tracked_wallets),
            "threshold": self.threshold,
            "sustained_hours": self.sustained_hours,
            "is_running": self._is_running,
        }
