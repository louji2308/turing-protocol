import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Tuple, Dict
from loguru import logger
from tqdm import tqdm
import joblib
import json

from data_pipeline.mantle_fetcher import MantleDataFetcher
from data_pipeline.feature_engineer import BehavioralFeatureEngineer


class DatasetBuilder:
    """
    Builds the labeled training dataset for the Interrogator.

    Label conventions:
    0 = Agent / Bot (Human Probability = low)
    1 = Human (Human Probability = high)

    Strategy for obtaining labeled data:
    - KNOWN AGENTS (label=0): Deploy simple bots on testnet.
      Record their wallet addresses. These are ground-truth agents.
    - KNOWN HUMANS (label=1): Identify Mantle wallets with characteristics
      that are statistically impossible to produce mechanically:
      * Active for 6+ months
      * Activity concentrated in specific hours (timezone-consistent)
      * Irregular inter-tx timing (CV > 1.5)
      * High protocol diversity (6+ unique protocols)
      * Transaction failures > 0% (humans make mistakes)
    """

    def __init__(
        self,
        rpc_url: str,
        data_dir: str = "interrogator/data"
    ):
        self.fetcher = MantleDataFetcher(rpc_url)
        self.engineer = BehavioralFeatureEngineer()
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def build_from_address_lists(
        self,
        human_addresses: List[str],
        agent_addresses: List[str],
        max_txs_per_wallet: int = 150
    ) -> pd.DataFrame:
        """
        Primary method to build training dataset.

        Args:
            human_addresses: List of wallet addresses known to be human
            agent_addresses: List of wallet addresses known to be agents
            max_txs_per_wallet: Transaction history depth

        Returns:
            DataFrame with 47 features + label column
        """
        all_features = []
        all_labels = []

        # Process human wallets
        logger.info(f"Processing {len(human_addresses)} human wallets...")
        for addr in tqdm(human_addresses, desc="Human wallets"):
            try:
                df = self.fetcher.fetch_wallet_transactions(
                    addr, max_txs_per_wallet
                )
                if len(df) < 20:
                    continue
                features = self.engineer.compute_all_features(df, addr)
                all_features.append(features)
                all_labels.append(1)  # Human
            except Exception as e:
                logger.warning(f"Skipped human {addr[:10]}: {e}")

        # Process agent wallets
        logger.info(f"Processing {len(agent_addresses)} agent wallets...")
        for addr in tqdm(agent_addresses, desc="Agent wallets"):
            try:
                df = self.fetcher.fetch_wallet_transactions(
                    addr, max_txs_per_wallet
                )
                if len(df) < 20:
                    continue
                features = self.engineer.compute_all_features(df, addr)
                all_features.append(features)
                all_labels.append(0)  # Agent
            except Exception as e:
                logger.warning(f"Skipped agent {addr[:10]}: {e}")

        # Assemble into DataFrame
        feature_df = pd.DataFrame(all_features)
        feature_df["label"] = all_labels

        # Log class balance
        n_humans = sum(all_labels)
        n_agents = len(all_labels) - n_humans
        logger.success(
            f"Dataset built: {n_humans} humans, {n_agents} agents. "
            f"Total: {len(feature_df)} samples, {feature_df.shape[1]-1} features."
        )

        # Save to disk
        output_path = self.data_dir / "training_data.parquet"
        feature_df.to_parquet(output_path, index=False)
        logger.success(f"Saved to {output_path}")

        return feature_df

    def generate_synthetic_agent_wallets(
        self,
        n_wallets: int = 50
    ) -> List[Dict]:
        """
        Generates synthetic feature vectors for known-agent behavior.
        Used when you don't have enough real agent wallets.

        This mimics several types of agents:
        - Type A: MEV bot (extremely fast, precise gas)
        - Type B: Scheduled DCA bot (cron-like timing)
        - Type C: Arbitrage bot (reactive to price, multi-step)
        - Type D: LP management bot (slow but very regular)
        """
        rng = np.random.default_rng(42)
        synthetic_agents = []

        agent_types = ["mev", "dca", "arbitrage", "lp_manager"]

        for i in range(n_wallets):
            agent_type = rng.choice(agent_types)
            features = self._generate_agent_features(agent_type, rng)
            features["label"] = 0
            features["source"] = f"synthetic_{agent_type}"
            synthetic_agents.append(features)

        return synthetic_agents

    def _generate_agent_features(
        self,
        agent_type: str,
        rng: np.random.Generator
    ) -> Dict[str, float]:
        """
        Generates a feature vector matching the behavioral profile
        of a specific agent type. Based on analysis of real bot behavior.
        """
        base = {f: 0.5 for f in [
            "temp_0_log_mean_delta", "temp_1_log_std_delta",
            "temp_2_skewness", "temp_3_kurtosis", "temp_4_cv",
            "temp_5_fast_reaction_ratio", "temp_6_autocorr",
            "temp_7_hour_gini",
            "gas_0_price_cv", "gas_1_round_fraction",
            "gas_2_nice_number_fraction", "gas_3_percentile_variance",
            "gas_4_overpay_ratio", "gas_5_mean_efficiency",
            "gas_6_efficiency_std",
            "div_0_unique_contract_ratio", "div_1_unique_protocols",
            "div_2_method_diversity", "div_3_protocol_hhi",
            "div_4_exploration_ratio", "div_5_weekend_ratio",
            "port_0_size_cv", "port_1_size_skew",
            "port_2_size_kurtosis", "port_3_overconfidence_score",
            "port_4_streak_size_correlation", "port_5_round_value_ratio",
            "port_6_lognormal_fit", "port_7_activity_consistency",
            "port_8_max_to_mean_ratio",
            "event_0_burstiness", "event_1_memory",
            "event_2_clustering", "event_3_avg_session_txs",
            "event_4_session_gap_cv",
            "consist_0_stress_variance_ratio", "consist_1_timing_early_cv",
            "consist_2_timing_late_cv", "consist_3_cv_evolution",
            "consist_4_failure_rate", "consist_5_method_evolution",
            "net_0_unique_recipient_ratio", "net_1_top1_concentration",
            "net_2_top3_concentration", "net_3_wallet_age_blocks_log",
            "net_4_total_volume_log", "net_5_contract_ratio",
        ]}

        if agent_type == "mev":
            # MEV bot: microsecond precision, perfect gas optimization
            base.update({
                "temp_0_log_mean_delta": rng.normal(0.5, 0.1),   # Very fast
                "temp_1_log_std_delta": rng.normal(0.2, 0.05),   # Very consistent
                "temp_4_cv": rng.normal(0.1, 0.05),              # Low variance
                "temp_5_fast_reaction_ratio": rng.normal(0.9, 0.05),  # Almost all fast
                "temp_6_autocorr": rng.normal(0.8, 0.1),         # High autocorrelation
                "temp_7_hour_gini": rng.normal(0.1, 0.05),       # Active 24/7
                "gas_0_price_cv": rng.normal(0.05, 0.02),        # Very precise gas
                "gas_1_round_fraction": rng.normal(0.05, 0.02),  # Never rounds
                "div_1_unique_protocols": rng.normal(1.5, 0.5),  # 1-2 protocols only
                "div_3_protocol_hhi": rng.normal(0.9, 0.05),     # Very concentrated
                "consist_4_failure_rate": rng.normal(0.001, 0.001),  # Never fails
                "net_5_contract_ratio": rng.normal(0.99, 0.01),  # Always contracts
            })

        elif agent_type == "dca":
            # DCA bot: cron-like timing, very regular
            base.update({
                "temp_4_cv": rng.normal(0.05, 0.02),    # Extremely regular
                "temp_6_autocorr": rng.normal(0.95, 0.03),  # Near-perfect regularity
                "temp_7_hour_gini": rng.normal(0.05, 0.02), # 24/7 uniform
                "event_0_burstiness": rng.normal(-0.8, 0.1), # Very regular
                "event_4_session_gap_cv": rng.normal(0.02, 0.01), # Identical gaps
                "port_0_size_cv": rng.normal(0.02, 0.01), # Same size every time
            })

        elif agent_type == "arbitrage":
            # Arbitrage bot: fast but slightly variable, multi-step
            base.update({
                "temp_5_fast_reaction_ratio": rng.normal(0.7, 0.1),
                "div_3_protocol_hhi": rng.normal(0.4, 0.1), # Multiple protocols
                "div_1_unique_protocols": rng.normal(3, 0.5), # Few but specific
                "event_0_burstiness": rng.normal(0.2, 0.1),  # Some burst (trades)
                "consist_4_failure_rate": rng.normal(0.02, 0.01), # Rare fails
            })

        elif agent_type == "lp_manager":
            # LP management bot: slower, but very consistent
            base.update({
                "temp_4_cv": rng.normal(0.3, 0.1),
                "div_1_unique_protocols": rng.normal(2, 0.5),
                "div_3_protocol_hhi": rng.normal(0.8, 0.1),
                "event_4_session_gap_cv": rng.normal(0.1, 0.05),
                "net_5_contract_ratio": rng.normal(0.98, 0.01),
            })

        # Clip all values to [0, 1] where applicable
        for k in base:
            base[k] = float(np.clip(base[k], 0.0, 2.0))

        return base