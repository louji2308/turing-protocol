from __future__ import annotations

import asyncio
import json
import time

from fastapi import APIRouter, HTTPException, Depends, Query
from loguru import logger
from pydantic import BaseModel

from oracle_service.config import OracleConfig
from oracle_service.score_cache import ScoreCache, get_cache
from interrogator.sybil_detector import SybilClusterDetector

router = APIRouter(prefix="/api/v1/intelligence", tags=["sybil"])

config = OracleConfig()


class ClusterMember(BaseModel):
    address: str
    hps: int


class ClusterSummary(BaseModel):
    cluster_id: str
    size: int
    avg_hps: int
    sybil_probability: float
    coordinator: str | None
    risk_level: str


class ClusterDetail(ClusterSummary):
    members: list[ClusterMember]
    shap_comparison: dict | None = None


@router.get("/sybil-clusters", response_model=list[ClusterSummary],
            summary="All detected Sybil clusters, filterable by size/risk")
async def list_clusters(
    min_size: int = Query(3, ge=1),
    risk_level: str | None = None,
    cache: ScoreCache = Depends(get_cache),
):
    clusters = cache.get_sybil_clusters(min_size=min_size, risk_level=risk_level)
    return [ClusterSummary(**c) for c in clusters]


@router.get("/sybil-clusters/{cluster_id}", response_model=ClusterDetail,
            summary="Cluster deep-dive: members, coordinator, SHAP comparison")
async def cluster_detail(cluster_id: str, cache: ScoreCache = Depends(get_cache)):
    detail = cache.get_sybil_cluster(cluster_id)
    if not detail:
        raise HTTPException(status_code=404, detail="cluster not found")
    members = [ClusterMember(address=m["address"], hps=m.get("hps", 0))
               for m in detail.get("members", [])]
    return ClusterDetail(
        cluster_id=detail["cluster_id"],
        size=detail["size"],
        avg_hps=detail["avg_hps"],
        sybil_probability=detail["sybil_probability"],
        coordinator=detail.get("coordinator"),
        risk_level=detail["risk_level"],
        members=members,
    )


@router.get("/sybil-clusters/address/{wallet}",
            summary="Is this wallet part of a known Sybil cluster?")
async def wallet_cluster_membership(wallet: str, cache: ScoreCache = Depends(get_cache)):
    cluster_id = cache.get_wallet_cluster_id(wallet)
    if not cluster_id:
        return {"wallet": wallet, "in_cluster": False}
    detail = cache.get_sybil_cluster(cluster_id)
    return {
        "wallet": wallet,
        "in_cluster": True,
        "cluster_id": cluster_id,
        "sybil_probability": detail["sybil_probability"],
        "risk_level": detail["risk_level"],
    }
