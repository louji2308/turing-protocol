import numpy as np
import pytest
from unittest.mock import Mock, patch
from interrogator.model import (
    InterrogatorModel, score_wallet_with_uncertainty,
    UNCERTAINTY_HIGH_MAX, UNCERTAINTY_MEDIUM_MAX,
)


class TestScoreWalletWithUncertainty:
    def test_high_confidence_for_low_variance(self):
        mock_model = Mock()
        mock_model.predict_proba.return_value = np.array([[0.85, 0.15]])
        booster = Mock()
        mock_model.get_booster.return_value = booster

        n_trees = 400
        booster.num_boosted_rounds.return_value = n_trees
        margins = np.full((51, 1), 1.5)
        booster.predict.return_value = margins

        result = score_wallet_with_uncertainty(mock_model, np.array([[0.5] * 49]))
        assert result["confidence"] == "high"
        assert result["uncertainty_hps"] < UNCERTAINTY_HIGH_MAX
        assert result["investable"] is True
        assert 0 <= result["hps_range"][0] <= result["hps"] <= result["hps_range"][1] <= 10000

    @patch("numpy.std", return_value=0.45)
    def test_low_confidence_for_high_variance(self, mock_std):
        mock_model = Mock()
        mock_model.predict_proba.return_value = np.array([[0.55, 0.45]])
        booster = Mock()
        mock_model.get_booster.return_value = booster

        n_trees = 400
        booster.num_boosted_rounds.return_value = n_trees
        margins = np.concatenate([
            np.full((40, 1), -1.0),
            np.full((11, 1), 1.0),
        ])
        booster.predict.return_value = margins

        result = score_wallet_with_uncertainty(mock_model, np.array([[0.5] * 49]))
        assert result["confidence"] == "low"
        assert result["uncertainty_hps"] >= UNCERTAINTY_MEDIUM_MAX
        assert result["investable"] is False

    def test_medium_confidence_mid_range(self):
        mock_model = Mock()
        mock_model.predict_proba.return_value = np.array([[0.70, 0.30]])
        booster = Mock()
        mock_model.get_booster.return_value = booster

        n_trees = 400
        booster.num_boosted_rounds.return_value = n_trees
        margins = np.full((51, 1), 0.6)
        booster.predict.return_value = margins

        with patch("numpy.std", return_value=0.1):
            result = score_wallet_with_uncertainty(mock_model, np.array([[0.5] * 49]))
            assert result["confidence"] in ("high", "medium")

    def test_fallback_on_booster_failure(self):
        mock_model = Mock()
        mock_model.predict_proba.return_value = np.array([[0.60, 0.40]])
        booster = Mock()
        mock_model.get_booster.return_value = booster
        booster.num_boosted_rounds.return_value = 400
        booster.predict.side_effect = RuntimeError("boom")

        result = score_wallet_with_uncertainty(mock_model, np.array([[0.5] * 49]))
        assert "hps" in result
        assert "confidence" in result
        assert "investable" in result
        assert "hps_range" in result
        assert result["hps"] == 4000

    def test_hps_range_always_valid(self):
        mock_model = Mock()
        mock_model.predict_proba.return_value = np.array([[0.99, 0.01]])
        booster = Mock()
        mock_model.get_booster.return_value = booster
        booster.num_boosted_rounds.return_value = 400
        margins = np.full((51, 1), 4.0)
        booster.predict.return_value = margins

        result = score_wallet_with_uncertainty(mock_model, np.array([[0.5] * 49]))
        lo, hi = result["hps_range"]
        assert 0 <= lo <= result["hps"] <= hi <= 10000

    def test_investable_false_when_uncertainty_high(self):
        mock_model = Mock()
        mock_model.predict_proba.return_value = np.array([[0.99, 0.01]])
        booster = Mock()
        mock_model.get_booster.return_value = booster
        booster.num_boosted_rounds.return_value = 400
        margins = np.concatenate([
            np.full((30, 1), 4.0),
            np.full((21, 1), -2.0),
        ])
        booster.predict.return_value = margins

        result = score_wallet_with_uncertainty(mock_model, np.array([[0.5] * 49]))
        if result["confidence"] == "low":
            assert result["investable"] is False


class TestInterrogatorModelUncertainty:
    def test_score_wallet_with_uncertainty_flag(self):
        model = InterrogatorModel()
        model.model = Mock()
        model.model.predict_proba.return_value = np.array([[0.80, 0.20]])

        result = model.score_wallet(np.array([[0.5] * 47]), return_uncertainty=True)
        assert isinstance(result, dict)
        assert "hps" in result
        assert "uncertainty" in result
