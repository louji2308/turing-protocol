import time
import os
import sys
import httpx
from web3 import Web3
from web3.middleware import geth_poa_middleware

from typing import Optional

_project_root = os.path.dirname(os.path.dirname(__file__))
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

ORACLE_API = os.getenv("TURING_ORACLE_API", "https://turing-oracle.onrender.com")
MANTLE_RPC = os.getenv(
    "MANTLE_TESTNET_RPC",
    os.getenv("MANTLE_RPC", "https://rpc.sepolia.mantle.xyz"),
)
HPS_ORACLE_ADDR = os.getenv(
    "HPS_ORACLE_ADDRESS",
    "0x824e72507C94E2A615400049167a661469351A1D",
)

HPS_ORACLE_ABI = [
    {
        "name": "getScoreWithFreshness",
        "type": "function",
        "stateMutability": "view",
        "inputs": [
            {"name": "wallet", "type": "address"},
            {"name": "maxStalenessSeconds", "type": "uint256"},
        ],
        "outputs": [
            {"name": "score", "type": "uint16"},
            {"name": "isFresh", "type": "bool"},
        ],
    },
    {
        "name": "isHuman",
        "type": "function",
        "stateMutability": "view",
        "inputs": [
            {"name": "wallet", "type": "address"},
            {"name": "threshold", "type": "uint16"},
        ],
        "outputs": [{"name": "", "type": "bool"}],
    },
    {
        "name": "getScore",
        "type": "function",
        "stateMutability": "view",
        "inputs": [{"name": "wallet", "type": "address"}],
        "outputs": [{"name": "", "type": "uint16"}],
    },
]

_cache: dict[str, tuple[float, dict]] = {}
CACHE_TTL_SECONDS = 3600


class ScoreResolver:
    def __init__(
        self,
        rpc_url: str = MANTLE_RPC,
        oracle_addr: str = HPS_ORACLE_ADDR,
        oracle_api: str = ORACLE_API,
        http_timeout: float = 8.0,
    ):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 30}))
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.oracle = self.w3.eth.contract(
            address=Web3.to_checksum_address(oracle_addr), abi=HPS_ORACLE_ABI
        )
        self.oracle_api = oracle_api
        self.http_timeout = http_timeout

    def resolve(self, address: str, max_staleness: int = 7200) -> dict:
        address = Web3.to_checksum_address(address)

        cached = _cache.get(address)
        if cached and (time.time() - cached[0]) < CACHE_TTL_SECONDS:
            out = dict(cached[1])
            out["source"] = "cache"
            return out

        skip_api = os.getenv("TURING_SKIP_API", "").lower() in ("1", "true", "yes")

        if not skip_api:
            try:
                resp = httpx.get(
                    f"{self.oracle_api}/score/{address}",
                    timeout=self.http_timeout,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    error_field = data.get("error") or data.get("detail")
                    if error_field is None:
                        hps = data.get("hps")
                        explanation = data.get("explanation") or data.get("details")
                        result = {
                            "address": address,
                            "hps": int(hps) if hps is not None else None,
                            "confidence": data.get("confidence", "unknown"),
                            "uncertainty": data.get("uncertainty"),
                            "model_version": data.get("model_version"),
                            "computed_at": data.get("computed_at"),
                            "dimension_scores": data.get("dimension_scores") or data.get("details"),
                            "explanation": explanation,
                            "fresh_proof": data.get("fresh_proof"),
                            "source": "oracle_api",
                        }
                        _cache[address] = (time.time(), result)
                        return result
            except (httpx.TimeoutException, httpx.HTTPError, Exception):
                pass

        try:
            score, is_fresh = self.oracle.functions.getScoreWithFreshness(
                address, max_staleness
            ).call()
            score_int = int(score)
            result = {
                "address": address,
                "hps": score_int if score_int > 0 else None,
                "confidence": "unknown",
                "uncertainty": None,
                "model_version": None,
                "computed_at": None,
                "fresh_proof": is_fresh,
                "dimension_scores": None,
                "explanation": None,
                "source": "onchain_fallback" if score_int > 0 else "onchain_unscored",
                "is_fresh": is_fresh,
            }
            _cache[address] = (time.time(), result)
            return result
        except Exception as e:
            return {
                "address": address,
                "hps": None,
                "confidence": "unknown",
                "source": "error",
                "error": str(e),
            }

    def resolve_with_fresh_proof(
        self, address: str, pob_address: str | None = None
    ) -> bool | None:
        try:
            address = Web3.to_checksum_address(address)
            if pob_address:
                pob_addr = Web3.to_checksum_address(pob_address)
                min_abi = [
                    {
                        "name": "hasFreshProof",
                        "type": "function",
                        "stateMutability": "view",
                        "inputs": [{"name": "wallet", "type": "address"}],
                        "outputs": [{"name": "", "type": "bool"}],
                    }
                ]
                pob = self.w3.eth.contract(address=pob_addr, abi=min_abi)
                return pob.functions.hasFreshProof(address).call()
            return None
        except Exception:
            return None

    def is_human(self, address: str, threshold: int) -> bool | None:
        try:
            address = Web3.to_checksum_address(address)
            return self.oracle.functions.isHuman(address, threshold).call()
        except Exception:
            return None

    def get_raw_score(self, address: str) -> int | None:
        try:
            address = Web3.to_checksum_address(address)
            score = self.oracle.functions.getScore(address).call()
            return int(score)
        except Exception:
            return None


def resolve_with_cold_start(
    resolver: ScoreResolver, address: str, wait: bool = False
) -> dict:
    result = resolver.resolve(address)
    if result.get("source") == "onchain_unscored" and wait:
        skip_api = os.getenv("TURING_SKIP_API", "").lower() in ("1", "true", "yes")
        if not skip_api:
            try:
                resp = httpx.get(
                    f"{ORACLE_API}/score/{address}",
                    timeout=20.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    error_field = data.get("error") or data.get("detail")
                    if error_field is None:
                        result = {
                            **result,
                            "hps": int(data.get("hps", 0)) if data.get("hps") else None,
                            "source": "oracle_api_cold_start",
                        }
            except httpx.HTTPError:
                pass
    return result
