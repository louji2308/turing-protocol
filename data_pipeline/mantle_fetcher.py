"""
MantleDataFetcher with RPC fallback when explorer API is unavailable.
"""

from web3 import Web3
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from loguru import logger
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
import os

load_dotenv()


class MantleDataFetcher:
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

    # Backup explorer APIs to try in order.
    # Each entry is either:
    #   - a dict {"url": ..., "version": 2}  → Etherscan V2 (uses chainid & apikey params)
    #   - a plain URL string                  → Etherscan V1 (deprecated but kept as fallback)
    EXPLORER_APIS = {
        5003: [
            {"url": "https://api.etherscan.io/v2/api", "version": 2},
            "https://api-sepolia.mantlescan.xyz/api",
            "https://sepolia.mantlescan.xyz/api",
        ],
        5000: [
            {"url": "https://api.etherscan.io/v2/api", "version": 2},
            "https://api.mantlescan.xyz/api",
            "https://explorer.mantle.xyz/api",
            "https://mantlescan.xyz/api",
        ],
    }

    def __init__(self, rpc_url: str, max_retries: int = 3):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.max_retries = max_retries
        self._validate_connection()
        self.chain_id = self.w3.eth.chain_id
        self._explorer_apis = self.EXPLORER_APIS.get(self.chain_id, [])
        self._etherscan_api_key = os.getenv("ETHERSCAN_API_KEY", "").strip()

    def _validate_connection(self):
        if not self.w3.is_connected():
            raise ConnectionError("Cannot connect to Mantle RPC. Check your RPC URL.")
        logger.info(
            f"Connected to Mantle | Chain ID: {self.w3.eth.chain_id} | "
            f"Block: {self.w3.eth.block_number}"
        )

    def _validate_tx_belongs_to_wallet(
        self, txs: List[Dict], wallet_address: str
    ) -> List[Dict]:
        wallet_lower = wallet_address.lower()
        validated = []
        for tx in txs:
            tx_from = (tx.get("from") or "").lower()
            tx_to = (tx.get("to") or "").lower()
            if tx_from == wallet_lower or tx_to == wallet_lower:
                validated.append(tx)
        if len(validated) != len(txs):
            logger.warning(
                f"Filtered {len(txs) - len(validated)} txs not belonging to "
                f"{wallet_address[:10]} (possible API contamination)"
            )
        return validated

    def fetch_wallet_transactions(
        self,
        wallet_address: str,
        max_txs: int = 200,
        include_internal: bool = True
    ) -> pd.DataFrame:
        wallet_address = Web3.to_checksum_address(wallet_address)
        logger.info(f"Fetching transactions for {wallet_address}")

        txs = self._fetch_from_explorer(wallet_address, max_txs)

        if not txs:
            logger.info("Explorer unavailable — falling back to RPC block scan")
            txs = self._fetch_via_rpc(wallet_address, max_txs)

        if not txs:
            logger.warning("No transactions found for this wallet.")
            return pd.DataFrame()

        txs = self._validate_tx_belongs_to_wallet(txs, wallet_address)

        if not txs:
            logger.warning("No valid transactions after ownership validation.")
            return pd.DataFrame()

        df = pd.DataFrame(txs)
        df = self._enrich_dataframe(df, wallet_address)
        df = self._compute_temporal_features(df)
        df = self._tag_protocols(df)

        logger.success(f"Fetched {len(df)} transactions for {wallet_address[:10]}...")
        return df

    def fetch_wallet_transactions_adaptive(
        self,
        wallet_address: str,
        min_txs: int = 50,
        max_txs: int = 500,
        target_days: int = 90,
    ) -> pd.DataFrame:
        wallet_address = Web3.to_checksum_address(wallet_address)
        logger.info(f"Adaptive fetch for {wallet_address} (target={target_days}d, max={max_txs})")

        txs = self._fetch_from_explorer(wallet_address, max_txs)
        if not txs:
            txs = self._fetch_via_rpc(wallet_address, max_txs)
        if not txs:
            return pd.DataFrame()

        txs = self._validate_tx_belongs_to_wallet(txs, wallet_address)
        if not txs:
            return pd.DataFrame()

        df = pd.DataFrame(txs)
        df = self._enrich_dataframe(df, wallet_address)
        df = self._compute_temporal_features(df)
        df = self._tag_protocols(df)

        if len(df) < min_txs:
            logger.warning(f"Only {len(df)} txs for {wallet_address[:10]} (min {min_txs})")
            return df

        if len(df) < 2:
            return df

        time_span = df["timestamp"].max() - df["timestamp"].min()
        span_days = time_span / 86400

        if span_days < target_days and len(df) < max_txs:
            logger.info(f"Time span only {span_days:.0f}d, fetching {max_txs} txs total")
            txs = self._fetch_from_explorer(wallet_address, max_txs)
            if not txs:
                txs = self._fetch_via_rpc(wallet_address, max_txs)
            if txs:
                df = pd.DataFrame(txs)
                df = self._enrich_dataframe(df, wallet_address)
                df = self._compute_temporal_features(df)
                df = self._tag_protocols(df)

        if len(df) > max_txs:
            df = df.iloc[-max_txs:].reset_index(drop=True)

        logger.success(f"Adaptive fetch: {len(df)} txs spanning {span_days:.0f}d for {wallet_address[:10]}")
        return df

    # ------------------------------------------------------------------
    # EXPLORER API (primary — tries all known endpoints)
    # ------------------------------------------------------------------

    def _fetch_from_explorer(self, wallet_address: str, max_txs: int) -> List[Dict]:
        for entry in self._explorer_apis:
            if isinstance(entry, dict) and entry.get("version") == 2:
                result = self._try_explorer_v2(entry["url"], wallet_address, max_txs)
                name = entry["url"]
            else:
                name = entry if isinstance(entry, str) else str(entry)
                result = self._try_explorer_v1(name, wallet_address, max_txs)
            if result is not None:
                return result
            logger.info(f"Explorer endpoint {name} unavailable, trying next...")
        return []

    def _try_explorer_v2(
        self, api_url: str, wallet_address: str, max_txs: int
    ) -> Optional[List[Dict]]:
        if not self._etherscan_api_key:
            logger.debug("V2 endpoint skipped — no ETHERSCAN_API_KEY set")
            return None

        all_txs = []
        page = 1
        per_page = 50

        while len(all_txs) < max_txs:
            params = {
                "chainid": self.chain_id,
                "module": "account",
                "action": "txlist",
                "address": wallet_address,
                "startblock": 0,
                "endblock": "latest",
                "page": page,
                "offset": per_page,
                "sort": "asc",
                "apikey": self._etherscan_api_key,
            }
            try:
                resp = requests.get(
                    api_url,
                    params=params,
                    timeout=5,
                    headers={"User-Agent": "Mozilla/5.0 TuringProtocol/1.0"},
                )
                if resp.status_code != 200:
                    logger.debug(f"Explorer V2 HTTP {resp.status_code} from {api_url}")
                    return None

                data = resp.json()
                if data.get("status") != "1":
                    msg = data.get("message", "")
                    if "No transactions" in msg or "No records" in msg:
                        return all_txs
                    logger.debug(f"Explorer V2 status!=1: {msg} — {data.get('result', '')}")
                    return None

                results = data.get("result", [])
                all_txs.extend(results)

                if len(results) < per_page:
                    break
                page += 1

            except requests.exceptions.RequestException as e:
                logger.debug(f"Explorer V2 request error: {e}")
                return None
            except ValueError as e:
                logger.debug(f"Explorer V2 JSON parse error: {e}")
                return None

        return all_txs[:max_txs]

    def _try_explorer_v1(
        self, api_url: str, wallet_address: str, max_txs: int
    ) -> Optional[List[Dict]]:
        all_txs = []
        page = 1
        per_page = 50

        while len(all_txs) < max_txs:
            url = (
                f"{api_url}"
                f"?module=account&action=txlist"
                f"&address={wallet_address}"
                f"&startblock=0&endblock=latest"
                f"&page={page}&offset={per_page}&sort=asc"
            )
            try:
                resp = requests.get(
                    url,
                    timeout=5,
                    headers={"User-Agent": "Mozilla/5.0 TuringProtocol/1.0"},
                )
                if resp.status_code != 200:
                    logger.debug(f"Explorer V1 HTTP {resp.status_code} from {api_url}")
                    return None

                data = resp.json()
                if data.get("status") != "1":
                    msg = data.get("message", "")
                    if "No transactions" in msg or "No records" in msg:
                        return all_txs
                    logger.debug(f"Explorer V1 status!=1: {msg}")
                    return None

                results = data.get("result", [])
                all_txs.extend(results)

                if len(results) < per_page:
                    break
                page += 1

            except requests.exceptions.RequestException as e:
                logger.debug(f"Explorer V1 request error from {api_url}: {e}")
                return None
            except ValueError as e:
                logger.debug(f"Explorer V1 JSON parse error from {api_url}: {e}")
                return None

        return all_txs[:max_txs]

    # ------------------------------------------------------------------
    # RPC FALLBACK (scans recent blocks when explorer is down)
    # ------------------------------------------------------------------

    def _fetch_via_rpc(self, wallet_address: str, max_txs: int) -> List[Dict]:
        """
        Scans recent blocks looking for transactions from/to wallet_address.
        Uses concurrent block fetching for speed.
        """
        logger.info("Using RPC block-scan fallback (this may take ~15s)...")

        wallet_lower = wallet_address.lower()
        txs = []
        latest = self.w3.eth.block_number
        scan_depth = min(1000, latest)

        logger.info(
            f"Scanning blocks {latest - scan_depth} → {latest} "
            f"(depth={scan_depth})"
        )

        block_numbers = list(range(latest, latest - scan_depth, -1))

        def fetch_block(bn):
            try:
                block = self.w3.eth.get_block(bn, full_transactions=True)
                return block
            except Exception:
                return None

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(fetch_block, bn): bn for bn in block_numbers}
            for future in as_completed(futures):
                if len(txs) >= max_txs:
                    break
                block = future.result()
                if block is None:
                    continue
                for tx in block.transactions:
                    frm = (tx.get("from") or "").lower()
                    to  = (tx.get("to")   or "").lower()
                    if frm == wallet_lower or to == wallet_lower:
                        try:
                            receipt = self.w3.eth.get_transaction_receipt(tx.hash)
                            txs.append(self._rpc_tx_to_dict(tx, block, receipt))
                        except Exception:
                            txs.append(self._rpc_tx_to_dict(tx, block, None))
                        if len(txs) >= max_txs:
                            break

        logger.info(f"RPC scan found {len(txs)} transactions")
        return txs

    def _rpc_tx_to_dict(self, tx, block, receipt) -> Dict:
        """Convert web3 tx / block / receipt objects to the same dict
        schema that the explorer API returns."""
        gas_used  = receipt.gasUsed if receipt else int(tx.gas * 0.8)
        is_error  = 0 if (receipt and receipt.status == 1) else 1
        return {
            "hash":        tx.hash.hex(),
            "blockNumber": str(block.number),
            "timeStamp":   str(block.timestamp),
            "from":        tx["from"],
            "to":          (tx.to or ""),
            "value":       str(tx.value),
            "gas":         str(tx.gas),
            "gasUsed":     str(gas_used),
            "gasPrice":    str(tx.gasPrice),
            "isError":     str(is_error),
            "input":       tx.input.hex() if hasattr(tx.input, "hex") else (tx.input or "0x"),
        }

    # ------------------------------------------------------------------
    # Enrichment helpers (unchanged)
    # ------------------------------------------------------------------

    def _enrich_dataframe(self, df: pd.DataFrame, wallet_address: str) -> pd.DataFrame:
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

        for col in ["timestamp", "block_number", "value_wei",
                    "gas_limit", "gas_used", "gas_price"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df["failed"] = pd.to_numeric(df["failed"], errors="coerce").fillna(0).astype(int)
        df["success"]        = 1 - df["failed"]
        df["value_mnt"]      = df["value_wei"] / 1e18
        df["gas_cost_mnt"]   = (df["gas_used"] * df["gas_price"]) / 1e18
        df["gas_efficiency"] = df["gas_used"] / (df["gas_limit"] + 1e-9)

        df["is_sender"]       = df["from_addr"].str.lower() == wallet_address.lower()
        df["is_contract_call"] = df["input_data"].str.len() > 2
        df["method_id"]       = df["input_data"].apply(
            lambda x: x[:10] if isinstance(x, str) and len(x) >= 10 else "0x"
        )

        # Ensure to_addr is always a string
        df["to_addr"] = df["to_addr"].fillna("").astype(str)

        df = df.sort_values("timestamp").reset_index(drop=True)
        return df

    def _compute_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df["time_since_prev_tx"] = df["timestamp"].diff()
        dt = pd.to_datetime(df["timestamp"], unit="s", utc=True)
        df["hour_of_day"] = dt.dt.hour
        df["day_of_week"]  = dt.dt.dayofweek
        return df

    def _tag_protocols(self, df: pd.DataFrame) -> pd.DataFrame:
        protocol_map = {
            addr.lower(): name
            for name, addr in self.PROTOCOL_ADDRESSES.items()
        }
        df["protocol"]         = df["to_addr"].str.lower().map(protocol_map).fillna("unknown")
        df["is_known_protocol"] = df["protocol"] != "unknown"
        return df

    def fetch_multiple_wallets(
        self, wallet_addresses: List[str], max_txs_each: int = 150
    ) -> Dict[str, pd.DataFrame]:
        results = {}
        for i, addr in enumerate(wallet_addresses):
            logger.info(f"Fetching wallet {i+1}/{len(wallet_addresses)}")
            try:
                df = self.fetch_wallet_transactions(addr, max_txs_each)
                if len(df) >= 30:
                    results[addr] = df
                else:
                    logger.warning(f"Wallet {addr[:10]} only {len(df)} txs — skipping")
            except Exception as e:
                logger.error(f"Failed for {addr[:10]}: {e}")
            time.sleep(0.3)
        return results