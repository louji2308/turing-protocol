import asyncio
import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional, List

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
_data_pipeline = str(_project_root / "data_pipeline")
if _data_pipeline not in sys.path:
    sys.path.insert(0, _data_pipeline)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from web3 import Web3
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

from oracle_service.config import OracleConfig
from oracle_service.contracts import ContractLoader
from oracle_service.score_loop import ScoreSubmissionLoop
from oracle_service.pob_checker import POBEligibilityChecker
from oracle_service.retrainer import AdversarialRetrainer


config = OracleConfig()

config_errors = OracleConfig.validate(config)
if config_errors:
    logger.warning(f"Oracle config incomplete: {config_errors}")
    if not config.rpc_url:
        logger.error("RPC URL is required. Exiting.")
        sys.exit(1)

w3 = Web3(Web3.HTTPProvider(config.rpc_url, request_kwargs={"timeout": 30}))
if not w3.is_connected():
    logger.error(f"Cannot connect to {config.rpc_url}")
    sys.exit(1)
logger.success(f"Connected to chain {config.chain_id} via {config.rpc_url}")


def _ensure_connected():
    if not w3.is_connected():
        logger.warning("RPC disconnected. Reconnecting...")
        w3.provider = Web3.HTTPProvider(config.rpc_url, request_kwargs={"timeout": 30})
        if not w3.is_connected():
            logger.error("Failed to reconnect to RPC")
            return False
        logger.success("Reconnected to RPC")
    return True

oracle_contract = ContractLoader.load_hps_oracle(w3, config)
pob_contract = ContractLoader.load_proof_of_behavior(w3, config)

if oracle_contract:
    logger.success(f"HPSOracle loaded: {config.hps_oracle_address}")
if pob_contract:
    logger.success(f"ProofOfBehavior loaded: {config.pob_address}")

scorer = None
interrogator = None
score_loop: Optional[ScoreSubmissionLoop] = None
pob_checker: Optional[POBEligibilityChecker] = None
retrainer: Optional[AdversarialRetrainer] = None


class ScoreResponse(BaseModel):
    wallet: str
    hps: int
    error: Optional[str] = None
    details: Optional[dict] = None
    explanation: Optional[list] = None


class LeaderboardEntry(BaseModel):
    wallet: str
    hps: int
    last_updated: int


class HealthResponse(BaseModel):
    status: str
    chain_id: int
    operator: str
    oracle_contract_loaded: bool
    pob_contract_loaded: bool
    scorer_loaded: bool
    score_loop: dict
    pob_checker: dict
    retrainer: dict
    miner_mode: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    global scorer, interrogator, score_loop, pob_checker, retrainer

    try:
        from scorers.interrogator import Interrogator
        interrogator = Interrogator(ghost_wallet=config.ghost_wallet)
        scorer = interrogator
        logger.success(f"Interrogator loaded for scoring | ghost={config.ghost_wallet[:14]}...")
    except Exception as e:
        logger.error(f"Failed to load Interrogator: {e}")

    try:
        from mantle_fetcher import MantleDataFetcher
        if scorer is not None:
            fetcher = MantleDataFetcher(config.rpc_url)
            scorer.set_fetcher(fetcher)
            logger.success("MantleDataFetcher attached to scorer")
    except Exception as e:
        logger.warning(f"Could not attach MantleDataFetcher: {e}")

    if oracle_contract and scorer:
        score_loop = ScoreSubmissionLoop(
            scorer=scorer,
            w3=w3,
            oracle_contract=oracle_contract,
            config=config,
        )
        asyncio.create_task(score_loop.run())
        logger.info("ScoreSubmissionLoop background task started")
    else:
        logger.warning("Score loop not started (missing dependencies)")

    if oracle_contract and pob_contract and scorer:
        pob_checker = POBEligibilityChecker(
            scorer=scorer,
            oracle_contract=oracle_contract,
            pob_contract=pob_contract,
            w3=w3,
            config=config,
        )
        asyncio.create_task(pob_checker.run())
        logger.info("POBEligibilityChecker background task started")

    if interrogator and oracle_contract and scorer:
        retrainer = AdversarialRetrainer(
            interrogator=interrogator,
            scorer=scorer,
            w3=w3,
            oracle_contract=oracle_contract,
            config=config,
        )
        asyncio.create_task(retrainer.run())
        logger.info("AdversarialRetrainer background task started")

    yield

    if score_loop:
        score_loop.stop()
    if pob_checker:
        pob_checker.stop()
    if retrainer:
        retrainer.stop()
    logger.info("Oracle service shutting down")


app = FastAPI(
    title="Turing Protocol Oracle Service",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    miner_mode = os.getenv("MINER_MODE", "active")
    return HealthResponse(
        status="healthy",
        chain_id=config.chain_id,
        operator=w3.eth.default_account or "",
        oracle_contract_loaded=oracle_contract is not None,
        pob_contract_loaded=pob_contract is not None,
        scorer_loaded=scorer is not None,
        score_loop=score_loop.get_stats() if score_loop else {},
        pob_checker=pob_checker.get_stats() if pob_checker else {},
        retrainer=retrainer.get_stats() if retrainer else {},
        miner_mode=miner_mode,
    )


@app.get("/stats")
async def stats():
    total_scored = 0
    total_fresh = 0
    total_minted_val = 0
    try:
        total_scored = oracle_contract.functions.totalScoredWallets().call() if oracle_contract else 0
        total_fresh = pob_contract.functions.totalFreshProofs().call() if pob_contract else 0
        total_minted_val = pob_contract.functions.totalMinted().call() if pob_contract else 0
    except Exception as e:
        logger.debug(f"Stats contract call failed: {e}")
    return {
        "total_scored_wallets": total_scored,
        "total_fresh_proofs": total_fresh,
        "total_minted": total_minted_val,
        "model_version": config.model_version,
        "operator": w3.eth.default_account or "",
    }


@app.get("/score/{wallet}", response_model=ScoreResponse)
async def score_wallet(wallet: str):
    if not Web3.is_address(wallet):
        raise HTTPException(status_code=400, detail=f"Invalid address: {wallet}")
    if scorer is None:
        raise HTTPException(status_code=503, detail="Scorer not available")

    try:
        result = await asyncio.to_thread(
            lambda: scorer.score(wallet, use_cache=True, return_explanation=True)
        )
        return ScoreResponse(
            wallet=Web3.to_checksum_address(wallet),
            hps=int(result.get("hps", 0)),
            error=result.get("error"),
            details=result.get("raw"),
            explanation=result.get("explanation"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/leaderboard", response_model=List[LeaderboardEntry])
async def leaderboard(top_n: int = 50):
    if oracle_contract is None:
        raise HTTPException(status_code=503, detail="Oracle contract not loaded")

    try:
        active_wallets = await score_loop.get_active_wallets() if score_loop else []
        entries = []

        for wallet in active_wallets[:top_n]:
            try:
                score_data = await asyncio.to_thread(
                    lambda w=wallet: oracle_contract.functions.getScore(w).call()
                )
                score = score_data if isinstance(score_data, int) else 0
                last_upd = await asyncio.to_thread(
                    lambda w=wallet: oracle_contract.functions.lastUpdated(w).call()
                )
                last_upd = last_upd if isinstance(last_upd, int) else 0
                entries.append(LeaderboardEntry(
                    wallet=wallet,
                    hps=score,
                    last_updated=last_upd,
                ))
            except Exception:
                continue

        entries.sort(key=lambda e: e.hps, reverse=True)
        return entries[:top_n]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ghost/telemetry")
async def ghost_telemetry():
    if retrainer is None:
        raise HTTPException(status_code=503, detail="Retrainer not available")
    return retrainer.get_stats()


@app.post("/admin/retrain")
async def trigger_retrain():
    if retrainer is None:
        raise HTTPException(status_code=503, detail="Retrainer not available")
    if retrainer._is_retraining:
        raise HTTPException(status_code=409, detail="Retraining already in progress")

    ghost_score = 0
    try:
        if oracle_contract and config.ghost_wallet:
            score_data = oracle_contract.functions.getScore(config.ghost_wallet).call()
            ghost_score = score_data if isinstance(score_data, int) else 0
    except Exception:
        pass

    asyncio.create_task(retrainer._execute_retraining(ghost_score))
    return {
        "status": "triggered",
        "ghost_score": ghost_score,
        "from_version": retrainer._current_model_version,
        "target_version": retrainer._current_model_version + 1,
    }


@app.get("/admin/score-loop/status")
async def score_loop_status():
    if score_loop is None:
        raise HTTPException(status_code=503, detail="Score loop not running")
    return score_loop.get_stats()


@app.post("/admin/score-loop/trigger")
async def trigger_immediate_update():
    if score_loop is None:
        raise HTTPException(status_code=503, detail="Score loop not running")
    asyncio.create_task(score_loop._run_update_cycle())
    return {"status": "triggered"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("oracle_service.main:app", host="0.0.0.0", port=8080, log_level="info")
