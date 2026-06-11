import sys
sys.path.insert(0, '.')

import numpy as np
import pandas as pd
from pathlib import Path
from loguru import logger
from data_pipeline.feature_engineer import BehavioralFeatureEngineer


def make_synthetic_wallet_df(n=80, seed=42, human_strength=0.5):
    """
    Generates a wallet's transaction history on a spectrum from pure agent
    to pure human.

    Parameters
    ----------
    n : int
        Number of transactions.
    seed : int
        RNG seed — each wallet gets a unique one.
    human_strength : float, 0.0–1.0
        0.0 = textbook agent (fast, regular, precise).
        1.0 = textbook human (slow, irregular, sloppy).
        Values around 0.3–0.7 produce ambiguous wallets that make
        the classification problem realistic.
    """
    rng = np.random.default_rng(seed)

    # ------------------------------------------------------------------
    # 1. INTER-TRANSACTION DELAYS
    # ------------------------------------------------------------------
    # Agent component: fast, low-variance
    agent_delays = np.clip(rng.normal(0.3, 0.10, n), 0.05, 3.0)
    # Human component: slow, high-variance, log-normal
    human_delays = np.clip(rng.lognormal(mean=2.2, sigma=1.0, size=n), 0.05, 3600)
    # Some agents have cron-like periodic behavior
    if rng.random() < 0.3:
        interval = rng.choice([600, 1800, 3600, 7200, 14400, 28800, 86400])
        cron = np.full(n // 3, interval) * rng.normal(1.0, 0.02, n // 3)
        agent_delays[:len(cron)] = cron

    # Blend: human_strength controls the mix
    # At 0.0: pure agent, at 1.0: pure human
    blend = rng.beta(
        a=2.0 * (1.0 - human_strength) + 0.5,
        b=2.0 * human_strength + 0.5,
    ) if human_strength not in (0.0, 1.0) else human_strength
    delays = agent_delays * (1.0 - blend) + human_delays * blend
    delays = np.clip(delays, 0.05, 3600)

    # ------------------------------------------------------------------
    # 2. GAS PRICES
    # ------------------------------------------------------------------
    # Agent: tight, precise (one base price + tiny jitter)
    base_gas = rng.choice([1_000_000_000, 2_000_000_000, 3_000_000_000])
    agent_gas = np.full(n, base_gas, dtype=np.int64)
    # Human: varied, rounded, occasional overpay
    round_gas = rng.choice(
        np.array([1_000_000_000, 2_000_000_000, 3_000_000_000,
                  5_000_000_000, 10_000_000_000, 15_000_000_000,
                  20_000_000_000, 50_000_000_000], dtype=np.int64), n
    )
    human_gas = round_gas + rng.integers(0, 1_000_000_000, n)
    gas_prices = agent_gas.astype(np.int64) * (1.0 - blend) + human_gas.astype(np.int64) * blend
    gas_prices = gas_prices.astype(np.int64)

    # ------------------------------------------------------------------
    # 3. HOUR OF DAY
    # ------------------------------------------------------------------
    # Agent: uniform 0–23 or a narrow band
    if rng.random() < 0.6:
        agent_hours = rng.integers(0, 24, n)
    else:
        band_start = rng.integers(0, 18)
        agent_hours = rng.integers(band_start, band_start + 6, n)
    # Human: concentrated in waking hours 7–23, with occasional night
    human_hours = rng.integers(7, 23, n)
    if rng.random() < 0.3:
        n_night = rng.integers(1, n // 4)
        human_hours[rng.choice(n, n_night, replace=False)] = rng.integers(0, 6, n_night)
    hours = (agent_hours * (1.0 - blend) + human_hours * blend).astype(int) % 24

    # ------------------------------------------------------------------
    # 4. DAY OF WEEK
    # ------------------------------------------------------------------
    agent_days = rng.integers(0, 7, n)
    human_days = rng.integers(0, 5, n)
    if rng.random() < 0.4:
        n_weekend = rng.integers(1, max(2, n // 5))
        human_days[rng.choice(n, n_weekend, replace=False)] = rng.integers(5, 7, n_weekend)
    days = (agent_days * (1.0 - blend) + human_days * blend).astype(int) % 7

    # ------------------------------------------------------------------
    # 5. FAILURES
    # ------------------------------------------------------------------
    # Agent: nearly zero failures
    agent_failures = np.zeros(n, dtype=np.int64)
    # Human: small but non-zero failure rate
    human_fail_rate = rng.beta(1, 8)
    n_fail = max(1, int(n * human_fail_rate))
    human_failures = np.zeros(n, dtype=np.int64)
    human_failures[rng.choice(n, n_fail, replace=False)] = 1
    failures = np.where(
        rng.random(n) < blend,
        human_failures,
        agent_failures,
    ).astype(np.int64)

    # ------------------------------------------------------------------
    # 6. TRANSACTION VALUES
    # ------------------------------------------------------------------
    agent_values = rng.choice(
        [0.01, 0.1, 0.5, 1.0, 5.0, 10.0], n
    ) + rng.normal(0, 0.001, n)
    human_values = rng.lognormal(mean=0.5, sigma=1.5, size=n)
    # Round-number bias for humans
    for i in range(n):
        if rng.random() < 0.3:
            human_values[i] = rng.choice([0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0])
    values_mnt = agent_values * (1.0 - blend) + human_values * blend
    values_mnt = np.clip(values_mnt, 0.0001, 200.0)
    values_wei = (values_mnt * 1e18).astype(np.int64)

    # ------------------------------------------------------------------
    # 7. PROTOCOL DIVERSITY
    # ------------------------------------------------------------------
    all_protos = [
        'proto_a', 'proto_b', 'proto_c', 'proto_d', 'proto_e',
        'proto_f', 'proto_g', 'proto_h', 'proto_i', 'proto_j',
        'unknown', 'proto_k', 'proto_l',
    ]
    # Agent: 1–3 protocols (concentrated)
    n_agent_protos = rng.integers(1, 4)
    agent_protos_pool = all_protos[:8]  # known protocols only (no 'unknown')
    agent_proto_weights = rng.dirichlet(np.ones(n_agent_protos) * 2.0)
    agent_protos = rng.choice(
        rng.choice(agent_protos_pool, n_agent_protos, replace=False),
        n, p=agent_proto_weights / agent_proto_weights.sum(),
    )
    # Human: 3–12 protocols (exploratory, includes unknown)
    n_human_protos = rng.integers(3, min(12, n))
    human_protos = rng.choice(all_protos, n_human_protos, replace=False)
    human_proto_weights = rng.dirichlet(np.ones(n_human_protos) * 0.8)
    human_protos_assigned = rng.choice(
        human_protos, n, p=human_proto_weights / human_proto_weights.sum(),
    )
    protocols = np.where(
        rng.random(n) < blend,
        human_protos_assigned,
        agent_protos,
    )

    # ------------------------------------------------------------------
    # 8. GAS EFFICIENCY (gas_used / gas_limit)
    # ------------------------------------------------------------------
    # Agent: tight — limit close to used
    agent_used = rng.integers(70000, 90000, n)
    agent_limit = agent_used + rng.integers(5000, 15000, n)
    # Human: loose — often over-estimate limit
    human_used = rng.integers(30000, 150000, n)
    human_limit = human_used + rng.integers(20000, 150000, n)
    gas_used = (agent_used * (1.0 - blend) + human_used * blend).astype(np.int64)
    gas_limit = (agent_limit * (1.0 - blend) + human_limit * blend).astype(np.int64)

    # ------------------------------------------------------------------
    # 9. METHOD ID DIVERSITY
    # ------------------------------------------------------------------
    all_methods = ['0xaabb', '0xccdd', '0xeeff', '0x1122', '0x3344', '0x5566', '0x7788', '0x9900']
    n_agent_methods = rng.integers(1, 3)
    n_human_methods = rng.integers(2, min(7, n))
    method_ids = np.where(
        rng.random(n) < blend,
        rng.choice(all_methods[:n_human_methods], n),
        rng.choice(all_methods[:n_agent_methods], n),
    )

    # ------------------------------------------------------------------
    # BUILD DATAFRAME
    # ------------------------------------------------------------------
    timestamps = np.cumsum(delays) + 1700000000
    wallet = '0x' + 'a' * 40

    df = pd.DataFrame({
        'timestamp': timestamps.astype(np.int64),
        'block_number': np.arange(1000, 1000 + n),
        'from_addr': [wallet] * n,
        'to_addr': list(protocols),
        'value_wei': values_wei,
        'gas_limit': gas_limit,
        'gas_used': gas_used,
        'gas_price': gas_prices,
        'failed': failures,
        'input_data': ['0x12345678' + '0' * 56] * n,
        'is_sender': [True] * n,
        'is_contract_call': [True] * n,
        'method_id': list(method_ids),
        'success': 1 - failures,
        'value_mnt': values_mnt,
        'gas_cost_mnt': (gas_prices * gas_used) / 1e18,
        'gas_efficiency': gas_used.astype(float) / gas_limit.astype(float),
        'hour_of_day': hours,
        'day_of_week': days,
        'time_since_prev_tx': delays,
        'protocol': list(protocols),
        'is_known_protocol': [p != 'unknown' for p in protocols],
    })
    return df, wallet


def main():
    eng = BehavioralFeatureEngineer()
    all_features = []
    all_labels = []

    n_wallets = 1000

    # --- Generate wallets on a spectrum ---
    # human_strength = 0.0 → 0.2: strong agents
    # human_strength = 0.3 → 0.5: ambiguous / borderline
    # human_strength = 0.6 → 1.0: strong humans
    #
    # Label rule:
    #   human_strength > 0.5 → human (label=1)
    #   human_strength <= 0.5 → agent (label=0)
    #
    # Because wallets near 0.5 are borderline, the model will see
    # ambiguous samples and CANNOT achieve perfect separation.

    rng = np.random.default_rng(42)

    for i in range(n_wallets):
        # Draw human_strength from a U-shaped bimodal distribution
        # Most wallets are clearly human or clearly agent,
        # but ~20% fall in the ambiguous middle.
        if rng.random() < 0.4:
            human_strength = rng.beta(0.5, 0.5)  # U-shaped: clusters at 0 and 1
        else:
            human_strength = rng.beta(1.5, 1.5)  # bell-shaped around 0.5

        label = 1 if human_strength > 0.5 else 0

        n_txs = rng.integers(40, 130)
        df, addr = make_synthetic_wallet_df(
            n=n_txs, seed=i * 7 + 13, human_strength=human_strength,
        )
        try:
            feats = eng.compute_all_features(df, addr)
            all_features.append(feats)
            all_labels.append(label)
        except Exception as e:
            logger.warning(f"Skipped wallet {i} (strength={human_strength:.2f}): {e}")

    feature_df = pd.DataFrame(all_features)
    feature_df['label'] = all_labels

    n_humans = sum(all_labels)
    n_agents = len(all_labels) - n_humans
    logger.success(
        f"Dataset: {n_humans} humans, {n_agents} agents, "
        f"{feature_df.shape[1] - 1} features"
    )

    out_path = Path("interrogator/data/training_data.parquet")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    feature_df.to_parquet(out_path, index=False)
    logger.success(f"Saved to {out_path}")

    assert feature_df['label'].nunique() == 2, "Missing a class!"
    assert feature_df.shape[1] == 48, f"Expected 48 cols (47 features + label), got {feature_df.shape[1]}"
    logger.success("Sanity check passed.")


if __name__ == "__main__":
    main()
