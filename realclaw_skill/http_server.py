import os
import sys
import time
from typing import Optional

_project_root = os.path.dirname(os.path.dirname(__file__))
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from web3 import Web3
from loguru import logger

from .resolver import ScoreResolver, resolve_with_cold_start
from .decision import TrustDecision, resolve_tier
from .narrative import build_narrative


class CheckRequest(BaseModel):
    address: str
    threshold: Optional[int] = None
    tier: Optional[str] = None
    require_fresh_proof: bool = False
    explain: bool = False
    enrich: bool = False
    wait_for_score: bool = False


class HandshakeRequest(BaseModel):
    address_a: str
    address_b: str
    tier: str = "standard"
    threshold: Optional[int] = None


class SelfAuditRequest(BaseModel):
    addresses: list[str]


class ExplainRequest(BaseModel):
    address: str


app = FastAPI(
    title="Turing Trust Layer — RealClaw Skill HTTP API",
    version="1.0.0",
    description="Behavioural proof-of-humanity trust gate for Mantle wallets.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

resolver = ScoreResolver()


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/skill/manifest")
async def manifest():
    return {
        "name": "turing-trust",
        "version": "1.0.0",
        "description": "Behavioural proof-of-humanity trust gate for Mantle wallets.",
        "endpoints": {
            "check_wallet_trust": {
                "method": "POST",
                "path": "/skill/check_wallet_trust",
                "description": "Check whether a wallet address clears a trust threshold.",
            },
            "explain_wallet_trust": {
                "method": "POST",
                "path": "/skill/explain_wallet_trust",
                "description": "Get a plain-English explanation of a wallet's HPS score.",
            },
            "mutual_trust_handshake": {
                "method": "POST",
                "path": "/skill/mutual_trust_handshake",
                "description": "Mutual trust handshake between two wallets before a trade.",
            },
            "self_audit_fleet": {
                "method": "POST",
                "path": "/skill/self_audit_fleet",
                "description": "Audit a fleet of agent wallets for Sybil-cluster signatures.",
            },
        },
        "read_only": True,
        "custodial": False,
    }


@app.post("/skill/check_wallet_trust")
async def check_wallet_trust(req: CheckRequest):
    if not Web3.is_address(req.address):
        raise HTTPException(status_code=400, detail=f"Invalid address: {req.address}")

    try:
        thr = resolve_tier(req.threshold, req.tier)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        score_data = resolve_with_cold_start(resolver, req.address, wait=req.wait_for_score)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

    fresh_proof_status = None
    if req.require_fresh_proof:
        pob_addr = os.getenv("PROOF_OF_BEHAVIOR_ADDRESS")
        fresh_proof_status = resolver.resolve_with_fresh_proof(req.address, pob_addr)

    decision = TrustDecision(
        score_data,
        thr,
        require_fresh_proof=req.require_fresh_proof,
        fresh_proof_status=fresh_proof_status,
    ).evaluate()

    out = dict(decision)

    if req.explain:
        out["narrative"] = build_narrative(score_data, decision)

    if req.enrich:
        try:
            from .nansen_overlay import enrich_with_nansen
            out["nansen"] = enrich_with_nansen(req.address)
        except Exception as e:
            out["nansen"] = {"available": False, "reason": str(e)}

    return out


@app.post("/skill/explain_wallet_trust")
async def explain_wallet_trust(req: ExplainRequest):
    if not Web3.is_address(req.address):
        raise HTTPException(status_code=400, detail=f"Invalid address: {req.address}")

    try:
        score_data = resolver.resolve(req.address)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

    decision = TrustDecision(score_data, 0).evaluate()
    narrative = build_narrative(score_data, decision)

    return {
        "address": req.address,
        "hps": score_data.get("hps"),
        "narrative": narrative,
        "explanation": score_data.get("explanation"),
        "dimension_scores": score_data.get("dimension_scores"),
        "source": score_data.get("source"),
    }


@app.post("/skill/mutual_trust_handshake")
async def mutual_trust_handshake(req: HandshakeRequest):
    if not Web3.is_address(req.address_a):
        raise HTTPException(status_code=400, detail=f"Invalid address_a: {req.address_a}")
    if not Web3.is_address(req.address_b):
        raise HTTPException(status_code=400, detail=f"Invalid address_b: {req.address_b}")

    try:
        thr = resolve_tier(req.threshold, req.tier)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        a = resolver.resolve(req.address_a)
        b = resolver.resolve(req.address_b)
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

    hps_a = a.get("hps") or 0
    hps_b = b.get("hps") or 0
    deal_confidence = min(hps_a, hps_b)

    if deal_confidence >= thr:
        rec, frac, slip_delta = "proceed", 1.0, 0
    elif deal_confidence >= thr * 0.7:
        rec, frac, slip_delta = "proceed_with_caution", 0.5, 25
    else:
        rec, frac, slip_delta = "reject", 0.0, 0

    return {
        "address_a": req.address_a,
        "address_b": req.address_b,
        "hps_a": hps_a,
        "hps_b": hps_b,
        "deal_confidence": deal_confidence,
        "tier": req.tier,
        "threshold": thr,
        "recommendation": rec,
        "suggested_adjustments": {
            "max_trade_fraction_of_normal": frac,
            "slippage_tolerance_bps_delta": slip_delta,
        },
    }


@app.post("/skill/self_audit_fleet")
async def self_audit_fleet(req: SelfAuditRequest):
    if not req.addresses:
        raise HTTPException(status_code=400, detail="No addresses provided")

    scores: list[int] = []
    flagged: list[dict] = []
    funding_scores: list[int] = []

    for addr in req.addresses:
        if not Web3.is_address(addr):
            continue
        try:
            data = resolver.resolve(addr)
        except Exception:
            continue
        hps = data.get("hps") or 0
        scores.append(hps)
        dims = data.get("dimension_scores") or {}
        if isinstance(dims, dict):
            weak = [
                k
                for k, v in dims.items()
                if v is not None and v < 30
                and k not in ("ip_fingerprint", "cross_chain")
            ]
            fs = dims.get("funding_source")
            if fs is not None:
                funding_scores.append(fs)
        else:
            weak = []

        if hps < 5000 or weak:
            flagged.append({"address": addr, "hps": hps, "weak_dims": weak})

    mean_hps = round(sum(scores) / len(scores), 1) if scores else 0

    if funding_scores:
        mean_funding = sum(funding_scores) / len(funding_scores)
        if mean_funding < 30 and len(flagged) > len(req.addresses) / 3:
            cluster_risk = "high"
        elif mean_funding < 50 or len(flagged) > len(req.addresses) / 2:
            cluster_risk = "moderate"
        else:
            cluster_risk = "low"
    else:
        cluster_risk = "moderate" if flagged else "low"

    rec = (
        "Run NetworkTopologyModule-style EOA peer transfers and diversify "
        "funding sources for flagged wallets."
        if flagged
        else "Fleet looks behaviourally diverse."
    )

    return {
        "fleet_size": len(req.addresses),
        "mean_hps": mean_hps,
        "flagged_wallets": flagged,
        "cluster_risk": cluster_risk,
        "recommendation": rec,
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("TURING_TRUST_PORT", "8081"))
    uvicorn.run("realclaw_skill.http_server:app", host="0.0.0.0", port=port, log_level="info")
