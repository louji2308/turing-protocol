import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from realclaw_skill.narrative import build_narrative, FEATURE_DESCRIPTIONS, DIMENSION_DESCRIPTIONS


def test_narrative_proceed():
    score_data = {
        "hps": 8701,
        "confidence": "high",
        "uncertainty": 412,
    }
    decision = {
        "recommendation": "proceed",
        "trusted": True,
    }
    text = build_narrative(score_data, decision)
    assert "8701" in text
    assert "Human Probability Score" in text
    assert "trust threshold" in text


def test_narrative_reject():
    score_data = {
        "hps": 3000,
        "confidence": "high",
    }
    decision = {
        "recommendation": "reject",
        "trusted": False,
    }
    text = build_narrative(score_data, decision)
    assert "3000" in text
    assert "falls below" in text


def test_narrative_insufficient_data():
    score_data = {
        "hps": None,
    }
    decision = {
        "recommendation": "insufficient_data",
        "trusted": False,
    }
    text = build_narrative(score_data, decision)
    assert "No behavioural score" in text or "unverified" in text


def test_narrative_caution():
    score_data = {
        "hps": 7500,
        "confidence": "low",
        "uncertainty": 1800,
    }
    decision = {
        "recommendation": "proceed_with_caution",
        "trusted": True,
    }
    text = build_narrative(score_data, decision)
    assert "caution" in text.lower() or "smaller trade" in text


def test_narrative_with_explanation():
    score_data = {
        "hps": 8701,
        "confidence": "high",
        "explanation": [
            {"feature": "temp_4_cv", "shap": 0.45},
            {"feature": "temp_7_hour_gini", "shap": 0.32},
            {"feature": "gas_0_price_cv", "shap": 0.28},
        ],
    }
    decision = {
        "recommendation": "proceed",
        "trusted": True,
    }
    text = build_narrative(score_data, decision)
    assert "irregular transaction timing" in text or "Key signals" in text


def test_narrative_with_dimensions():
    score_data = {
        "hps": 8701,
        "confidence": "high",
        "dimension_scores": {
            "sleep": 90,
            "timing": 85,
            "gas_price": 45,
            "revert_rate": 20,
            "funding_source": 75,
            "transaction_graph": 80,
        },
    }
    decision = {
        "recommendation": "proceed",
        "trusted": True,
    }
    text = build_narrative(score_data, decision)
    assert "Weakest areas" in text
    assert "revert_rate" in text or "transaction failure rate" in text


def test_narrative_handles_missing_fields():
    score_data = {
        "hps": 8701,
        "confidence": "high",
    }
    decision = {
        "recommendation": "proceed",
        "trusted": True,
    }
    text = build_narrative(score_data, decision)
    assert "8701" in text
    assert isinstance(text, str)


def test_feature_descriptions_populated():
    assert len(FEATURE_DESCRIPTIONS) > 20


def test_dimension_descriptions_populated():
    assert len(DIMENSION_DESCRIPTIONS) >= 10
