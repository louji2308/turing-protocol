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
