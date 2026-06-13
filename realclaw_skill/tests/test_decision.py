import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from realclaw_skill.decision import TrustDecision, resolve_tier, TIERS


def test_tier_lenient():
    assert TIERS["lenient"] == 3000


def test_tier_standard():
    assert TIERS["standard"] == 7000


def test_tier_strict():
    assert TIERS["strict"] == 8000


def test_resolve_tier_both_none():
    assert resolve_tier(None, None) == 7000


def test_resolve_tier_conflicting_same_value():
    assert resolve_tier(8000, "strict") == 8000


def test_trust_decision_high_uncertainty_caution():
    data = {
        "hps": 8500,
        "confidence": "high",
        "source": "oracle_api",
        "uncertainty": 2000,
    }
    decision = TrustDecision(data, 7000).evaluate()
    assert decision["recommendation"] == "proceed_with_caution"


def test_trust_decision_edge_threshold():
    data = {
        "hps": 7000,
        "confidence": "high",
        "source": "oracle_api",
    }
    decision = TrustDecision(data, 7000).evaluate()
    assert decision["trusted"] is True
    assert decision["recommendation"] == "proceed"


def test_trust_decision_below_threshold():
    data = {
        "hps": 6999,
        "confidence": "high",
        "source": "oracle_api",
    }
    decision = TrustDecision(data, 7000).evaluate()
    assert decision["trusted"] is False
    assert decision["recommendation"] == "reject"


def test_trust_decision_none_hps():
    data = {
        "hps": None,
        "confidence": "unknown",
        "source": "onchain_unscored",
    }
    decision = TrustDecision(data, 7000).evaluate()
    assert decision["trusted"] is False
    assert decision["recommendation"] == "insufficient_data"


def test_trust_decision_error_source():
    data = {
        "hps": 0,
        "confidence": "unknown",
        "source": "error",
        "error": "RPC failed",
    }
    decision = TrustDecision(data, 7000).evaluate()
    assert decision["trusted"] is False
    assert decision["recommendation"] == "insufficient_data"
    # error key should not be in output
    assert "error" not in decision
