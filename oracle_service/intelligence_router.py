from __future__ import annotations

import asyncio
import time
from collections import defaultdict

from fastapi import APIRouter, HTTPException, Query, Depends
from loguru import logger
from pydantic import BaseModel, Field

from oracle_service.config import OracleConfig
from oracle_service.score_cache import ScoreCache, get_cache
from data_pipeline.mantle_fetcher import MantleDataFetcher
from scorers.interrogator import Interrogator
from interrogator.scorer import WalletScorer

router = APIRouter(prefix="/api/v1/intelligence", tags=["intelligence"])

config = OracleConfig()


# -------------------------------------------------------------------
# Pydantic response models
# -------------------------------------------------------------------

class ProtocolHumanness(BaseModel):
    protocol: str = Field(..., description="Human-readable protocol name")
    address: str
    wallets_sampled: int
    human_ratio: float = Field(..., description="Fraction of sampled wallets with HPS >= 7000")
    avg_hps: int
    median_hps: int
    hps_p25: int
    hps_p75: int
    bot_heavy_count: int = Field(..., description="Wallets with HPS < 4000")
    genuine_human_count: int
    trend_7d: float | None = Field(None, description="Delta human_ratio vs 7 days ago")
    trend_30d: float | None = Field(None, description="Delta human_ratio vs 30 days ago")
    computed_at: int


class ProtocolHealthDetail(ProtocolHumanness):
    history: list[dict] = Field(..., description="Time series of human_ratio, avg_hps")


class SmartMoneyFlow(BaseModel):
    protocol: str
    address: str
    inflow_mnt: float
    outflow_mnt: float
    net_flow_mnt: float
    unique_smart_wallets: int


class SmartMoneyFlowsResponse(BaseModel):
    period_days: int
    smart_wallet_count: int
    threshold_hps: int
    top_flows: list[SmartMoneyFlow]
    computed_at: int


class EmergingProtocol(BaseModel):
    protocol: str
    address: str
    human_growth_pct: float
    recent_human_count: int
    prior_human_count: int
    signal: str


class AirdropExposureRequest(BaseModel):
    protocol_address: str
    claimant_addresses: list[str] | None = Field(
        None, description="Optional explicit claimant list; if omitted, uses fetch_protocol_interactors as a proxy snapshot."
    )
    threshold: int = Field(7000, ge=0, le=10000)
    snapshot_block: int | None = None


class ThresholdSensitivity(BaseModel):
    passes: int
    human_pct: float


class AirdropExposureResponse(BaseModel):
    total_claimants: int
    scored: int
    human_above_threshold: int
    bot_exposure_pct: float
    recommended_threshold: int
    threshold_sensitivity: dict[str, ThresholdSensitivity]
    computed_at: int


class SmartMoneyWallet(BaseModel):
    address: str
    hps: int
    last_updated: int


class SmartMoneyWalletsResponse(BaseModel):
    count: int
    wallets: list[SmartMoneyWallet]
    computed_at: int


# -------------------------------------------------------------------
# Dependencies (wired from main.py app.state)
# -------------------------------------------------------------------

def _get_app_state():
    """Lazy import to avoid circular dependency at module load time."""
    from fastapi.concurrency import run_in_threadpool
    import oracle_service.main as main_mod
    return main_mod.app.state


def get_fetcher() -> MantleDataFetcher:
    state = _get_app_state()
    fetcher = getattr(state, "fetcher", None)
    if fetcher is None:
        raise HTTPException(status_code=503, detail="fetcher not available")
    return fetcher


def get_scorer() -> WalletScorer:
    state = _get_app_state()
    scorer = getattr(state, "scorer_instance", None)
    if scorer is None:
        raise HTTPException(status_code=503, detail="scorer not available")
    return scorer


# -------------------------------------------------------------------
# IMPL-01A — Protocol Humanness Score
# -------------------------------------------------------------------

@router.get(
    "/protocols",
    response_model=list[ProtocolHumanness],
    summary="Ranked list of all tracked Mantle protocols by human_ratio",
    description=(
        "Returns every protocol in MANTLE_PROTOCOLS with its current Protocol "
        "Humanness Score (PHS): the fraction of recent unique interactors that "
        "are verified human (HPS >= 7000). Sorted descending by human_ratio. "
        "This is the single number a VC should look at first."
    ),
)
async def list_protocols(cache: ScoreCache = Depends(get_cache)) -> list[ProtocolHumanness]:
    rows = cache.get_latest_protocol_health()
    if not rows:
        raise HTTPException(status_code=503, detail="insufficient_data: intelligence cycle has not run yet")
    out = []
    for r in rows:
        trend_7d = cache.compute_trend(r["protocol_address"], "human_ratio", days=7)
        trend_30d = cache.compute_trend(r["protocol_address"], "human_ratio", days=30)
        out.append(ProtocolHumanness(
            protocol=r["protocol_name"], address=r["protocol_address"],
            wallets_sampled=r["wallets_sampled"], human_ratio=r["human_ratio"],
            avg_hps=r["avg_hps"], median_hps=r["median_hps"],
            hps_p25=r["hps_p25"], hps_p75=r["hps_p75"],
            bot_heavy_count=r["bot_heavy_count"], genuine_human_count=r["genuine_human_count"],
            trend_7d=trend_7d, trend_30d=trend_30d, computed_at=r["computed_at"],
        ))
    return sorted(out, key=lambda p: p.human_ratio, reverse=True)


@router.get(
    "/protocols/{address}/health",
    response_model=ProtocolHealthDetail,
    summary="Deep-dive on a single protocol's human-activity health over time",
)
async def protocol_health(address: str, days: int = Query(30, ge=1, le=90),
                           cache: ScoreCache = Depends(get_cache)) -> ProtocolHealthDetail:
    latest = cache.get_latest_protocol_health(address=address)
    if not latest:
        raise HTTPException(status_code=404, detail=f"no health data for {address}")
    latest = latest[0]
    history = cache.get_protocol_health_history(address, days)
    trend_7d = cache.compute_trend(address, "human_ratio", days=7)
    trend_30d = cache.compute_trend(address, "human_ratio", days=30)
    return ProtocolHealthDetail(
        protocol=latest["protocol_name"], address=latest["protocol_address"],
        wallets_sampled=latest["wallets_sampled"], human_ratio=latest["human_ratio"],
        avg_hps=latest["avg_hps"], median_hps=latest["median_hps"],
        hps_p25=latest["hps_p25"], hps_p75=latest["hps_p75"],
        bot_heavy_count=latest["bot_heavy_count"], genuine_human_count=latest["genuine_human_count"],
        trend_7d=trend_7d, trend_30d=trend_30d, computed_at=latest["computed_at"],
        history=history,
    )


@router.get(
    "/protocols/{address}/holders",
    summary="Top human wallets interacting with this protocol (VC due-diligence list)",
)
async def protocol_holders(
    address: str, limit: int = Query(20, ge=1, le=100),
    cache: ScoreCache = Depends(get_cache), fetcher: MantleDataFetcher = Depends(get_fetcher),
) -> dict:
    interactors = await fetcher.fetch_protocol_interactors(address, days=30)
    scored = []
    sem = asyncio.Semaphore(10)

    async def _score(addr: str):
        async with sem:
            s = cache.get_cached_score(addr)
            if s:
                scored.append((addr, s["hps"]))

    await asyncio.gather(*(_score(a) for a in interactors[:config.protocol_sample_cap]))
    top = sorted(scored, key=lambda x: x[1], reverse=True)[:limit]
    return {
        "protocol": address,
        "top_human_wallets": [{"address": a, "hps": h} for a, h in top if h >= config.human_hps_threshold],
        "computed_at": int(time.time()),
    }


# -------------------------------------------------------------------
# IMPL-01B — Smart Money Flow Tracker
# -------------------------------------------------------------------

@router.get(
    "/smart-money/flows",
    response_model=SmartMoneyFlowsResponse,
    summary="Where are wallets with HPS >= 8500 deploying capital right now?",
    description=(
        "Smart money = wallets with Human Probability Score >= "
        f"{config.smart_money_hps_threshold} (top ~5% confidence band). "
        "Aggregates their recent on-chain transfers by destination protocol "
        "and ranks protocols by net inflow."
    ),
)
async def smart_money_flows(
    days: int = Query(14, ge=1, le=30), cache: ScoreCache = Depends(get_cache),
) -> SmartMoneyFlowsResponse:
    rows = cache.get_latest_smart_money_flows(period_days=days)
    if not rows:
        raise HTTPException(status_code=503, detail="insufficient_data")
    smart_wallets = cache.get_wallets_above_threshold(config.smart_money_hps_threshold)
    flows = [
        SmartMoneyFlow(
            protocol=r["protocol_name"], address=r["protocol_address"],
            inflow_mnt=r["inflow_mnt"], outflow_mnt=r["outflow_mnt"],
            net_flow_mnt=r["net_flow_mnt"], unique_smart_wallets=r["unique_smart_wallets"],
        )
        for r in rows
    ]
    return SmartMoneyFlowsResponse(
        period_days=days, smart_wallet_count=len(smart_wallets),
        threshold_hps=config.smart_money_hps_threshold,
        top_flows=sorted(flows, key=lambda f: f.net_flow_mnt, reverse=True)[:15],
        computed_at=int(time.time()),
    )


@router.get(
    "/smart-money/wallets",
    response_model=SmartMoneyWalletsResponse,
    summary="Ranked list of highest-HPS wallets with behavioral fingerprints",
)
async def smart_money_wallets(
    limit: int = Query(50, ge=1, le=200), cache: ScoreCache = Depends(get_cache),
) -> SmartMoneyWalletsResponse:
    wallets = cache.get_top_wallets_by_hps(limit=limit, min_hps=config.smart_money_hps_threshold)
    return SmartMoneyWalletsResponse(
        count=len(wallets),
        wallets=[SmartMoneyWallet(**w) for w in wallets],
        computed_at=int(time.time()),
    )


@router.get(
    "/smart-money/alerts",
    summary="New smart-money entrants (last 24h) and protocol inflow spikes",
    description=(
        "Two alert types: (1) wallets that crossed the smart-money HPS threshold "
        "in the last 24 hours, (2) protocols whose smart-money net inflow jumped "
        ">2x vs the prior period. Computed by IntelligenceAggregator's background loop."
    ),
)
async def smart_money_alerts(cache: ScoreCache = Depends(get_cache)) -> dict:
    alerts = cache.get_recent_alerts(hours=24)
    return {"alerts": alerts, "count": len(alerts), "computed_at": int(time.time())}


# -------------------------------------------------------------------
# IMPL-01C — Emerging Protocol Detection
# -------------------------------------------------------------------

@router.get(
    "/emerging",
    response_model=list[EmergingProtocol],
    summary="Protocols gaining verified human users fastest, right now",
    description=(
        "Compares verified-human interactor counts in the most recent "
        "`days`-day window vs the prior `days`-day window, per protocol. "
        "Protocols with >50% growth and a meaningful prior baseline "
        f"(>= {config.emerging_min_prior_humans} prior human interactors) "
        "are flagged 'accelerating' (50-100% growth) or 'organic_traction' (>100%). "
    ),
)
async def emerging_protocols(
    days: int = Query(7, ge=1, le=30), cache: ScoreCache = Depends(get_cache),
) -> list[EmergingProtocol]:
    rows = cache.get_emerging_protocols(days=days)
    return [
        EmergingProtocol(
            protocol=r["protocol_name"], address=r["protocol_address"],
            human_growth_pct=r["human_growth_pct"],
            recent_human_count=r["recent_human_count"],
            prior_human_count=r["prior_human_count"], signal=r["signal"],
        )
        for r in sorted(rows, key=lambda x: x["human_growth_pct"], reverse=True)
    ]


# -------------------------------------------------------------------
# IMPL-01D — Airdrop Farming Exposure Calculator
# -------------------------------------------------------------------

@router.post(
    "/airdrop-exposure",
    response_model=AirdropExposureResponse,
    summary="Estimate what % of an airdrop would be captured by bots if ungated",
    description=(
        "Given a protocol address (and optionally an explicit claimant list / "
        "snapshot block), scores all claimants and reports the bot-capture "
        "exposure at the requested threshold, plus a sensitivity table at "
        "thresholds 5000/7000/8000 so the protocol team can pick a cutoff."
    ),
)
async def airdrop_exposure(
    req: AirdropExposureRequest,
    cache: ScoreCache = Depends(get_cache),
    fetcher: MantleDataFetcher = Depends(get_fetcher),
    scorer: WalletScorer = Depends(get_scorer),
) -> AirdropExposureResponse:
    claimants = req.claimant_addresses
    if not claimants:
        claimants = await fetcher.fetch_protocol_interactors(
            req.protocol_address, days=90, max_results=5000,
        )
    if not claimants:
        raise HTTPException(status_code=422, detail="no claimants resolvable for this protocol")

    sem = asyncio.Semaphore(10)
    scores: list[int] = []

    async def _score(addr: str):
        async with sem:
            try:
                cached = cache.get_cached_score(addr)
                if cached:
                    scores.append(cached["hps"])
                    return
                result = await asyncio.to_thread(scorer.score, addr, use_cache=True)
                if result and "hps" in result:
                    scores.append(result["hps"])
            except Exception as exc:
                logger.bind(component="airdrop_exposure").warning(f"score failed for {addr}: {exc}")

    await asyncio.gather(*(_score(a) for a in claimants[:5000]))

    if not scores:
        raise HTTPException(status_code=503, detail="insufficient_data: no claimants scorable")

    def _sensitivity(thr: int) -> ThresholdSensitivity:
        passing = [s for s in scores if s >= thr]
        return ThresholdSensitivity(
            passes=len(passing),
            human_pct=round(100 * len(passing) / len(scores), 1),
        )

    human_above = sum(1 for s in scores if s >= req.threshold)
    bot_exposure_pct = round(100 * (1 - human_above / len(scores)), 1)

    return AirdropExposureResponse(
        total_claimants=len(claimants),
        scored=len(scores),
        human_above_threshold=human_above,
        bot_exposure_pct=bot_exposure_pct,
        recommended_threshold=config.human_hps_threshold,
        threshold_sensitivity={
            "5000": _sensitivity(5000),
            "7000": _sensitivity(7000),
            "8000": _sensitivity(8000),
        },
        computed_at=int(time.time()),
    )
