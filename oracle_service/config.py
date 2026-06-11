import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class OracleConfig:
    rpc_url: str = field(default_factory=lambda: (
        os.getenv("MANTLE_TESTNET_RPC", "https://rpc.sepolia.mantle.xyz")
        if os.getenv("ACTIVE_NETWORK", "testnet") == "testnet"
        else os.getenv("MANTLE_MAINNET_RPC", "https://rpc.mantle.xyz")
    ))
    chain_id: int = field(default_factory=lambda: (
        int(os.getenv("MANTLE_CHAIN_ID_TESTNET", "5003"))
        if os.getenv("ACTIVE_NETWORK", "testnet") == "testnet"
        else int(os.getenv("MANTLE_CHAIN_ID_MAINNET", "5000"))
    ))
    network: str = field(default_factory=lambda: os.getenv("ACTIVE_NETWORK", "testnet"))
    operator_private_key: str = field(default_factory=lambda: os.getenv("OPERATOR_PRIVATE_KEY", ""))
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

    @classmethod
    def validate(cls, config: "OracleConfig") -> list[str]:
        errors = []
        if not config.rpc_url:
            errors.append("RPC URL not configured")
        if not config.operator_private_key:
            errors.append("OPERATOR_PRIVATE_KEY not set")
        if not config.hps_oracle_address:
            errors.append("HPS_ORACLE_ADDRESS not set")
        if not config.pob_address:
            errors.append("PROOF_OF_BEHAVIOR_ADDRESS not set")
        return errors
