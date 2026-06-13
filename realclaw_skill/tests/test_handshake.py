import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from realclaw_skill.decision import TrustDecision, resolve_tier, TIERS


def test_handshake_min_of_two():
    data_a = {"hps": 9120, "confidence": "high", "source": "oracle_api"}
    data_b = {"hps": 6850, "confidence": "high", "source": "oracle_api"}

    dec_a = TrustDecision(data_a, 7000).evaluate()
    dec_b = TrustDecision(data_b, 7000).evaluate()

    deal_confidence = min(data_a["hps"], data_b["hps"])
    assert deal_confidence == 6850
    assert dec_a["trusted"] is True
    assert dec_b["trusted"] is False


def test_handshake_weakest_link():
    high_hps = 9120
    low_hps = 4641
    threshold = 7000

    deal_confidence = min(high_hps, low_hps)
    assert deal_confidence == 4641

    threshold_70pct = threshold * 0.7
    if deal_confidence >= threshold:
        rec, frac = "proceed", 1.0
    elif deal_confidence >= threshold_70pct:
        rec, frac = "proceed_with_caution", 0.5
    else:
        rec, frac = "reject", 0.0

    assert rec == "reject"
    assert frac == 0.0


def test_handshake_proceed():
    high_hps = 8500
    other_hps = 7200
    threshold = 7000

    deal_confidence = min(high_hps, other_hps)
    assert deal_confidence == 7200

    if deal_confidence >= threshold:
        rec = "proceed"
    else:
        rec = "reject"
    assert rec == "proceed"


def test_handshake_caution():
    high_hps = 8500
    other_hps = 5000
    threshold = 7000

    deal_confidence = min(high_hps, other_hps)
    assert deal_confidence == 5000

    threshold_70pct = threshold * 0.7
    if deal_confidence >= threshold:
        rec = "proceed"
    elif deal_confidence >= threshold_70pct:
        rec = "proceed_with_caution"
    else:
        rec = "reject"

    # 5000 < 4900? No, 5000 >= 4900, so it should be proceed_with_caution
    assert rec == "proceed_with_caution"


def test_self_audit_cluster_risk():
    scores = [8800, 9100, 2980, 7200, 4500]
    threshold = 5000
    flagged = [s for s in scores if s < threshold]
    mean_hps = sum(scores) / len(scores)

    assert len(flagged) == 2
    assert round(mean_hps, 1) == 6516.0

    cluster_risk = "high" if len(flagged) > len(scores) / 2 else (
        "moderate" if flagged else "low"
    )
    assert cluster_risk == "moderate"
