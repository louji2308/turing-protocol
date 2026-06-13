import os
from dataclasses import dataclass, field
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()


def _rpc_list(var: str, default: str) -> List[str]:
    raw = os.getenv(var, default)
    return [u.strip() for u in raw.split(",") if u.strip()]


def _operator_keys(var: str) -> List[str]:
    raw = os.getenv(var, "")
    return [k.strip() for k in raw.split(",") if k.strip().startswith("0x")]


@dataclass
class OracleConfig:
    rpc_urls: List[str] = field(default_factory=lambda: (
        _rpc_list("MANTLE_TESTNET_RPC", "https://rpc.sepolia.mantle.xyz")
        if os.getenv("ACTIVE_NETWORK", "testnet") == "testnet"
        else _rpc_list("MANTLE_MAINNET_RPC", "https://rpc.mantle.xyz")
    ))
    chain_id: int = field(default_factory=lambda: (
        int(os.getenv("MANTLE_CHAIN_ID_TESTNET", "5003"))
        if os.getenv("ACTIVE_NETWORK", "testnet") == "testnet"
        else int(os.getenv("MANTLE_CHAIN_ID_MAINNET", "5000"))
    ))
    network: str = field(default_factory=lambda: os.getenv("ACTIVE_NETWORK", "testnet"))

    operator_private_key: str = field(default_factory=lambda: os.getenv("OPERATOR_PRIVATE_KEY", ""))
    operator_private_keys: List[str] = field(default_factory=lambda: _operator_keys("OPERATOR_PRIVATE_KEYS"))

    hps_oracle_address: str = field(default_factory=lambda: os.getenv("HPS_ORACLE_ADDRESS", ""))
    pob_address: str = field(default_factory=lambda: os.getenv("PROOF_OF_BEHAVIOR_ADDRESS", ""))
    ghost_wallet: str = field(default_factory=lambda: os.getenv("GHOST_WALLET_ADDRESS", ""))

    update_interval: int = field(default_factory=lambda: int(os.getenv("ORACLE_UPDATE_INTERVAL_SECONDS", "900")))
    pob_threshold: int = field(default_factory=lambda: int(os.getenv("POB_SCORE_THRESHOLD", "7000")))
    pob_sustained_hours: float = field(default_factory=lambda: float(os.getenv("POB_SUSTAINED_HOURS", "72")))
    min_tx_history: int = field(default_factory=lambda: int(os.getenv("MIN_TX_HISTORY", "50")))
    model_version: int = 100
    score_cache_ttl: int = 900
    max_concurrent_scores: int = 10
    batch_chunk_size: int = 100

    max_rpc_retries: int = field(default_factory=lambda: int(os.getenv("MAX_RPC_RETRIES", "3")))
    rpc_retry_delay: int = field(default_factory=lambda: int(os.getenv("RPC_RETRY_DELAY_SECONDS", "5")))
    admin_api_key: str = field(default_factory=lambda: os.getenv("ADMIN_API_KEY", ""))

    # IMPL-01: Investment Intelligence thresholds
    smart_money_hps_threshold: int = 8500
    human_hps_threshold: int = 7000
    bot_heavy_hps_threshold: int = 4000
    protocol_sample_cap: int = 200
    emerging_growth_threshold: float = 0.50
    emerging_min_prior_humans: int = 5
    intelligence_cycle_seconds: int = 3600
    smart_money_cycle_seconds: int = 900
    sybil_cycle_seconds: int = 21600

    mantle_protocols: dict = field(default_factory=lambda: {
        "Agni Finance":      "0x319B69888b0d11cEC22caA5034e25FfFBDc88421",
        "Merchant Moe":      "0xeaEE7EE68874218c3558b40063c42B82D3E7232a",
        "Aurelius":          "0xa3Dd459A9A75b8EFDa7f48Fc4Bae83038d2D20c9",
        "Lendle":            "0xCFa5aE7c2CE8Fadc6426C1ff872cA45378Fb7cF",
        "Init Capital":      "0x972B1E7EB42c8E0A2B0D76aA44a979c5dD1C7e6",
        "Cleopatra DEX":     "0xAAA16c016BF556fcD620328f0759252E29b2AB5B",
        "Fenix Finance":     "0x3aBed1dF619e9f1C88F3D3Bc5C5b9c9ABbB9eF91",
        "Symbiotic":         "0x67E1Fb2E2B5A1E0b9C0A1b2C3D4E5F6a7b8c9d0e",
        "Pendle":            "0x1b8eFfD9c1a23C4e5F6a7B8c9D0e1F2a3B4c5D6e",
        "LayerBank":         "0x5C9d0E1F2a3B4c5D6e7F8a9b0C1d2E3f4A5b6C7",
    })

    active_networks: List[str] = field(default_factory=lambda: ["mantle_testnet", "mantle_mainnet"])
    network_config: dict = field(default_factory=lambda: {
        "mantle_testnet": {
            "rpc": "https://rpc.sepolia.mantle.xyz",
            "chain_id": 5003,
            "hps_oracle": os.getenv("HPS_ORACLE_ADDRESS", ""),
            "proof_of_behavior": os.getenv("PROOF_OF_BEHAVIOR_ADDRESS", ""),
            "explorer": "https://explorer.testnet.mantle.xyz",
        },
        "mantle_mainnet": {
            "rpc": "https://rpc.mantle.xyz",
            "chain_id": 5000,
            "hps_oracle": os.getenv("HPS_ORACLE_ADDRESS_MAINNET", ""),
            "proof_of_behavior": os.getenv("PROOF_OF_BEHAVIOR_ADDRESS_MAINNET", ""),
            "explorer": "https://explorer.mantle.xyz",
        },
    })

    def get_operator_addresses(self) -> List[str]:
        from eth_account import Account
        addresses = []
        for key in self.operator_private_keys:
            try:
                addresses.append(Account.from_key(key).address)
            except Exception:
                continue
        return addresses

    @classmethod
    def validate(cls, config: "OracleConfig") -> list[str]:
        errors = []
        if not config.rpc_urls:
            errors.append("No RPC URLs configured")
        if not config.operator_private_key and not config.operator_private_keys:
            errors.append("No operator private key(s) configured")
        elif config.operator_private_key:
            if not config.operator_private_key.startswith("0x") or len(config.operator_private_key) != 66:
                errors.append("OPERATOR_PRIVATE_KEY has invalid format (must be 0x-prefixed 64-char hex)")
        if not config.hps_oracle_address:
            errors.append("HPS_ORACLE_ADDRESS not set")
        if not config.pob_address:
            errors.append("PROOF_OF_BEHAVIOR_ADDRESS not set")
        return errors
