import json
import os
from typing import Optional
from web3 import Web3
from web3.contract import Contract
from loguru import logger

from oracle_service.config import OracleConfig


ABI_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dashboard", "src", "abi")


class ContractLoader:

    @staticmethod
    def load_abi(contract_name: str) -> Optional[list]:
        path = os.path.join(ABI_DIR, f"{contract_name}.json")
        if not os.path.exists(path):
            alt_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "contracts", "artifacts", "contracts", "src",
                f"{contract_name}.sol", f"{contract_name}.json"
            )
            if os.path.exists(alt_path):
                with open(alt_path) as f:
                    data = json.load(f)
                return data.get("abi", [])
            logger.error(f"ABI not found for {contract_name} at {path}")
            return None
        with open(path) as f:
            data = json.load(f)
        return data.get("abi", data if isinstance(data, list) else [])

    @staticmethod
    def load_hps_oracle(w3: Web3, config: OracleConfig) -> Optional[Contract]:
        abi = ContractLoader.load_abi("HPSOracle")
        if not abi or not config.hps_oracle_address:
            logger.error("Cannot load HPSOracle contract: missing ABI or address")
            return None
        return w3.eth.contract(
            address=Web3.to_checksum_address(config.hps_oracle_address),
            abi=abi
        )

    @staticmethod
    def load_proof_of_behavior(w3: Web3, config: OracleConfig) -> Optional[Contract]:
        abi = ContractLoader.load_abi("ProofOfBehavior")
        if not abi or not config.pob_address:
            logger.error("Cannot load ProofOfBehavior contract: missing ABI or address")
            return None
        return w3.eth.contract(
            address=Web3.to_checksum_address(config.pob_address),
            abi=abi
        )
