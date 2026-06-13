FEATURE_DESCRIPTIONS = {
    "temp_4_cv": "irregular transaction timing (a strong human signal)",
    "temp_7_hour_gini": "activity concentrated in specific hours of the day",
    "consist_4_failure_rate": "a non-zero transaction failure rate",
    "gas_0_price_cv": "variable gas price selection",
    "div_3_protocol_hhi": "diversity across multiple protocols",
    "temp_5_fast_reaction_ratio": "fast, sub-2-second reactions (a bot signal when high)",
    "port_0_size_cv": "varied trade sizes",
    "gas_1_round_fraction": "round-number gas prices (a human psychological signal)",
    "gas_2_nice_number_fraction": "nice-number gas prices divisible by 5",
    "gas_4_overpay_ratio": "occasional gas overpayment (emotional urgency)",
    "port_3_overconfidence_score": "increasing position sizes after winning streaks",
    "port_5_round_value_ratio": "round-number trade amounts",
    "port_8_max_to_mean_ratio": "occasional outlier trade sizes (impulse)",
    "event_0_burstiness": "bursty activity pattern (human-like trading sessions)",
    "event_2_clustering": "transactions clustering in short activity windows",
    "event_3_avg_session_txs": "session-based trading pattern",
    "net_0_unique_recipient_ratio": "diverse counterparty interactions",
    "net_1_top1_concentration": "concentration on a single counterparty (bot signal when high)",
    "net_5_contract_ratio": "interaction ratio with contracts vs EOAs",
    "consist_0_stress_variance_ratio": "behaviour changing under market stress",
    "consist_5_method_evolution": "evolving function call patterns over time",
    "div_0_unique_contract_ratio": "unique contract interaction ratio",
    "div_1_unique_protocols": "number of unique protocols used",
    "div_4_exploration_ratio": "exploration of new/unseen contracts",
    "div_5_weekend_ratio": "weekend activity ratio",
    "port_6_lognormal_fit": "log-normal position size distribution (human trading)",
    "port_7_activity_consistency": "natural variability in activity levels",
    "temp_3_kurtosis": "temporal distribution shape",
    "temp_6_autocorr": "temporal autocorrelation (bot signal when high)",
    "gas_3_percentile_variance": "gas price percentile variance",
    "gas_5_mean_efficiency": "gas efficiency pattern",
    "gas_6_efficiency_std": "gas efficiency variability",
    "net_2_top3_concentration": "top-3 counterparty concentration",
    "net_3_wallet_age_blocks_log": "wallet age in blocks",
    "net_4_total_volume_log": "total transaction volume",
    "consist_1_timing_early_cv": "early-period timing variability",
    "consist_2_timing_late_cv": "late-period timing variability",
    "consist_3_cv_evolution": "timing consistency evolution over time",
    "temp_0_log_mean_delta": "average inter-transaction time",
    "temp_1_log_std_delta": "inter-transaction time variability",
    "temp_2_skewness": "temporal distribution skew",
    "event_1_memory": "temporal memory between transactions",
    "event_4_session_gap_cv": "session gap variability",
    "port_1_size_skew": "trade size distribution skew",
    "port_2_size_kurtosis": "trade size distribution kurtosis",
    "port_4_streak_size_correlation": "streak-size correlation",
    "div_2_method_diversity": "function selector diversity",
}

DIMENSION_DESCRIPTIONS = {
    "sleep": "timezone-consistent activity pattern",
    "timing": "inter-transaction timing irregularity",
    "gas_price": "gas price psychology",
    "amount_entropy": "position sizing psychology",
    "revert_rate": "transaction failure rate",
    "wallet_age": "account age and history depth",
    "funding_source": "diversity of funding origins",
    "contract_diversity": "protocol exploration breadth",
    "news_reaction": "news-driven trading bursts",
    "transaction_graph": "counterparty network topology",
    "ip_fingerprint": "IP/fingerprint signal (neutral, weighted 0)",
    "cross_chain": "cross-chain activity (neutral, weighted 0)",
}


def build_narrative(score_data: dict, decision: dict) -> str:
    hps = score_data.get("hps")
    if hps is None:
        return "No behavioural score is available for this wallet — treat as unverified."

    lines = [f"This wallet has a Human Probability Score of {hps}/10000."]

    rec = decision.get("recommendation", "insufficient_data")
    if rec == "proceed":
        lines.append("It clears the requested trust threshold with high confidence.")
    elif rec == "proceed_with_caution":
        uncertainty = score_data.get("uncertainty")
        parts = [
            "It clears the threshold, but the model's confidence is low",
        ]
        if uncertainty is not None:
            parts.append(f"(uncertainty: {uncertainty})")
        parts.append(". Consider smaller trade sizes.")
        lines.append(" ".join(parts))
    elif rec == "reject":
        lines.append("It falls below the requested trust threshold.")
    else:
        lines.append("There is not enough data to make a confident trust decision.")

    explanation = score_data.get("explanation") or score_data.get("details")
    if explanation:
        if isinstance(explanation, list):
            top = sorted(
                explanation,
                key=lambda x: (
                    abs(x.get("shap", x.get("value", 0)))
                    if isinstance(x, dict)
                    else 0
                ),
                reverse=True,
            )[:3]
            descs = []
            for f in top:
                feat_name = (
                    f.get("feature", f.get("name", str(f)))
                    if isinstance(f, dict)
                    else str(f)
                )
                desc = FEATURE_DESCRIPTIONS.get(feat_name, feat_name)
                descs.append(desc)
            if descs:
                lines.append("Key signals: " + "; ".join(descs) + ".")

    dims = score_data.get("dimension_scores") or {}
    if isinstance(dims, dict) and dims:
        scored_dims = [
            (k, v)
            for k, v in dims.items()
            if k not in ("ip_fingerprint", "cross_chain")
            and v is not None
        ]
        weakest = sorted(scored_dims, key=lambda kv: kv[1])[:2]
        if weakest:
            weak_descs = [
                f"{DIMENSION_DESCRIPTIONS.get(k, k)} ({v}/100)" for k, v in weakest
            ]
            lines.append("Weakest areas: " + ", ".join(weak_descs) + ".")

    return " ".join(lines)
