import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from realclaw_skill.resolver import ScoreResolver, _cache, resolve_with_cold_start
from realclaw_skill.decision import TrustDecision, resolve_tier, TIERS


SAMPLE_ADDR = "0xE0E216283eef00895b6ABAa73848448596B85724"
REAL_ADDR = "0xE0E216283eef00895b6ABAa73848448596B85724"


def test_resolve_tier_standard_default():
    assert resolve_tier(None, None) == TIERS["standard"]


def test_resolve_tier_custom_threshold():
    assert resolve_tier(5000, None) == 5000


def test_resolve_tier_named_tier():
    assert resolve_tier(None, "strict") == TIERS["strict"]


def test_resolve_tier_unknown_tier_raises():
    try:
        resolve_tier(None, "bogus")
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_resolve_tier_conflicting_raises():
    try:
        resolve_tier(5000, "strict")
        assert False, "Expected ValueError"
    except ValueError:
        pass


def test_trust_decision_trusted():
    data = {
        "hps": 8500,
        "confidence": "high",
        "source": "oracle_api",
        "uncertainty": 300,
    }
    decision = TrustDecision(data, 7000).evaluate()
    assert decision["trusted"] is True
    assert decision["recommendation"] == "proceed"


def test_trust_decision_rejected():
    data = {
        "hps": 3000,
        "confidence": "high",
        "source": "oracle_api",
    }
    decision = TrustDecision(data, 7000).evaluate()
    assert decision["trusted"] is False
    assert decision["recommendation"] == "reject"


def test_trust_decision_low_confidence_caution():
    data = {
        "hps": 7500,
        "confidence": "low",
        "source": "oracle_api",
        "uncertainty": 2000,
    }
    decision = TrustDecision(data, 7000).evaluate()
    assert decision["trusted"] is True
    assert decision["recommendation"] == "proceed_with_caution"


def test_trust_decision_insufficient_data():
    data = {
        "hps": None,
        "confidence": "unknown",
        "source": "error",
    }
    decision = TrustDecision(data, 7000).evaluate()
    assert decision["trusted"] is False
    assert decision["recommendation"] == "insufficient_data"


def test_trust_decision_low_confidence_untrusted():
    data = {
        "hps": 3000,
        "confidence": "low",
        "source": "oracle_api",
    }
    decision = TrustDecision(data, 7000).evaluate()
    assert decision["trusted"] is False
    assert decision["recommendation"] == "insufficient_data"


def test_trust_decision_require_fresh_proof():
    data = {
        "hps": 8500,
        "confidence": "high",
        "source": "oracle_api",
    }
    decision = TrustDecision(data, 7000, require_fresh_proof=True, fresh_proof_status=False).evaluate()
    assert decision["trusted"] is False
    assert decision["recommendation"] == "reject"


def test_trust_decision_fresh_proof_allows():
    data = {
        "hps": 8500,
        "confidence": "high",
        "source": "oracle_api",
    }
    decision = TrustDecision(data, 7000, require_fresh_proof=True, fresh_proof_status=True).evaluate()
    assert decision["trusted"] is True
    assert decision["recommendation"] == "proceed"


@patch("realclaw_skill.resolver.httpx.get")
def test_resolve_cold_start_fallback(mock_get):
    data = {
        "address": REAL_ADDR,
        "hps": None,
        "confidence": "unknown",
        "source": "onchain_unscored",
    }
    _cache.clear()
    resolver = ScoreResolver()

    resolved = resolve_with_cold_start(resolver, REAL_ADDR, wait=False)
    # without wait, should just return whatever resolve gives
    assert isinstance(resolved, dict)
    _cache.clear()
