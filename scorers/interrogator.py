from interrogator.scorer import WalletScorer
from data_pipeline.mantle_fetcher import MantleDataFetcher
from loguru import logger
import os


class Interrogator:
    """
    Bridge adapter: wraps WalletScorer into the API the oracle_service expects.
    """

    def __init__(self, ghost_wallet: str = None):
        rpc_url = os.getenv("MANTLE_TESTNET_RPC", "https://rpc.sepolia.mantle.xyz")
        models_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "interrogator", "models"
        )
        self._scorer = WalletScorer(rpc_url=rpc_url, models_dir=models_dir)
        self._fetcher = None
        self._ghost_wallet = ghost_wallet or os.getenv("GHOST_WALLET_ADDRESS")
        logger.success(f"Interrogator initialized with models from {models_dir}")

    def set_fetcher(self, fetcher):
        self._fetcher = fetcher
        if fetcher:
            logger.success("MantleDataFetcher attached to Interrogator")

    def score(self, wallet, use_cache=True, return_explanation=False):
        return self._scorer.score(
            wallet,
            use_cache=use_cache,
            return_explanation=return_explanation,
        )

    def score_batch(self, wallets, return_explanations=False):
        return self._scorer.score_batch(wallets, return_explanations)

    def load_latest_ghost_data(self):
        from interrogator.trainer import load_latest_ghost_data
        return load_latest_ghost_data(ghost_wallet=self._ghost_wallet)

    def adversarial_retrain(self, new_version):
        from interrogator.trainer import adversarial_retrain
        return adversarial_retrain(self, new_version)

    def reload_model(self):
        self._scorer.reload_model()

    def save_model(self, model_path):
        from interrogator.trainer import save_model
        return save_model(self, model_path)
