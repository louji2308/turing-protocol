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

        # Check cache
        cached = self._get_cached_features(wallet_address) if use_cache else None

        if cached is not None:
            features_dict = cached
            logger.debug(f"Using cached features for {wallet_address[:10]}")
        else:
            # Fetch and engineer features
            try:
                df = self.fetcher.fetch_wallet_transactions(
                    wallet_address, max_txs=150
                )
                if len(df) < 10:
                    return self._insufficient_history_result(wallet_address)

                features_dict = self.engineer.compute_all_features(
                    df, wallet_address
                )
                self._cache_features(wallet_address, features_dict)

            except Exception as e:
                logger.error(f"Feature engineering failed for {wallet_address[:10]}: {e}")
                return self._error_result(wallet_address, str(e))

        # Transform for model
        X = self.preprocessor.transform(features_dict)

        # Score
        ml_hps = self.model.score_wallet(X)

        # Hybrid: combine ML prediction with dimension-based scoring
        # Mantle Sepolia block time = 2s
        final_hps, ml_weight, dim_weight, dim_scores = hybrid_hps(
            ml_hps=ml_hps,
            features=features_dict,
            dim_scorer=self.dim_scorer,
            block_time=2.0,
        )
        hps = final_hps
        probability = hps / 10000.0

        # Determine confidence
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

        if return_explanation:
            result["explanation"] = self.model.explain_wallet(X)
            result["fingerprint"] = self.model.compute_behavior_fingerprint(X)

        logger.info(
            f"Scored {wallet_address[:10]}... | "
            f"HPS={hps} ({probability:.1%}) [{confidence}] | "
            f"{result['computation_ms']}ms"
        )

        return result

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