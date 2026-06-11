import numpy as np
import os
import time
from typing import Optional, Dict, Any, List
from web3 import Web3
from eth_account import Account
from loguru import logger


class NetworkTopologyModule:

    def __init__(
        self,
        w3: Web3,
        private_key: str,
        peer_wallets: Optional[List[str]] = None,
        seed: Optional[int] = None,
    ):
        self.w3 = w3
        self.account = Account.from_key(private_key)
        self.wallet_address = self.account.address
        self.rng = np.random.default_rng(seed)

        self.peer_wallets = peer_wallets or self._default_peers()
        self.eoa_transfer_ratio = 0.20
        self.min_funding_sources_target = 5

        self._sent_eoa_transfers = 0
        self._funding_sources_seen = set()
        self._last_eoa_transfer_time = 0
        self._transfer_history = []

    def _default_peers(self) -> List[str]:
        raw = os.getenv("GHOST_PEER_WALLETS", "")
        if raw:
            return [w.strip() for w in raw.split(",") if Web3.is_address(w.strip())]
        return []

    def should_send_eoa_transfer(self, total_tx_count: int) -> bool:
        if time.time() - self._last_eoa_transfer_time < 7200:
            return False
        current_ratio = (self._sent_eoa_transfers + 1) / (total_tx_count + 1)
        if current_ratio > self.eoa_transfer_ratio:
            return False
        return self.rng.random() < self.eoa_transfer_ratio

    def generate_eoa_transfer(self) -> Optional[Dict[str, Any]]:
        if not self.peer_wallets:
            return None
        peer = self.rng.choice(self.peer_wallets)
        amount_mnt = self._human_amount()
        amount_wei = int(amount_mnt * 1e18)

        return {
            "type": "eoa_transfer",
            "to": Web3.to_checksum_address(peer),
            "amount_wei": amount_wei,
            "amount_mnt": amount_mnt,
            "gas_estimate": 21000,
            "reason": "peer_transfer",
        }

    def _human_amount(self) -> float:
        if self.rng.random() < 0.70:
            return float(self.rng.choice([0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]))
        return round(float(self.rng.uniform(0.001, 10.0)), 4)

    def record_transfer(self, transfer: Dict, result: Dict):
        self._sent_eoa_transfers += 1
        self._last_eoa_transfer_time = time.time()
        self._transfer_history.append({
            **transfer,
            "result": result,
            "timestamp": int(time.time()),
        })

    def record_funding_source(self, source_address: str):
        self._funding_sources_seen.add(source_address.lower())

    def get_funding_diversity_score(self) -> float:
        count = len(self._funding_sources_seen)
        if count >= self.min_funding_sources_target:
            return 1.0
        return count / self.min_funding_sources_target

    def get_eoa_transfer_ratio(self) -> float:
        total = len(self._transfer_history)
        if total == 0:
            return 0.0
        return self._sent_eoa_transfers / total

    def get_stats(self) -> dict:
        return {
            "sent_eoa_transfers": self._sent_eoa_transfers,
            "unique_funding_sources": len(self._funding_sources_seen),
            "funding_diversity_score": round(self.get_funding_diversity_score(), 3),
            "eoa_transfer_ratio": round(self.get_eoa_transfer_ratio(), 3),
            "peer_wallets_configured": len(self.peer_wallets),
            "last_eoa_transfer": self._last_eoa_transfer_time,
        }
