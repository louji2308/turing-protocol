import asyncio
import os
import time
import shutil
from typing import Dict, List, Optional
from datetime import datetime, timezone
from web3 import Web3
from web3.contract import Contract
from loguru import logger
from dotenv import load_dotenv

from oracle_service.config import OracleConfig

load_dotenv()


MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "checkpoints")


class AdversarialRetrainer:

    def __init__(
        self,
        interrogator,
        scorer,
        w3: Web3,
        oracle_contract: Contract,
        config: OracleConfig,
    ):
        self.interrogator = interrogator
        self.scorer = scorer
        self.w3 = w3
        self.oracle_contract = oracle_contract
        self.config = config

        self.check_interval = 7200
        self.ghost_wallet = config.ghost_wallet
        self.retraining_threshold = 7800

        self._is_running = False
        self._last_retrain_time = 0.0
        self._current_model_version = config.model_version
        self._retrain_count = 0
        self._retrain_history: List[dict] = []
        self._recent_ghost_scores: List[dict] = []
        self._is_retraining = False

    async def run(self):
        self._is_running = True
        logger.info(
            f"AdversarialRetrainer started | "
            f"ghost={self.ghost_wallet[:10] if self.ghost_wallet else 'N/A'} | "
            f"interval={self.check_interval}s"
        )

        while self._is_running:
            try:
                await self._check_cycle()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Retrainer check error: {e}")

            await asyncio.sleep(self.check_interval)

    def stop(self):
        self._is_running = False

    async def _check_cycle(self):
        cycle_start = time.time()
        ghost = self.ghost_wallet
        if not ghost:
            logger.debug("No ghost wallet configured. Skipping retrainer check.")
            return

        try:
            score_data = await asyncio.to_thread(
                lambda: self.oracle_contract.functions.getScore(ghost).call()
            )
            ghost_score = score_data if isinstance(score_data, int) else 0
        except Exception as e:
            logger.debug(f"Could not fetch ghost score: {e}")
            return

        self._recent_ghost_scores.append({
            "timestamp": time.time(),
            "score": ghost_score,
        })
        if len(self._recent_ghost_scores) > 50:
            self._recent_ghost_scores = self._recent_ghost_scores[-50:]

        should_retrain = self._should_trigger_retraining(ghost_score)
        if should_retrain and not self._is_retraining:
            await self._execute_retraining(ghost_score)

        cycle_duration = time.time() - cycle_start
        logger.debug(
            f"Retrainer cycle | ghost_score={ghost_score} | "
            f"model_v{self._current_model_version} | "
            f"retrain_needed={should_retrain} | {cycle_duration:.1f}s"
        )

    def _should_trigger_retraining(self, current_score: int) -> bool:
        if self._is_retraining:
            return False

        if current_score < self.retraining_threshold:
            return False

        if len(self._recent_ghost_scores) < 3:
            return False

        recent = self._recent_ghost_scores[-5:]
        sustained_above = sum(1 for s in recent if s["score"] >= self.retraining_threshold)
        if sustained_above < 3:
            return False

        time_since_last = time.time() - self._last_retrain_time
        if time_since_last < 21600:
            return False

        return True

    async def _execute_retraining(self, current_score: int):
        self._is_retraining = True
        retrain_start = time.time()
        new_version = self._current_model_version + 1
        logger.warning(
            f"Adversarial retraining triggered | "
            f"ghost_score={current_score} | "
            f"v{self._current_model_version} -> v{new_version}"
        )

        try:
            await asyncio.to_thread(
                self.interrogator.load_latest_ghost_data
            )

            await asyncio.to_thread(
                self.interrogator.adversarial_retrain,
                new_version
            )

            os.makedirs(MODEL_DIR, exist_ok=True)
            model_filename = f"interrogator_v{new_version}.pt"
            model_path = os.path.join(MODEL_DIR, model_filename)

            await asyncio.to_thread(
                self.interrogator.save_model, model_path
            )
            logger.success(f"Model saved: {model_path}")

            self._current_model_version = new_version
            self._last_retrain_time = time.time()
            self._retrain_count += 1
            self.config.model_version = new_version

            duration = time.time() - retrain_start
            self._retrain_history.append({
                "timestamp": int(time.time()),
                "version": new_version,
                "ghost_score": current_score,
                "duration_seconds": round(duration, 2),
            })

            logger.success(
                f"Retraining v{new_version} complete | "
                f"ghost_score={current_score} | "
                f"{duration:.1f}s"
            )

        except Exception as e:
            logger.error(f"Retraining failed: {e}")

        finally:
            self._is_retraining = False

    def get_stats(self) -> dict:
        return {
            "current_model_version": self._current_model_version,
            "retrain_count": self._retrain_count,
            "is_retraining": self._is_retraining,
            "last_retrain_timestamp": int(self._last_retrain_time),
            "retrain_threshold": self.retraining_threshold,
            "ghost_wallet": self.ghost_wallet,
            "recent_ghost_scores": [
                {
                    "timestamp": int(s["timestamp"]),
                    "score": s["score"],
                }
                for s in self._recent_ghost_scores[-5:]
            ],
            "retrain_history": self._retrain_history[-3:],
        }
