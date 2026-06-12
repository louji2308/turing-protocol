import numpy as np
from typing import Dict, List, Tuple
from loguru import logger


def _sigmoid(x: float, center: float, width: float) -> float:
    """Smooth 0→100 transition centered at `center` over `width` range.
    Below center-width → 0, above center+width → 100."""
    x = (x - center) / (width / 6)
    return float(100.0 / (1.0 + np.exp(-x)))


def _linear_clip(x: float, x_min: float, x_max: float, y_min: float = 0.0, y_max: float = 100.0) -> float:
    """Linear interpolation from (x_min → y_min) to (x_max → y_max), clipped."""
    if x != x or x <= x_min:
        return y_min
    if x >= x_max:
        return y_max
    p = (x - x_min) / (x_max - x_min)
    return y_min + p * (y_max - y_min)


def _inverse_linear(x: float, x_min: float, x_max: float, y_min: float = 0.0, y_max: float = 100.0) -> float:
    """Like linear_clip but decreasing: (x_min → y_max) to (x_max → y_min)."""
    if x != x or x <= x_min:
        return y_max
    if x >= x_max:
        return y_min
    p = (x - x_min) / (x_max - x_min)
    return y_max - p * (y_max - y_min)


class DimensionScorer:
    """
    Scores a wallet across 12 behavioral dimensions (0-100 each).
    
    Human ≈ 70-100    |  Spam/Farming Bot ≈ 0-30
    Careful Bot ≈ 20-50 |  Uncertain/Mixed ≈ 40-60
    """

    # Dimension weight defaults (equal weight, can be tuned)
    # ip_fingerprint and cross_chain are set to 0 because they cannot
    # be determined from on-chain single-chain data. Including them as
    # neutral 50 would dilute the composite score with non-informative noise.
    WEIGHTS: Dict[str, float] = {
        "sleep_pattern":          1.0,
        "transaction_timing":     1.0,
        "gas_price":              1.0,
        "amount_entropy":         1.0,
        "revert_rate":            1.0,
        "wallet_age":             1.0,
        "funding_source":         1.0,
        "contract_diversity":     1.0,
        "news_reaction":          1.0,
        "ip_fingerprint":         0.0,
        "cross_chain":            0.0,
        "transaction_graph":      1.0,
    }

    def __init__(self, custom_weights: Dict[str, float] = None):
        if custom_weights:
            self.WEIGHTS.update(custom_weights)

    # =============================================================
    # DIMENSION 1: Sleep Pattern
    #   Human: timezone-clustered activity, irregular gaps
    #   Spam bot: 24/7 uniform, no gaps
    #   Careful bot: fake programmed gaps
    # =============================================================
    def _sleep_pattern(self, f: Dict[str, float]) -> float:
        hour_gini = f.get("temp_7_hour_gini", 0.0)
        cv = f.get("temp_4_cv", 0.0)

        # Hour gini: 0 = uniform (bot), 0.5+ = timezone-clustered (human)
        gini_score = _linear_clip(hour_gini, 0.05, 0.45, 10, 90)
        # CV: <0.3 = bot, >1.0 = human
        cv_score = _linear_clip(cv, 0.2, 1.2, 10, 90)

        return (gini_score * 0.6 + cv_score * 0.4)

    # =============================================================
    # DIMENSION 2: Transaction Timing
    #   Human: irregular, emotion-driven, CV > 1.0
    #   Spam bot: exact intervals, burst floods
    #   Careful bot: randomized but uniformly so
    # =============================================================
    def _transaction_timing(self, f: Dict[str, float]) -> float:
        cv = f.get("temp_4_cv", 0.0)
        fast_ratio = f.get("temp_5_fast_reaction_ratio", 0.0)
        autocorr = f.get("temp_6_autocorr", 0.0)
        burstiness = f.get("event_0_burstiness", 0.0)

        # CV: high = human
        cv_s = _linear_clip(cv, 0.2, 1.2, 5, 90)
        # Fast ratio: low = human (humans don't react in <2s always)
        fast_s = _inverse_linear(fast_ratio, 0.05, 0.6, 5, 90)
        # Autocorrelation: near 0 = human, high positive = cron bot
        auto_s = _inverse_linear(abs(autocorr), 0.05, 0.6, 10, 90)
        # Burstiness: positive = human (bursts), negative = regular intervals
        burst_s = _linear_clip(burstiness, -0.5, 0.5, 10, 90)

        return (cv_s * 0.35 + fast_s * 0.25 + auto_s * 0.20 + burst_s * 0.20)

    # =============================================================
    # DIMENSION 3: Gas Price
    #   Human: imperfect, emotionally varied, round numbers
    #   Spam bot: lowest possible or probe-and-revert
    #   Careful bot: network average, calibrated, no rounding
    # =============================================================
    def _gas_price(self, f: Dict[str, float]) -> float:
        price_cv = f.get("gas_0_price_cv", 0.0)
        round_frac = f.get("gas_1_round_fraction", 0.0)
        nice_frac = f.get("gas_2_nice_number_fraction", 0.0)
        overpay = f.get("gas_4_overpay_ratio", 0.0)

        # Price CV: high variability = human emotion
        cv_s = _linear_clip(price_cv, 0.02, 0.4, 5, 85)
        # Round fraction: humans round gas to nice values
        round_s = _linear_clip(round_frac, 0.05, 0.6, 5, 90)
        # Nice numbers (divisible by 5): human preference
        nice_s = _linear_clip(nice_frac, 0.05, 0.5, 5, 85)
        # Overpay ratio: humans occasionally overpay when urgent
        overpay_s = _linear_clip(overpay, 0.0, 0.15, 10, 80)

        return (cv_s * 0.30 + round_s * 0.30 + nice_s * 0.20 + overpay_s * 0.20)

    # =============================================================
    # DIMENSION 4: Amount Entropy
    #   Human: high variance, round amounts, real decisions
    #   Spam bot: very low variance, fixed or near-fixed
    #   Careful bot: artificially high (randomized)
    # =============================================================
    def _amount_entropy(self, f: Dict[str, float]) -> float:
        size_cv = f.get("port_0_size_cv", 0.0)
        size_skew = f.get("port_1_size_skew", 0.0)
        round_val = f.get("port_5_round_value_ratio", 0.0)
        max_mean = f.get("port_8_max_to_mean_ratio", 0.0)

        # Size CV: high = human variability
        cv_s = _linear_clip(size_cv, 0.1, 1.5, 5, 85)
        # Round value ratio: humans use round numbers
        round_s = _linear_clip(round_val, 0.05, 0.5, 5, 90)
        # Max-to-mean ratio: humans have impulse buys (outliers)
        max_s = _linear_clip(max_mean, 1.0, 10.0, 5, 80)
        # Size skew: positive = human (occasional large trades)
        skew_s = _linear_clip(size_skew, 0.0, 2.0, 10, 80)

        return (cv_s * 0.30 + round_s * 0.30 + max_s * 0.20 + skew_s * 0.20)

    # =============================================================
    # DIMENSION 5: Revert Rate
    #   Human: moderate 2-5% (real errors)
    #   Spam bot: extremely high >10% (probe transactions)
    #   Careful bot: low near 0% (simulates off-chain first)
    # =============================================================
    def _revert_rate(self, f: Dict[str, float]) -> float:
        fail_rate = f.get("consist_4_failure_rate", 0.0)

        if fail_rate < 0.005:
            return 20.0
        elif fail_rate < 0.01:
            return _linear_clip(fail_rate, 0.005, 0.01, 20, 55)
        elif fail_rate < 0.04:
            return _linear_clip(fail_rate, 0.01, 0.04, 55, 95)
        elif fail_rate < 0.07:
            return _linear_clip(fail_rate, 0.04, 0.07, 95, 85)
        elif fail_rate < 0.12:
            return _linear_clip(fail_rate, 0.07, 0.12, 85, 30)
        else:
            return max(5.0, 30.0 * np.exp(-3.5 * (fail_rate - 0.12)))

    # =============================================================
    # DIMENSION 6: Wallet Age
    #   Human: organic, deep history (months/years)
    #   Spam bot: freshly created, shallow
    #   Careful bot: aged deliberately in advance
    # =============================================================
    def _wallet_age(self, f: Dict[str, float]) -> float:
        age_log = f.get("net_3_wallet_age_blocks_log", 0.0)
        # Mantle Sepolia produces ~1 block/2s. 
        # 1 day ~ 43200 blocks, log ~ 10.7
        # 1 week ~ 302400 blocks, log ~ 12.6
        # 1 month ~ 1.3M blocks, log ~ 14.1
        score = _linear_clip(age_log, 8.0, 14.0, 5, 95)
        return score

    # =============================================================
    # DIMENSION 7: Funding Source
    #   Human: various, organic sources
    #   Spam bot: single donor wallet fan-out
    #   Careful bot: CEX withdrawals + intermediary layers
    # =============================================================
    def _funding_source(self, f: Dict[str, float]) -> float:
        unique_recip = f.get("net_0_unique_recipient_ratio", 0.0)
        top1 = f.get("net_1_top1_concentration", 0.0)
        contract_ratio = f.get("net_5_contract_ratio", 0.0)

        # High recipient diversity = human-like web
        recip_s = _linear_clip(unique_recip, 0.05, 0.4, 10, 85)
        # Low top-1 concentration = human (not just one donor)
        top1_s = _inverse_linear(top1, 0.3, 0.95, 5, 85)
        # Lower contract ratio = more EOA-to-EOA (human)
        contr_s = _inverse_linear(contract_ratio, 0.3, 0.95, 10, 80)

        return (recip_s * 0.35 + top1_s * 0.35 + contr_s * 0.30)

    # =============================================================
    # DIMENSION 8: Contract Diversity
    #   Human: interest-driven, thematic, 3+ protocols
    #   Spam bot: task-shaped only (1-2 protocols)
    #   Careful bot: padded with noise (artificial diversity)
    # =============================================================
    def _contract_diversity(self, f: Dict[str, float]) -> float:
        protocols = f.get("div_1_unique_protocols", 0.0)
        hhi = f.get("div_3_protocol_hhi", 1.0)
        exploration = f.get("div_4_exploration_ratio", 0.0)
        weekend = f.get("div_5_weekend_ratio", 0.0)

        # Protocol count: 1 = bot, 3+ = human
        prot_s = _linear_clip(protocols, 1.0, 4.0, 5, 90)
        # HHI: low = diverse (human), high = concentrated (bot)
        hhi_s = _inverse_linear(hhi, 0.3, 0.95, 5, 85)
        # Exploration ratio: exploring unknown contracts = human curiosity
        expl_s = _linear_clip(exploration, 0.0, 0.15, 10, 85)
        # Weekend ratio: humans trade less on weekends (but some do)
        week_s = _linear_clip(weekend, 0.05, 0.25, 20, 80)

        return (prot_s * 0.30 + hhi_s * 0.30 + expl_s * 0.20 + week_s * 0.20)

    # =============================================================
    # DIMENSION 9: Reaction to News
    #   Human: bursty, herding behavior, session-based
    #   Spam bot: none (script keeps running)
    #   Careful bot: programmed pauses for major triggers
    # =============================================================
    def _news_reaction(self, f: Dict[str, float]) -> float:
        burstiness = f.get("event_0_burstiness", 0.0)
        clustering = f.get("event_2_clustering", 0.0)
        session_txs = f.get("event_3_avg_session_txs", 0.0)
        session_gap_cv = f.get("event_4_session_gap_cv", 0.0)

        # Burstiness: positive = human (bursts of activity)
        burst_s = _linear_clip(burstiness, -0.3, 0.5, 10, 90)
        # Clustering: humans cluster txs in activity windows
        clust_s = _linear_clip(clustering, 0.05, 0.4, 10, 85)
        # Session txs: humans do 2-8 txs per session
        sess_s = _linear_clip(session_txs, 1.0, 5.0, 10, 85)
        # Session gap CV: irregular session timing = human
        gap_s = _linear_clip(session_gap_cv, 0.2, 1.0, 10, 80)

        return (burst_s * 0.30 + clust_s * 0.25 + sess_s * 0.25 + gap_s * 0.20)

    # =============================================================
    # DIMENSION 10: IP / Fingerprint
    #   Cannot determine from on-chain data alone.
    #   Neutral 50 — requires off-chain metadata.
    # =============================================================
    def _ip_fingerprint(self, f: Dict[str, float]) -> float:
        return 50.0

    # =============================================================
    # DIMENSION 11: Cross-Chain Patterns
    #   Cannot determine from single-chain data.
    #   Neutral 50 — requires multi-chain data sources.
    # =============================================================
    def _cross_chain(self, f: Dict[str, float]) -> float:
        return 50.0

    # =============================================================
    # DIMENSION 12: Transaction Graph
    #   Human: web-like, non-repeating, varied recipients
    #   Spam bot: star/chain patterns from single donor
    #   Careful bot: broken up with intermediaries
    # =============================================================
    def _transaction_graph(self, f: Dict[str, float]) -> float:
        unique_recip = f.get("net_0_unique_recipient_ratio", 0.0)
        top1 = f.get("net_1_top1_concentration", 1.0)
        top3 = f.get("net_2_top3_concentration", 1.0)
        contract_ratio = f.get("net_5_contract_ratio", 0.0)

        # Unique recipients: high = human web
        recip_s = _linear_clip(unique_recip, 0.05, 0.4, 5, 85)
        # Top-1 concentration: low = human
        top1_s = _inverse_linear(top1, 0.3, 0.95, 5, 85)
        # Top-3 concentration: low = human  
        top3_s = _inverse_linear(top3, 0.5, 0.98, 5, 80)
        # Contract ratio: high = bot (only calls contracts, no EOA sends)
        contr_s = _inverse_linear(contract_ratio, 0.3, 0.95, 5, 80)

        return (recip_s * 0.25 + top1_s * 0.25 + top3_s * 0.25 + contr_s * 0.25)

    # =============================================================
    # SCORE ALL DIMENSIONS
    # =============================================================
    def score_all(self, features: Dict[str, float]) -> Dict[str, float]:
        return {
            "sleep_pattern":          round(self._sleep_pattern(features), 1),
            "transaction_timing":     round(self._transaction_timing(features), 1),
            "gas_price":              round(self._gas_price(features), 1),
            "amount_entropy":         round(self._amount_entropy(features), 1),
            "revert_rate":            round(self._revert_rate(features), 1),
            "wallet_age":             round(self._wallet_age(features), 1),
            "funding_source":         round(self._funding_source(features), 1),
            "contract_diversity":     round(self._contract_diversity(features), 1),
            "news_reaction":          round(self._news_reaction(features), 1),
            "ip_fingerprint":         round(self._ip_fingerprint(features), 1),
            "cross_chain":            round(self._cross_chain(features), 1),
            "transaction_graph":      round(self._transaction_graph(features), 1),
        }

    @staticmethod
    def _wallet_age_boost(features: Dict[str, float], block_time: float = 12.0) -> float:
        """
        Returns a multiplier >1.0 for wallets older than 2 years.
        Boost grows with age: +5% per year after 2 years, capped at +30%.
        block_time: seconds per block (12 for Ethereum, 2 for Mantle Sepolia).
        """
        age_log = features.get("net_3_wallet_age_blocks_log", 0.0)
        if age_log <= 0:
            return 1.0
        age_blocks = np.expm1(age_log)
        age_days = age_blocks * block_time / 86400.0
        if age_days <= 730:
            return 1.0
        boost = 1.0 + (age_days - 730) / 365.0 * 0.05
        return min(boost, 1.30)

    def overall_score(self, features: Dict[str, float], block_time: float = 12.0) -> Tuple[float, Dict[str, float]]:
        dims = self.score_all(features)
        total_weight = sum(self.WEIGHTS.get(k, 1.0) for k in dims)
        weighted_sum = sum(dims[k] * self.WEIGHTS.get(k, 1.0) for k in dims)
        avg = weighted_sum / total_weight
        boost = self._wallet_age_boost(features, block_time)
        boosted = avg * boost
        return round(boosted, 1), dims


def hybrid_hps(
    ml_hps: int,
    features: Dict[str, float],
    dim_scorer: DimensionScorer = None,
    block_time: float = 12.0,
) -> Tuple[int, float, float, Dict[str, float]]:
    """
    Adaptive hybrid combining ML prediction with dimension-based scoring.
    
    Returns:
        (final_hps, ml_weight, dim_weight, dimension_scores)
    """
    if dim_scorer is None:
        dim_scorer = DimensionScorer()

    dim_avg, dim_scores = dim_scorer.overall_score(features, block_time)
    dim_hps = int(dim_avg * 100.0)

    # Fixed 70/30 blend: trust ML_HPS more than Dim_HPS
    # The ML model captures non-linear feature interactions; dimensions provide
    # interpretable guardrails but are conservative on thin histories.
    weight_ml = 0.7
    weight_dim = 0.3

    final = int(round(ml_hps * weight_ml + dim_hps * weight_dim))
    final = max(0, min(10000, final))

    return final, weight_ml, weight_dim, dim_scores
