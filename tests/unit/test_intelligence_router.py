import pytest
from unittest.mock import AsyncMock, Mock, patch
from fastapi import HTTPException
from oracle_service.intelligence_router import (
    router, list_protocols, protocol_health, smart_money_flows,
    emerging_protocols, airdrop_exposure, ProtocolHumanness,
    SmartMoneyFlowsResponse, EmergingProtocol, AirdropExposureRequest,
)


def _mock_cache(protocols=None):
    cache = Mock()
    cache.get_latest_protocol_health.return_value = protocols or []
    cache.get_protocol_health_history.return_value = []
    cache.compute_trend.return_value = None
    cache.get_latest_smart_money_flows.return_value = []
    cache.get_wallets_above_threshold.return_value = []
    cache.get_emerging_protocols.return_value = []
    cache.get_cached_score.return_value = None
    return cache


class TestListProtocols:
    async def test_empty_cache_raises_503(self):
        cache = _mock_cache(protocols=None)
        cache.get_latest_protocol_health.return_value = None
        with pytest.raises(HTTPException) as exc:
            await list_protocols(cache=cache)
        assert exc.value.status_code == 503
        assert "insufficient_data" in exc.value.detail

    async def test_partial_data_returns_one_protocol(self):
        cache = _mock_cache(protocols=[
            {
                "protocol_address": "0xabc", "protocol_name": "TestProto",
                "wallets_sampled": 50, "human_ratio": 0.75, "avg_hps": 7500,
                "median_hps": 7800, "hps_p25": 6500, "hps_p75": 8500,
                "bot_heavy_count": 5, "genuine_human_count": 30, "computed_at": 1000,
            }
        ])
        result = await list_protocols(cache=cache)
        assert len(result) == 1
        assert result[0].protocol == "TestProto"
        assert result[0].human_ratio == 0.75

    async def test_happy_path_sorted_by_human_ratio(self):
        cache = _mock_cache(protocols=[
            {
                "protocol_address": "0xlow", "protocol_name": "Low",
                "wallets_sampled": 50, "human_ratio": 0.30, "avg_hps": 3000,
                "median_hps": 3000, "hps_p25": 2000, "hps_p75": 4000,
                "bot_heavy_count": 20, "genuine_human_count": 10, "computed_at": 1000,
            },
            {
                "protocol_address": "0xhigh", "protocol_name": "High",
                "wallets_sampled": 50, "human_ratio": 0.90, "avg_hps": 9000,
                "median_hps": 9200, "hps_p25": 8000, "hps_p75": 9800,
                "bot_heavy_count": 1, "genuine_human_count": 45, "computed_at": 1000,
            },
        ])
        result = await list_protocols(cache=cache)
        assert len(result) == 2
        assert result[0].protocol == "High"
        assert result[1].protocol == "Low"


class TestSmartMoneyFlows:
    async def test_empty_flows_raises_503(self):
        cache = _mock_cache()
        with pytest.raises(HTTPException) as exc:
            await smart_money_flows(cache=cache)
        assert exc.value.status_code == 503

    async def test_populated_flows_returns_response(self):
        cache = _mock_cache()
        cache.get_latest_smart_money_flows.return_value = [
            {
                "protocol_address": "0xabc", "protocol_name": "Agni",
                "period_days": 14, "inflow_mnt": 100.0, "outflow_mnt": 30.0,
                "unique_smart_wallets": 10, "net_flow_mnt": 70.0, "computed_at": 1000,
            }
        ]
        cache.get_wallets_above_threshold.return_value = ["0xw1", "0xw2"]
        result = await smart_money_flows(days=14, cache=cache)
        assert isinstance(result, SmartMoneyFlowsResponse)
        assert result.period_days == 14


class TestEmergingProtocols:
    async def test_empty_returns_empty_list(self):
        cache = _mock_cache()
        result = await emerging_protocols(cache=cache)
        assert result == []

    async def test_growth_data_returns_emerging_protocols(self):
        cache = _mock_cache()
        cache.get_emerging_protocols.return_value = [
            {
                "protocol_address": "0xabc", "protocol_name": "Rising",
                "lookback_days": 7, "recent_human_count": 50,
                "prior_human_count": 20, "human_growth_pct": 150.0,
                "signal": "organic_traction", "computed_at": 1000,
            }
        ]
        result = await emerging_protocols(days=7, cache=cache)
        assert len(result) == 1
        assert result[0].signal == "organic_traction"


class TestAirdropExposure:
    async def test_empty_claimants_returns_422(self):
        cache = _mock_cache()
        fetcher = Mock()
        fetcher.fetch_protocol_interactors = AsyncMock(return_value=[])
        scorer = Mock()
        req = AirdropExposureRequest(protocol_address="0xabc", claimant_addresses=[])
        with pytest.raises(HTTPException) as exc:
            await airdrop_exposure(req, cache=cache, fetcher=fetcher, scorer=scorer)
        assert exc.value.status_code == 422
