from typing import Dict, List, Optional, Tuple
from loguru import logger
import numpy as np
import time
from pathlib import Path

from interrogator.model import InterrogatorModel
from data_pipeline.feature_engineer import BehavioralFeatureEngineer
from data_pipeline.preprocessing import FeaturePreprocessor
from data_pipeline.mantle_fetcher import MantleDataFetcher
from scorers.dimension_scorer import DimensionScorer, hybrid_hps
from oracle_service.score_cache import get_cached_score, get_cached_explanation, cache_score, clear_expired


class WalletScorer:
    """
    Production-grade real-time wallet scoring service.

    This is the bridge between the ML model and the oracle submission loop.
    Given any wallet address, it fetches data, engineers features,
    and returns a Human Probability Score ready for on-chain submission.

    Performance target: Score any wallet in < 30 seconds.
    Cached features reduce repeat scoring to < 1 second.
    """

    def __init__(
        self,
        rpc_url: str,
        models_dir: str = "interrogator/models"
    ):
        self.fetcher = MantleDataFetcher(rpc_url)
        self.engineer = BehavioralFeatureEngineer()
        self.preprocessor = FeaturePreprocessor(models_dir)
        self.model = InterrogatorModel(models_dir)
        self.model.load()

        self.dim_scorer = DimensionScorer()

        # Feature cache: {wallet_address: (features_dict, timestamp)}
        # Expire cache entries after 15 minutes
        self._feature_cache: Dict[str, Tuple[dict, float]] = {}
        self._cache_ttl = 900  # 15 minutes

    def score(
        self,
        wallet_address: str,
        use_cache: bool = True,
        return_explanation: bool = False
    ) -> Dict:
        """
        Scores a single wallet and returns HPS + optional explanation.

        Args:
            wallet_address: Ethereum address string
            use_cache: Use cached features if available and fresh
            return_explanation: Include SHAP contributions in result

        Returns:
            {
                "address": "0x...",
                "hps": 7234,           # 0-10000, int
                "probability": 0.7234, # float
                "confidence": "high",  # low/medium/high
                "explanation": [...],  # only if return_explanation=True
                "fingerprint": "0x...",
                "computed_at": 1234567890
            }
        """
        start = time.time()

        # 1. Check SQLite for full cached result (including explanation)
        cached_db = get_cached_score(wallet_address, max_age_seconds=900) if use_cache else None
        if cached_db is not None:
            if return_explanation and "explanation" not in cached_db:
                cached_db["explanation"] = get_cached_explanation(wallet_address)
            logger.debug(f"Using SQLite cache for {wallet_address[:10]}")
            return cached_db

        # 2. Compute score (without explanation — SHAP is slow)
        features_dict = self._compute_features(wallet_address, use_cache)
        if features_dict is None:
            return self._insufficient_history_result(wallet_address)

        X = self.preprocessor.transform(features_dict)
        ml_hps = self.model.score_wallet(X)

        final_hps, ml_weight, dim_weight, dim_scores = hybrid_hps(
            ml_hps=ml_hps, features=features_dict,
            dim_scorer=self.dim_scorer, block_time=2.0,
        )
        hps = final_hps
        probability = hps / 10000.0

        if probability > 0.85 or probability < 0.15:
            confidence = "high"
        elif probability > 0.70 or probability < 0.30:
            confidence = "medium"
        else:
            confidence = "low"

        result = {
            "address": wallet_address,
            "hps": hps,
            "ml_hps": ml_hps,
            "probability": probability,
            "confidence": confidence,
            "ml_weight": ml_weight,
            "dim_weight": dim_weight,
            "dimension_scores": dim_scores,
            "computed_at": int(time.time()),
            "computation_ms": int((time.time() - start) * 1000),
        }

        # 3. Compute explanation only if requested (and only on first request)
        if return_explanation:
            logger.info(f"Computing SHAP explanation for {wallet_address[:10]}...")
            result["explanation"] = self.model.explain_wallet(X)
            result["fingerprint"] = self.model.compute_behavior_fingerprint(X)

        # 4. Cache result (without explanation first, then with it on next cache cycle)
        try:
            cache_score(wallet_address, result)
        except Exception:
            pass

        elapsed = result['computation_ms']
        logger.info(
            f"Scored {wallet_address[:10]}... | "
            f"HPS={hps} ({probability:.1%}) [{confidence}] | {elapsed}ms"
        )

        return result

    def _compute_features(self, wallet_address: str, use_cache: bool) -> Optional[dict]:
        cached = self._get_cached_features(wallet_address) if use_cache else None
        if cached is not None:
            return cached
        try:
            df = self.fetcher.fetch_wallet_transactions_adaptive(
                wallet_address, min_txs=50, max_txs=500, target_days=90
            )
            if len(df) < 10:
                return None
            features_dict = self.engineer.compute_all_features(df, wallet_address)
            self._cache_features(wallet_address, features_dict)
            return features_dict
        except Exception as e:
            logger.error(f"Feature engineering failed for {wallet_address[:10]}: {e}")
            return None

    def score_batch(
        self,
        wallet_addresses: List[str],
        return_explanations: bool = False
    ) -> List[Dict]:
        """
        Scores a list of wallets efficiently.
        Used by the oracle submission loop every 15 minutes.
        """
        results = []
        total = len(wallet_addresses)

        for i, addr in enumerate(wallet_addresses):
            logger.info(f"Scoring {i+1}/{total}: {addr[:10]}...")
            result = self.score(addr, return_explanation=return_explanations)
            results.append(result)
            # Slight rate limit to avoid hammering the RPC
            time.sleep(0.2)

        return results

    def _get_cached_features(
        self,
        wallet_address: str
    ) -> Optional[dict]:
        entry = self._feature_cache.get(wallet_address)
        if entry is None:
            return None
        features, cached_at = entry
        if time.time() - cached_at > self._cache_ttl:
            del self._feature_cache[wallet_address]
            return None
        return features

    def _cache_features(
        self,
        wallet_address: str,
        features: dict
    ):
        self._feature_cache[wallet_address] = (features, time.time())

    def reload_model(self):
        self.model.reload()
        self.preprocessor = FeaturePreprocessor(self.model.models_dir)
        self._feature_cache.clear()
        logger.success("Scorer reloaded with retrained model")

    def _insufficient_history_result(self, address: str) -> Dict:
        return {
            "address": address,
            "hps": 5000,  # Uncertain
            "probability": 0.5,
            "confidence": "low",
            "error": "insufficient_history",
            "computed_at": int(time.time()),
        }

    def _error_result(self, address: str, error: str) -> Dict:
        return {
            "address": address,
            "hps": 5000,
            "probability": 0.5,
            "confidence": "low",
            "error": error,
            "computed_at": int(time.time()),
        }