import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')


class BehavioralFeatureEngineer:

    ENTRY_POINT_ADDRESSES = {
        "0x5FF137D4b0FDCD49DcA30c7CF57E578a026d2789",
        "0x0000000071727De22E5E9d8BAf0edAc6f37da032",
        "0x000000000000aDdB49795b0f9bA5BC2986f0f5c0",
    }

    AGNI_POOL_FACTORY = "0x25780dc8Fc3cfBD75F33bFDAB65e969b603b2035"
    MERCHANT_MOE_ROUTER = "0xeaEE7EE68874218c3558b40063c42B82D3E7232a"
    SWAP_EVENT_SIG = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
    STAKING_CONTRACT = "0xe6829d9a7eE3040e1276Fa75293Bde931859e8fA"

    """
    Transforms raw transaction DataFrames into 49-dimensional
    behavioral feature vectors for the Interrogator classifier.

    Feature Classes:
    1. Temporal Irregularity (8 features)
    2. Gas Behavior (7 features)
    3. Interaction Diversity (6 features)
    4. Portfolio Behavior (9 features)
    5. Temporal Correlation to Events (5 features)
    6. Behavioral Consistency (6 features)
    7. Network Graph (6 features)
    8. Mantle Native (2 features): staking duration, bridge CV

    Total: 49 features
    """

    def __init__(self):
        self._fetcher = None

    def set_fetcher(self, fetcher):
        self._fetcher = fetcher

    def _is_aa_wallet(self, df: pd.DataFrame) -> bool:
        entry_point_calls = df[df["to_addr"].isin(self.ENTRY_POINT_ADDRESSES)]
        return len(entry_point_calls) > len(df) * 0.3

    def _adjust_gas_for_aa(self, features: Dict[str, float], is_aa: bool) -> Dict[str, float]:
        if is_aa:
            features["gas_5_mean_efficiency"] = 0.5
            features["gas_6_efficiency_std"] = 0.1
        return features

    def compute_all_features(
        self,
        df: pd.DataFrame,
        wallet_address: str,
        include_mantle_native: bool = False
    ) -> Dict[str, float]:
        """
        Master function. Takes a transaction DataFrame and returns
        a complete 47-feature dictionary (or 49 with mantle-native features).

        This is what the Interrogator model calls for each wallet.
        """
        if len(df) < 10:
            raise ValueError(
                f"Insufficient transaction history: {len(df)} txs. "
                f"Need at least 10."
            )

        # Only use transactions where this wallet is the sender
        sender_df = df[df["is_sender"] == True].copy()

        if len(sender_df) < 5:
            raise ValueError("Wallet has fewer than 5 outgoing transactions.")

        is_aa = self._is_aa_wallet(df)

        features = {}

        # Compute each feature class
        features.update(self._temporal_irregularity_features(sender_df))
        features.update(self._gas_behavior_features(sender_df))
        features.update(self._interaction_diversity_features(df))
        features.update(self._portfolio_behavior_features(sender_df))
        features.update(self._temporal_correlation_features(sender_df))
        features.update(self._behavioral_consistency_features(sender_df))
        features.update(self._network_features(df, wallet_address))

        features = self._adjust_gas_for_aa(features, is_aa)

        # Append Mantle-native features (48-49) with safe defaults
        features["mantle_48_staking_duration_days"] = 0.0
        features["mantle_49_bridge_cv"] = 0.0

        expected = 49
        assert len(features) == expected, (
            f"Expected {expected} features, got {len(features)}. "
            f"Something is missing."
        )

        return features

    async def compute_mantle_staking_features(self, wallet: str) -> dict:
        if self._fetcher is None:
            return {"mantle_48_staking_duration_days": 0.0, "mantle_49_bridge_cv": 0.0}
        stake_events = await self._fetcher.fetch_staking_events(wallet)
        bridge_events = await self._fetcher.fetch_bridge_events(wallet)
        import time
        if stake_events:
            first_stake_ts = min(e["timestamp"] for e in stake_events)
            days = (time.time() - first_stake_ts) / 86400
            staking_duration = float(np.log1p(max(days, 0)))
        else:
            staking_duration = 0.0
        if len(bridge_events) >= 2:
            amounts = [float(e["amount"]) for e in bridge_events]
            bridge_cv = float(np.std(amounts) / max(np.mean(amounts), 1e-9))
        else:
            bridge_cv = 0.0
        return {
            "mantle_48_staking_duration_days": round(staking_duration, 4),
            "mantle_49_bridge_cv": round(bridge_cv, 4),
        }

    async def compute_dex_behavior_features(self, wallet: str) -> dict:
        if self._fetcher is None:
            return {
                "dex_swap_count": 0, "dex_slippage_cv": 0.0,
                "dex_pairs_diversity": 0, "dex_after_hours_ratio": 0.0,
                "dex_mev_victim_ratio": 0.0,
            }
        swaps = await self._fetcher.fetch_dex_swaps(
            wallet, pools=[self.AGNI_POOL_FACTORY, self.MERCHANT_MOE_ROUTER]
        )
        if not swaps:
            return {
                "dex_swap_count": 0, "dex_slippage_cv": 0.0,
                "dex_pairs_diversity": 0, "dex_after_hours_ratio": 0.0,
                "dex_mev_victim_ratio": 0.0,
            }
        slippages = [s["slippage_bps"] for s in swaps if s.get("slippage_bps") is not None]
        pairs = {(s["token_in"], s["token_out"]) for s in swaps}
        from datetime import datetime
        after_hours = sum(1 for s in swaps if not (9 <= datetime.utcfromtimestamp(s["timestamp"]).hour < 17))
        sandwiched = sum(1 for s in swaps if s.get("was_sandwiched"))
        return {
            "dex_swap_count": len(swaps),
            "dex_slippage_cv": round(float(np.std(slippages) / max(np.mean(slippages), 1e-9)), 4) if slippages else 0.0,
            "dex_pairs_diversity": len(pairs),
            "dex_after_hours_ratio": round(after_hours / len(swaps), 4),
            "dex_mev_victim_ratio": round(sandwiched / len(swaps), 4),
        }

    # =========================================================
    # FEATURE CLASS 1: TEMPORAL IRREGULARITY (8 features)
    # =========================================================
    # Human decision-making has inherent noise. Agents are precise.
    # We measure the SHAPE of the inter-transaction time distribution.
    # A human's distribution is wide, right-skewed, and has high variance.
    # An agent's distribution is narrow, symmetric, and mechanically regular.

    def _temporal_irregularity_features(
        self,
        df: pd.DataFrame
    ) -> Dict[str, float]:
        deltas = df["time_since_prev_tx"].dropna()

        if len(deltas) < 3:
            return {k: 0.5 for k in [
                "temp_0_log_mean_delta", "temp_1_log_std_delta",
                "temp_2_skewness", "temp_3_kurtosis", "temp_4_cv",
                "temp_5_fast_reaction_ratio", "temp_6_autocorr", "temp_7_hour_gini",
            ]}

        # Remove outliers (gaps > 7 days indicate inactivity, not behavior)
        deltas = deltas[deltas < 604800]  # 7 days in seconds
        deltas = deltas[deltas > 0]

        if len(deltas) < 3:
            return {k: 0.5 for k in [
                "temp_0_log_mean_delta", "temp_1_log_std_delta",
                "temp_2_skewness", "temp_3_kurtosis", "temp_4_cv",
                "temp_5_fast_reaction_ratio", "temp_6_autocorr", "temp_7_hour_gini",
            ]}

        log_deltas = np.log1p(deltas)
        _ac_raw = deltas.autocorr(lag=1) if len(deltas) > 5 else 0.0
        _autocorr = float(_ac_raw) if not np.isnan(_ac_raw) else 0.0

        return {
            # Mean reaction time (log scale) — humans ~7-30 sec, agents ~0.1-2 sec
            "temp_0_log_mean_delta": float(np.mean(log_deltas)),

            # Standard deviation — humans high, agents low
            "temp_1_log_std_delta": float(np.std(log_deltas)),

            # Skewness — human distributions are right-skewed (occasional slow)
            "temp_2_skewness": float(stats.skew(log_deltas)),

            # Kurtosis — agents often have platykurtic (flat) distributions
            "temp_3_kurtosis": float(stats.kurtosis(log_deltas)),

            # Coefficient of variation — normalized variability
            # Humans: >1.0, Agents: often <0.3
            "temp_4_cv": float(
                np.std(deltas) / (np.mean(deltas) + 1e-9)
            ),

            # Proportion of very fast reactions (<2 seconds)
            # High proportion = strong agent signal
            "temp_5_fast_reaction_ratio": float(
                (deltas < 2).sum() / len(deltas)
            ),

            # Autocorrelation lag-1
            # Agents on a schedule have high autocorrelation
            # Humans are nearly uncorrelated
            "temp_6_autocorr": _autocorr,

            # Hour concentration (Gini coefficient of hourly activity)
            # Agents active 24/7 uniformly — Gini near 0
            # Humans active in specific hours — Gini near 1
            "temp_7_hour_gini": self._gini(
                df.groupby("hour_of_day").size().reindex(
                    range(24), fill_value=0
                ).values
            ),
        }

    # =========================================================
    # FEATURE CLASS 2: GAS BEHAVIOR (7 features)
    # =========================================================
    # Humans use wallets that suggest gas. They round to comfortable numbers.
    # They occasionally overpay (urgency) or underpay (inattention).
    # Agents compute precise gas via eth_gasPrice and apply exact multipliers.

    def _gas_behavior_features(
        self,
        df: pd.DataFrame
    ) -> Dict[str, float]:
        gas_prices = df["gas_price"].dropna()
        gas_prices = gas_prices[gas_prices > 0]

        if len(gas_prices) < 3:
            return {k: 0.5 for k in [
                "gas_0_price_cv", "gas_1_round_fraction", "gas_2_nice_number_fraction",
                "gas_3_percentile_variance", "gas_4_overpay_ratio",
                "gas_5_mean_efficiency", "gas_6_efficiency_std",
            ]}

        gas_in_gwei = gas_prices / 1e9

        # Rounding behavior: humans like round numbers
        # Check what fraction of gas prices end in .0 Gwei
        rounded_fraction = float(
            (gas_in_gwei % 1.0 < 0.05).sum() / len(gas_in_gwei)
        )

        # Nice number fraction (ends in 0 or 5 Gwei)
        nice_number_fraction = float(
            (gas_in_gwei % 5 < 0.1).sum() / len(gas_in_gwei)
        )

        # Gas efficiency distribution
        efficiency = df["gas_efficiency"].dropna()
        efficiency = efficiency[(efficiency > 0) & (efficiency <= 1)]

        return {
            # Overall gas price spread (agents have tighter spread)
            "gas_0_price_cv": float(
                np.std(gas_in_gwei) / (np.mean(gas_in_gwei) + 1e-9)
            ),

            # Fraction of round gas prices
            "gas_1_round_fraction": rounded_fraction,

            # Fraction of "nice number" gas prices
            "gas_2_nice_number_fraction": nice_number_fraction,

            # Gas price percentile variance across time
            # Agents consistently use median gas; humans vary more
            "gas_3_percentile_variance": float(
                np.std(
                    stats.rankdata(gas_in_gwei) / len(gas_in_gwei) * 100
                )
            ),

            # Proportion of transactions that overpaid by >50%
            # (emotional urgency is a human trait)
            "gas_4_overpay_ratio": float(
                (gas_in_gwei > gas_in_gwei.median() * 1.5).sum()
                / len(gas_in_gwei)
            ),

            # Mean gas efficiency (gas_used / gas_limit)
            # Agents tend to set limit precisely; humans over-estimate
            "gas_5_mean_efficiency": float(
                efficiency.mean() if len(efficiency) > 0 else 0.5
            ),

            # Gas efficiency std — humans more variable
            "gas_6_efficiency_std": float(
                efficiency.std() if len(efficiency) > 0 else 0.0
            ),
        }

    # =========================================================
    # FEATURE CLASS 3: INTERACTION DIVERSITY (6 features)
    # =========================================================
    # Humans are curious. They interact with many protocols, including
    # ones irrelevant to their main strategy. Agents are focused.

    def _interaction_diversity_features(
        self,
        df: pd.DataFrame
    ) -> Dict[str, float]:
        # Count unique contract addresses interacted with
        unique_contracts = df["to_addr"].nunique()
        total_txs = len(df)

        # Known protocol interactions
        known_protocols = df[df["is_known_protocol"] == True]["protocol"]
        unique_protocols = known_protocols.nunique()

        # Method ID diversity (unique function calls)
        unique_methods = df["method_id"].nunique()

        # Protocol concentration (Herfindahl-Hirschman Index)
        # 1.0 = all transactions to one protocol (agent-like)
        # Near 0 = very spread (human-like curiosity)
        protocol_counts = df.groupby("to_addr").size()
        total = protocol_counts.sum()
        hhi = float(((protocol_counts / total) ** 2).sum())

        # Ratio of transactions to unknown/new contracts
        # Humans explore. Agents don't.
        unknown_ratio = float(
            (df["is_known_protocol"] == False).sum() / total_txs
        )

        # Weekend activity ratio
        # Humans trade on weekdays more than weekends
        # Bots are uniformly active
        weekend_txs = df[df["day_of_week"].isin([5, 6])]
        weekend_ratio = float(len(weekend_txs) / total_txs)

        return {
            "div_0_unique_contract_ratio": float(
                unique_contracts / total_txs
            ),
            "div_1_unique_protocols": float(unique_protocols),
            "div_2_method_diversity": float(
                unique_methods / total_txs
            ),
            "div_3_protocol_hhi": hhi,
            "div_4_exploration_ratio": unknown_ratio,
            "div_5_weekend_ratio": weekend_ratio,
        }

    # =========================================================
    # FEATURE CLASS 4: PORTFOLIO BEHAVIOR (9 features)
    # =========================================================
    # Human traders exhibit well-documented behavioral finance biases.
    # Loss aversion, recency bias, disposition effect, overconfidence.
    # Purely rational agents do not exhibit these patterns.
    # Measuring their presence is measuring humanity.

    def _portfolio_behavior_features(
        self,
        df: pd.DataFrame
    ) -> Dict[str, float]:
        # Value-based features (approximate portfolio behavior via tx values)
        values = df["value_mnt"].dropna()
        values_nonzero = values[values > 0]

        if len(values_nonzero) < 3:
            return {k: 0.5 for k in [
                "port_0_size_cv", "port_1_size_skew", "port_2_size_kurtosis",
                "port_3_overconfidence_score", "port_4_streak_size_correlation",
                "port_5_round_value_ratio", "port_6_lognormal_fit",
                "port_7_activity_consistency", "port_8_max_to_mean_ratio",
            ]}

        # Size variation (humans are more variable in position size)
        size_cv = float(np.std(values_nonzero) / (np.mean(values_nonzero) + 1e-9))

        # Streak analysis: does the wallet increase size after wins?
        # This is the overconfidence bias signal
        # (We approximate "wins" as large value transfers —
        # in a full implementation you'd track actual P&L)
        streaks = self._compute_size_after_streak(values_nonzero)

        # Loss aversion proxy: do holdings accumulate during dips?
        # We proxy this by looking at whether wallet sends MORE
        # transactions during periods of high network activity
        # (fear-of-missing-out behavior)
        activity_consistency = self._activity_consistency_score(df)

        # Round number bias in transaction values
        # Humans prefer round numbers (0.1 ETH, 0.5 ETH, 1.0 ETH)
        round_value_ratio = float(
            sum(
                1 for v in values_nonzero
                if any(abs(v - r) < 0.001 for r in [0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 5.0, 10.0])
            ) / len(values_nonzero)
        )

        # Log-normal fit quality for transaction values
        # Human value distributions fit log-normal well
        # Agents often have more discrete/fixed values
        try:
            _ks = stats.kstest(
                np.log(values_nonzero + 1e-10),
                'norm'
            )
            lognorm_ks = float(_ks.pvalue)
        except Exception:
            lognorm_ks = 0.5

        return {
            "port_0_size_cv": size_cv,
            "port_1_size_skew": float(stats.skew(np.log1p(values_nonzero))),
            "port_2_size_kurtosis": float(
                stats.kurtosis(np.log1p(values_nonzero))
            ),
            "port_3_overconfidence_score": streaks.get("overconfidence", 0.5),
            "port_4_streak_size_correlation": streaks.get("size_corr", 0.0),
            "port_5_round_value_ratio": round_value_ratio,
            "port_6_lognormal_fit": float(lognorm_ks),
            "port_7_activity_consistency": activity_consistency,
            "port_8_max_to_mean_ratio": float(
                values_nonzero.max() / (values_nonzero.mean() + 1e-9)
            ),
        }

    # =========================================================
    # FEATURE CLASS 5: TEMPORAL CORRELATION TO EVENTS (5 features)
    # =========================================================
    # Human traders react to news events through social media.
    # Their reaction has a delayed, variable onset.
    # Agents react instantly and precisely if triggered.

    def _temporal_correlation_features(
        self,
        df: pd.DataFrame
    ) -> Dict[str, float]:
        # We measure burstiness — human activity has bursts separated
        # by long quiet periods (driven by news cycles, daily routines)
        # Agents have more uniform activity.

        if len(df) < 10:
            return {k: 0.5 for k in [
                "event_0_burstiness", "event_1_memory", "event_2_clustering",
                "event_3_avg_session_txs", "event_4_session_gap_cv",
            ]}

        timestamps = df["timestamp"].sort_values()
        deltas = timestamps.diff().dropna()

        # Burstiness parameter (Goh & Barabasi 2008)
        # B = (std - mean) / (std + mean)
        # B near 1 = very bursty (human)
        # B near -1 = very regular (agent)
        std_delta = deltas.std()
        mean_delta = deltas.mean()
        burstiness = float(
            (std_delta - mean_delta) / (std_delta + mean_delta + 1e-9)
        )

        # Memory coefficient (correlation between consecutive intervals)
        # Humans: clustered activity leads to positive memory
        # Agents on cron jobs: near-zero memory
        if len(deltas) > 5:
            m1 = deltas.iloc[:-1].values
            m2 = deltas.iloc[1:].values
            mean_m1 = m1.mean()
            mean_m2 = m2.mean()
            std_m1 = m1.std()
            std_m2 = m2.std()
            memory = float(
                np.mean((m1 - mean_m1) * (m2 - mean_m2)) /
                (std_m1 * std_m2 + 1e-9)
            )
        else:
            memory = 0.0

        # Activity clustering (proportion of tx in top 10% time windows)
        hourly_activity = df.groupby(
            pd.to_datetime(df["timestamp"], unit="s").dt.hour
        ).size()
        top_10pct_threshold = np.percentile(hourly_activity, 90)
        clustering = float(
            hourly_activity[hourly_activity >= top_10pct_threshold].sum()
            / len(df)
        )

        # Active session detection
        # Humans have "sessions" (30-60 min of activity then long break)
        sessions = self._detect_sessions(df, gap_threshold=3600)  # 1 hr gap
        avg_session_txs = float(
            np.mean([s["tx_count"] for s in sessions])
            if sessions else 1.0
        )

        # Inter-session gap regularity (agents have regular session gaps)
        session_gaps = [
            sessions[i+1]["start"] - sessions[i]["end"]
            for i in range(len(sessions)-1)
        ]
        session_gap_cv = float(
            np.std(session_gaps) / (np.mean(session_gaps) + 1e-9)
            if len(session_gaps) > 1 else 0.5
        )

        return {
            "event_0_burstiness": burstiness,
            "event_1_memory": memory,
            "event_2_clustering": clustering,
            "event_3_avg_session_txs": np.log1p(avg_session_txs),
            "event_4_session_gap_cv": session_gap_cv,
        }

    # =========================================================
    # FEATURE CLASS 6: BEHAVIORAL CONSISTENCY (6 features)
    # =========================================================
    # Humans become more erratic during market stress.
    # Agents either hold steady or stop.

    def _behavioral_consistency_features(
        self,
        df: pd.DataFrame
    ) -> Dict[str, float]:
        if len(df) < 20:
            return {k: 0.5 for k in [
                "consist_0_stress_variance_ratio", "consist_1_timing_early_cv",
                "consist_2_timing_late_cv", "consist_3_cv_evolution",
                "consist_4_failure_rate", "consist_5_method_evolution",
            ]}

        # Detect high-activity periods (proxy for market stress)
        # (In full implementation, correlate with Mantle network gas price spikes)
        txs_per_hour = df.groupby(
            pd.to_datetime(df["timestamp"], unit="s").dt.floor("h")
        ).size()

        high_activity_threshold = txs_per_hour.quantile(0.75)
        high_periods = txs_per_hour[txs_per_hour >= high_activity_threshold]
        low_periods = txs_per_hour[txs_per_hour < high_activity_threshold]

        # Variance ratio: high-activity vs low-activity periods
        # Humans: higher variance during stress
        # Agents: similar variance regardless of conditions
        if len(high_periods) > 2 and len(low_periods) > 2:
            variance_ratio = float(
                high_periods.std() / (low_periods.std() + 1e-9)
            )
        else:
            variance_ratio = 1.0

        # Transaction timing precision over time
        # Measure whether timing gets more or less regular across time
        # Split tx history in half and compare timing CVs
        mid = len(df) // 2
        early_deltas = df.iloc[:mid]["time_since_prev_tx"].dropna()
        late_deltas = df.iloc[mid:]["time_since_prev_tx"].dropna()

        early_cv = float(
            np.std(early_deltas) / (np.mean(early_deltas) + 1e-9)
            if len(early_deltas) > 2 else 0.5
        )
        late_cv = float(
            np.std(late_deltas) / (np.mean(late_deltas) + 1e-9)
            if len(late_deltas) > 2 else 0.5
        )

        # Failure rate — humans sometimes fail txs (wrong gas, mistakes)
        failure_rate = float(df["failed"].mean())

        # Method diversity over time
        # Do they use the same methods over and over? (agent) or explore? (human)
        early_methods = df.iloc[:mid]["method_id"].nunique()
        late_methods = df.iloc[mid:]["method_id"].nunique()
        method_evolution = float(late_methods / (early_methods + 1))

        return {
            "consist_0_stress_variance_ratio": variance_ratio,
            "consist_1_timing_early_cv": early_cv,
            "consist_2_timing_late_cv": late_cv,
            "consist_3_cv_evolution": late_cv - early_cv,
            "consist_4_failure_rate": failure_rate,
            "consist_5_method_evolution": method_evolution,
        }

    # =========================================================
    # FEATURE CLASS 7: NETWORK FEATURES (6 features)
    # =========================================================
    # Coordinated bot farms show distinctive graph patterns.
    # Multiple wallets funded from same source, trading in sync.

    def _network_features(
        self,
        df: pd.DataFrame,
        wallet_address: str
    ) -> Dict[str, float]:
        # Unique counterparties this wallet has sent to
        sent_txs = df[df["is_sender"] == True]
        unique_recipients = sent_txs["to_addr"].nunique()

        # Repeat interaction ratio (same address repeatedly)
        # Agents often interact with only 1-3 contract addresses
        recipient_counts = sent_txs["to_addr"].value_counts()
        top1_ratio = float(
            recipient_counts.iloc[0] / len(sent_txs)
            if len(sent_txs) > 0 else 0.5
        )
        top3_ratio = float(
            recipient_counts.iloc[:3].sum() / len(sent_txs)
            if len(sent_txs) > 2 else 0.5
        )

        # Wallet age in blocks
        if len(df) > 0:
            age_blocks = float(
                df["block_number"].max() - df["block_number"].min()
            )
        else:
            age_blocks = 0.0

        # Transaction volume log10
        total_volume = float(np.log1p(df["value_mnt"].sum()))

        # Average MNT per transaction
        avg_tx_value = float(np.log1p(df["value_mnt"].mean()))

        # Contract vs EOA interaction ratio
        # Agents interact mostly with contracts
        # Humans also send MNT to other humans (EOAs)
        contract_ratio = float(
            df["is_contract_call"].mean()
        )

        return {
            "net_0_unique_recipient_ratio": float(
                unique_recipients / (len(sent_txs) + 1)
            ),
            "net_1_top1_concentration": top1_ratio,
            "net_2_top3_concentration": top3_ratio,
            "net_3_wallet_age_blocks_log": np.log1p(age_blocks),
            "net_4_total_volume_log": total_volume,
            "net_5_contract_ratio": contract_ratio,
        }

    # =========================================================
    # UTILITY METHODS
    # =========================================================

    def _gini(self, values: np.ndarray) -> float:
        """
        Computes Gini coefficient of an array.
        0 = perfectly equal distribution (agent-like 24/7 activity)
        1 = perfectly concentrated (all activity in one hour)
        Human activity has Gini ~0.4-0.7 (peak hours but not exclusive)
        """
        if len(values) < 2 or values.sum() == 0:
            return 0.0
        values = np.sort(values)
        n = len(values)
        cumsum = np.cumsum(values)
        return float(
            (2 * np.sum((np.arange(1, n+1)) * values) - (n+1) * cumsum[-1])
            / (n * cumsum[-1])
        )

    def _compute_size_after_streak(
        self,
        values: pd.Series
    ) -> Dict[str, float]:
        """
        Checks if transaction sizes increase after a "winning" streak.
        A winning streak is defined as N consecutive transactions
        of above-median value (proxy for profitable period).
        Humans get overconfident after wins and increase size.
        """
        if len(values) < 10:
            return {"overconfidence": 0.5, "size_corr": 0.0}

        median = values.median()
        # Define win streak as 3+ consecutive above-median txs
        win_mask = values > median
        streak_lengths = []
        current_streak = 0

        for is_win in win_mask:
            if is_win:
                current_streak += 1
            else:
                if current_streak > 0:
                    streak_lengths.append(current_streak)
                current_streak = 0

        if current_streak > 0:
            streak_lengths.append(current_streak)

        if not streak_lengths:
            return {"overconfidence": 0.5, "size_corr": 0.0}

        avg_streak = np.mean(streak_lengths)
        # Overconfidence score: longer streaks + size increase = high score
        # We normalize to 0-1 range where 0.5 = neutral
        overconfidence = float(
            min(1.0, avg_streak / 5.0) * 0.5 + 0.25
        )

        # Correlation between streak position and next tx size
        positions = list(range(len(values)))
        size_corr = float(np.corrcoef(positions, values)[0, 1])
        if np.isnan(size_corr):
            size_corr = 0.0

        return {"overconfidence": overconfidence, "size_corr": size_corr}

    def _activity_consistency_score(self, df: pd.DataFrame) -> float:
        """
        Measures how consistent the wallet's activity level is across time.
        Agents: highly consistent. Humans: variable.
        Returns a score where low = consistent (agent), high = variable (human).
        """
        hourly = df.groupby(
            pd.to_datetime(df["timestamp"], unit="s").dt.floor("6h")
        ).size()

        if len(hourly) < 4:
            return 0.5

        return float(
            np.std(hourly) / (np.mean(hourly) + 1e-9)
        )

    def _detect_sessions(
        self,
        df: pd.DataFrame,
        gap_threshold: int = 3600
    ) -> List[Dict]:
        """
        Identifies trading sessions — clusters of activity separated
        by gaps longer than gap_threshold seconds.
        Returns list of session dicts with start, end, tx_count.
        """
        if len(df) < 2:
            return []

        sessions = []
        session_start = df.iloc[0]["timestamp"]
        session_tx_count = 1
        prev_ts = df.iloc[0]["timestamp"]

        for _, row in df.iloc[1:].iterrows():
            if row["timestamp"] - prev_ts > gap_threshold:
                sessions.append({
                    "start": session_start,
                    "end": prev_ts,
                    "tx_count": session_tx_count
                })
                session_start = row["timestamp"]
                session_tx_count = 1
            else:
                session_tx_count += 1
            prev_ts = row["timestamp"]

        # Add final session
        sessions.append({
            "start": session_start,
            "end": prev_ts,
            "tx_count": session_tx_count
        })

        return sessions