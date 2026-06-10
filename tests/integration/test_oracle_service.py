import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from oracle_service.config import OracleConfig
from oracle_service.score_loop import ScoreSubmissionLoop
from oracle_service.pob_checker import POBEligibilityChecker
from oracle_service.retrainer import AdversarialRetrainer


@pytest.fixture
def mock_w3():
    w3 = MagicMock()
    w3.is_connected.return_value = True
    w3.eth.block_number = 1000000
    w3.eth.get_transaction_count.return_value = 5
    w3.eth.gas_price = 1000000000
    w3.eth.estimate_gas.return_value = 200000
    w3.eth.default_account = "0xOperator"
    return w3


@pytest.fixture
def mock_oracle_contract():
    contract = MagicMock()
    contract.functions.getScore.return_value.call.return_value = 7500
    contract.functions.lastUpdated.return_value.call.return_value = 2000000
    contract.functions.batchUpdateScores.return_value.build_transaction.return_value = {
        "from": "0xOperator",
        "nonce": 5,
        "gas": 500000,
        "gasPrice": 1000000000,
    }
    contract.events.ScoreUpdated.get_logs.return_value = [
        {"args": {"wallet": "0x1234567890abcdef1234567890abcdef12345678"}},
        {"args": {"wallet": "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"}},
    ]
    return contract


@pytest.fixture
def mock_pob_contract():
    contract = MagicMock()
    contract.functions.mint.return_value.build_transaction.return_value = {
        "from": "0xOperator",
        "nonce": 5,
        "gas": 300000,
        "gasPrice": 1000000000,
    }
    contract.functions.updateFreshness.return_value.build_transaction.return_value = {
        "from": "0xOperator",
        "nonce": 5,
        "gas": 100000,
        "gasPrice": 1000000000,
    }
    contract.functions.walletToTokenId.return_value.call.return_value = 0
    contract.events.ProofMinted.get_logs.return_value = []
    return contract


@pytest.fixture
def mock_scorer():
    scorer = MagicMock()
    def score_side_effect(addr, *args, **kwargs):
        return {
            "hps": 7500 if "1234" in addr else 3000,
            "error": None,
        }
    scorer.score.side_effect = score_side_effect
    return scorer


@pytest.fixture
def mock_interrogator():
    inter = MagicMock()
    inter.load_latest_ghost_data.return_value = None
    inter.adversarial_retrain.return_value = None
    inter.save_model.return_value = None
    return inter


@pytest.fixture
def config():
    cfg = OracleConfig()
    cfg.rpc_url = "https://rpc.testnet.mantle.xyz"
    cfg.chain_id = 5003
    cfg.operator_private_key = "0x" + "ab" * 32
    cfg.hps_oracle_address = "0x" + "12" * 20
    cfg.pob_address = "0x" + "34" * 20
    cfg.ghost_wallet = "0x" + "56" * 20
    cfg.update_interval = 60
    cfg.pob_threshold = 7000
    cfg.pob_sustained_hours = 72
    cfg.min_tx_history = 50
    cfg.model_version = 100
    cfg.max_concurrent_scores = 5
    cfg.batch_chunk_size = 100
    return cfg


class TestScoreSubmissionLoop:

    @pytest.mark.asyncio
    async def test_run_update_cycle(self, mock_scorer, mock_w3, mock_oracle_contract, config):
        loop = ScoreSubmissionLoop(mock_scorer, mock_w3, mock_oracle_contract, config)

        mock_w3.eth.send_raw_transaction.return_value = b"\x01" * 32
        mock_w3.eth.wait_for_transaction_receipt.return_value = {"status": 1}

        await loop._run_update_cycle()

        assert loop._total_updates == 1
        assert loop._total_wallets_updated > 0

    @pytest.mark.asyncio
    async def test_get_active_wallets(self, mock_scorer, mock_w3, mock_oracle_contract, config):
        loop = ScoreSubmissionLoop(mock_scorer, mock_w3, mock_oracle_contract, config)
        wallets = await loop._get_active_wallets()
        assert len(wallets) > 0
        assert config.ghost_wallet in wallets

    def test_get_stats(self, mock_scorer, mock_w3, mock_oracle_contract, config):
        loop = ScoreSubmissionLoop(mock_scorer, mock_w3, mock_oracle_contract, config)
        stats = loop.get_stats()
        assert "total_updates" in stats
        assert stats["model_version"] == 100
        assert stats["operator"] is not None


class TestPOBEligibilityChecker:

    @pytest.mark.asyncio
    async def test_evaluate_wallet_above_threshold(
        self, mock_scorer, mock_w3, mock_oracle_contract, mock_pob_contract, config
    ):
        checker = POBEligibilityChecker(
            mock_scorer, mock_oracle_contract, mock_pob_contract, mock_w3, config
        )

        wallet = Web3.to_checksum_address("0x1234567890abcdef1234567890abcdef12345678")
        await checker._evaluate_wallet(wallet)

        assert wallet.lower() in checker._tracked_wallets

    def test_get_stats(self, mock_scorer, mock_w3, mock_oracle_contract, mock_pob_contract, config):
        checker = POBEligibilityChecker(
            mock_scorer, mock_oracle_contract, mock_pob_contract, mock_w3, config
        )
        stats = checker.get_stats()
        assert stats["threshold"] == 7000


class TestAdversarialRetrainer:

    def test_should_trigger_retraining(self, mock_interrogator, mock_scorer, mock_w3, mock_oracle_contract, config):
        retrainer = AdversarialRetrainer(
            mock_interrogator, mock_scorer, mock_w3, mock_oracle_contract, config
        )

        retrainer._recent_ghost_scores = [
            {"timestamp": 1000, "score": 8000},
            {"timestamp": 2000, "score": 7900},
            {"timestamp": 3000, "score": 8100},
            {"timestamp": 4000, "score": 8200},
            {"timestamp": 5000, "score": 8000},
        ]

        assert retrainer._should_trigger_retraining(8000) is True

    def test_should_not_trigger_below_threshold(self, mock_interrogator, mock_scorer, mock_w3, mock_oracle_contract, config):
        retrainer = AdversarialRetrainer(
            mock_interrogator, mock_scorer, mock_w3, mock_oracle_contract, config
        )
        assert retrainer._should_trigger_retraining(5000) is False

    def test_get_stats(self, mock_interrogator, mock_scorer, mock_w3, mock_oracle_contract, config):
        retrainer = AdversarialRetrainer(
            mock_interrogator, mock_scorer, mock_w3, mock_oracle_contract, config
        )
        stats = retrainer.get_stats()
        assert stats["current_model_version"] == 100


from web3 import Web3
