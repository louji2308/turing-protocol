from web3 import Web3
from web3.types import TxReceipt, TxData
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from loguru import logger
import time
import asyncio
import aiohttp
from dotenv import load_dotenv
import os

load_dotenv()


class MantleDataFetcher:
    """
    Fetches and structures on-chain transaction data from Mantle Network.

    We use both the standard JSON-RPC (for tx details) and the Mantle
    Explorer API (for richer tx history without scanning every block).

    Architecture decision: We use synchronous web3 for individual tx
    lookups but async HTTP for bulk history queries to the explorer API.
    This is the fastest combination for our use case.
    """

    # Known Mantle DeFi protocol contract addresses
    PROTOCOL_ADDRESSES = {
        "merchant_moe_router":  "0xeaEE7EE68874218c3558b40063c42B82D3E7232a",
        "merchant_moe_factory": "0xa6630671775c4EA2743840F9A5016dCf2A104054",
        "agni_pool":            "0x5c0d2247F93c6901f782Ca7fFB1B0E3df6aBb53f",
        "fluxion_vault":        "0x0000000000000000000000000000000000000000",
        "byreal_perps":         "0x0000000000000000000000000000000000000000",
        "meth_staking":         "0xe6829d9a7eE3040e1276Fa75293Bde931859e8fA",
        "usdy_token":           "0x5bE26527e817998A7206475496fDE1E68957c5A6",
        "mnt_token":            "0x78c1b0C915c4FAA5FffA6CAbf0219DA63d7f4cb8",
    }

    def __init__(self, rpc_url: str, max_retries: int = 3):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.max_retries = max_retries
        self._validate_connection()
        chain_id = self.w3.eth.chain_id
        if chain_id == 5003:
            self.MANTLE_EXPLORER_API = "https://explorer.sepolia.mantle.xyz/api"
        else:
            self.MANTLE_EXPLORER_API = "https://explorer.mantle.xyz/api"

    def _validate_connection(self):
        if not self.w3.is_connected():
            raise ConnectionError(
                f"Cannot connect to Mantle RPC. Check your RPC URL."
            )
        logger.info(
            f"Connected to Mantle | Chain ID: {self.w3.eth.chain_id} | "
            f"Block: {self.w3.eth.block_number}"
        )

    def fetch_wallet_transactions(
        self,
        wallet_address: str,
        max_txs: int = 200,
        include_internal: bool = True
    ) -> pd.DataFrame:
        """
        Fetches up to max_txs transactions for a wallet and returns
        a structured DataFrame with all fields needed for feature engineering.

        Returns DataFrame with columns:
        - hash, block_number, timestamp, from_addr, to_addr
        - value_wei, gas_used, gas_price, gas_limit
        - is_contract_interaction, contract_address
        - method_id, success
        - time_since_prev_tx (computed)
        - protocol_tag (which DeFi protocol, if any)
        """
        wallet_address = Web3.to_checksum_address(wallet_address)
        logger.info(f"Fetching transactions for {wallet_address}")

        # Primary method: Explorer API (faster for bulk history)
        txs = self._fetch_from_explorer(wallet_address, max_txs)

        if not txs:
            logger.warning(
                "Explorer API returned no results. "
                "This wallet may have no history."
            )
            return pd.DataFrame()

        df = pd.DataFrame(txs)
        df = self._enrich_dataframe(df, wallet_address)
        df = self._compute_temporal_features(df)
        df = self._tag_protocols(df)

        logger.success(
            f"Fetched {len(df)} transactions for {wallet_address[:10]}..."
        )
        return df

    def _fetch_from_explorer(
        self,
        wallet_address: str,
        max_txs: int
    ) -> List[Dict]:
        """
        Uses Mantle Explorer's account API.
        Returns raw transaction list.
        """
        import requests

        all_txs = []
        page = 1
        per_page = 50  # Explorer API page limit

        while len(all_txs) < max_txs:
            url = (
                f"{self.MANTLE_EXPLORER_API}"
                f"?module=account"
                f"&action=txlist"
                f"&address={wallet_address}"
                f"&startblock=0"
                f"&endblock=latest"
                f"&page={page}"
                f"&offset={per_page}"
                f"&sort=asc"
            )

            for attempt in range(self.max_retries):
                try:
                    response = requests.get(
                        url,
                        timeout=15,
                        headers={"User-Agent": "Mozilla/5.0"},
                    )

                    if response.status_code != 200:
                        logger.warning(
                            f"Explorer returned HTTP {response.status_code} "
                            f"for {wallet_address[:10]}..."
                        )
                        return all_txs

                    try:
                        data = response.json()
                    except Exception as e:
                        logger.warning(
                            f"Explorer did not return JSON for {wallet_address[:10]}...: {e}"
                        )
                        return all_txs

                    if data.get("status") != "1":
                        return all_txs

                    all_txs.extend(data.get("result", []))
                    page += 1
                    break

                except Exception as e:
                    if attempt == self.max_retries - 1:
                        logger.error(f"Explorer API failed after retries: {e}")
                        return all_txs
                    time.sleep(1 * (attempt + 1))  # Exponential backoff

            if len(data["result"]) < per_page:
                # Last page
                break

        return all_txs[:max_txs]

    def _enrich_dataframe(
        self,
        df: pd.DataFrame,
        wallet_address: str
    ) -> pd.DataFrame:
        """
        Standardizes column names, converts types, adds derived fields.
        """
        # Standardize
        df = df.rename(columns={
            "hash": "tx_hash",
            "blockNumber": "block_number",
            "timeStamp": "timestamp",
            "from": "from_addr",
            "to": "to_addr",
            "value": "value_wei",
            "gas": "gas_limit",
            "gasUsed": "gas_used",
            "gasPrice": "gas_price",
            "isError": "failed",
            "input": "input_data",
        })

        # Type conversions
        df["timestamp"] = pd.to_numeric(df["timestamp"])
        df["block_number"] = pd.to_numeric(df["block_number"])
        df["value_wei"] = pd.to_numeric(df["value_wei"])
        df["gas_limit"] = pd.to_numeric(df["gas_limit"])
        df["gas_used"] = pd.to_numeric(df["gas_used"])
        df["gas_price"] = pd.to_numeric(df["gas_price"])
        df["failed"] = df["failed"].astype(int)

        # Derived
        df["success"] = 1 - df["failed"]
        df["value_mnt"] = df["value_wei"] / 1e18
        df["gas_cost_mnt"] = (df["gas_used"] * df["gas_price"]) / 1e18
        df["gas_efficiency"] = df["gas_used"] / df["gas_limit"]

        # Is this tx initiated by our wallet (vs received)?
        df["is_sender"] = (
            df["from_addr"].str.lower() == wallet_address.lower()
        )

        # Is this a contract interaction (has input data beyond "0x")?
        df["is_contract_call"] = (
            df["input_data"].str.len() > 2
        )

        # Extract method ID (first 4 bytes of calldata)
        df["method_id"] = df["input_data"].apply(
            lambda x: x[:10] if len(x) >= 10 else "0x"
        )

        # Sort by time
        df = df.sort_values("timestamp").reset_index(drop=True)

        return df

    def _compute_temporal_features(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Adds time-between-transactions column.
        This is one of the most powerful features for human detection.
        """
        # Time delta between consecutive transactions (in seconds)
        df["time_since_prev_tx"] = df["timestamp"].diff()

        # Time of day (UTC hour) — humans have activity patterns
        df["hour_of_day"] = pd.to_datetime(
            df["timestamp"], unit="s", utc=True
        ).dt.hour

        # Day of week — humans trade less on weekends?
        df["day_of_week"] = pd.to_datetime(
            df["timestamp"], unit="s", utc=True
        ).dt.dayofweek

        return df

    def _tag_protocols(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Tags each transaction with the DeFi protocol it interacted with.
        Critical for interaction diversity features.
        """
        protocol_map = {
            addr.lower(): name
            for name, addr in self.PROTOCOL_ADDRESSES.items()
        }

        df["protocol"] = df["to_addr"].str.lower().map(protocol_map).fillna("unknown")
        df["is_known_protocol"] = df["protocol"] != "unknown"

        return df

    def fetch_multiple_wallets(
        self,
        wallet_addresses: List[str],
        max_txs_each: int = 150
    ) -> Dict[str, pd.DataFrame]:
        """
        Batch fetch for building training dataset.
        Returns dict of {address: DataFrame}
        """
        results = {}
        for i, addr in enumerate(wallet_addresses):
            logger.info(f"Fetching wallet {i+1}/{len(wallet_addresses)}")
            try:
                df = self.fetch_wallet_transactions(addr, max_txs_each)
                if len(df) >= 30:  # Minimum history threshold
                    results[addr] = df
                else:
                    logger.warning(
                        f"Wallet {addr[:10]} has only {len(df)} txs — skipping"
                    )
            except Exception as e:
                logger.error(f"Failed for {addr[:10]}: {e}")

            # Rate limit: Mantle Explorer allows ~5 req/sec
            time.sleep(0.3)

        return results