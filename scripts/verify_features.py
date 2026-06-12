# scripts/verify_features.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
from data_pipeline.feature_engineer import BehavioralFeatureEngineer

def make_synthetic_df(n=80, seed=42, mode='human'):
    rng = np.random.default_rng(seed)
    if mode == 'human':
        delays = rng.lognormal(mean=2.5, sigma=1.2, size=n)
        gas_prices = rng.choice(
            np.array([1_000_000_000, 2_000_000_000, 3_000_000_000,
                      5_000_000_000, 10_000_000_000], dtype=np.int64),
            n
        )
        hours = rng.integers(8, 23, n)
        days = rng.integers(0, 5, n)
        failures = np.zeros(n, dtype=np.int64)
        failures[rng.choice(n, max(1, n // 12), replace=False)] = 1
        values = rng.lognormal(mean=1, sigma=1.5, size=n) * 1e18
        protocols = rng.choice(['proto_a','proto_b','proto_c','unknown','proto_d'], n)
    else:
        delays = np.clip(rng.normal(0.5, 0.05, n), 0.01, 2.0)
        gas_prices = np.full(n, 2_000_000_000, dtype=np.int64)
        hours = (np.arange(n) % 24).astype(int)
        days = (np.arange(n) % 7).astype(int)
        failures = np.zeros(n, dtype=int)
        values = np.full(n, 1e18)
        protocols = np.full(n, 'proto_a')

    timestamps = np.cumsum(delays) + 1700000000
    wallet = '0x' + 'a' * 40

    df = pd.DataFrame({
        'timestamp': timestamps.astype(np.int64),
        'block_number': np.arange(1000, 1000+n),
        'from_addr': [wallet]*n,
        'to_addr': list(protocols),
        'value_wei': np.clip(values, 0, 9_200_000_000_000_000_000).astype(np.int64),
        'gas_limit': np.full(n, 100000),
        'gas_used': np.full(n, 80000),
        'gas_price': gas_prices.astype(np.int64),
        'failed': failures,
        'input_data': ['0x12345678'+'0'*56]*n,
        'is_sender': [True]*n,
        'is_contract_call': [True]*n,
        'method_id': list(rng.choice(['0xaabb', '0xccdd', '0xeeff', '0x1122'], n)),
        'success': 1 - failures,
        'value_mnt': values/1e18,
        'gas_cost_mnt': np.full(n, 0.0001),
        'gas_efficiency': np.full(n, 0.8),
        'hour_of_day': hours,
        'day_of_week': days,
        'time_since_prev_tx': delays,
        'protocol': list(protocols),
        'is_known_protocol': [p != 'unknown' for p in protocols],
    })
    return df, wallet

eng = BehavioralFeatureEngineer()

print("=== Testing HUMAN synthetic wallet ===")
df_h, addr_h = make_synthetic_df(80, mode='human')
try:
    feats_h = eng.compute_all_features(df_h, addr_h)
    print(f"Feature count: {len(feats_h)} (expected 47)")
    assert len(feats_h) == 47, f"WRONG COUNT: {len(feats_h)}"
    print("All feature values valid (no NaN):", all(v == v for v in feats_h.values()))
    print("Feature names sample:", list(feats_h.keys())[:5])
    print("HUMAN TEST PASSED")
except Exception as e:
    print(f"HUMAN TEST FAILED: {e}")

print()
print("=== Testing AGENT synthetic wallet ===")
df_a, addr_a = make_synthetic_df(80, mode='agent')
try:
    feats_a = eng.compute_all_features(df_a, addr_a)
    print(f"Feature count: {len(feats_a)} (expected 47)")
    assert len(feats_a) == 47
    print("AGENT TEST PASSED")
except Exception as e:
    print(f"AGENT TEST FAILED: {e}")

print()
print("=== Comparing key signals: HUMAN vs AGENT ===")
if 'feats_h' in locals() and 'feats_a' in locals():
    print(f"temp_4_cv (timing variability)  → human: {feats_h['temp_4_cv']:.4f}  agent: {feats_a['temp_4_cv']:.4f}  (human should be HIGHER)")
    print(f"temp_5_fast_reaction_ratio      → human: {feats_h['temp_5_fast_reaction_ratio']:.4f}  agent: {feats_a['temp_5_fast_reaction_ratio']:.4f}  (agent should be HIGHER)")
    print(f"temp_7_hour_gini                → human: {feats_h['temp_7_hour_gini']:.4f}  agent: {feats_a['temp_7_hour_gini']:.4f}  (human should be HIGHER)")
    print(f"consist_4_failure_rate          → human: {feats_h['consist_4_failure_rate']:.4f}  agent: {feats_a['consist_4_failure_rate']:.4f}  (human should be HIGHER)")
    print(f"port_0_size_cv                  → human: {feats_h['port_0_size_cv']:.4f}  agent: {feats_a['port_0_size_cv']:.4f}  (human should be HIGHER)")
    print(f"gas_0_price_cv                  → human: {feats_h['gas_0_price_cv']:.4f}  agent: {feats_a['gas_0_price_cv']:.4f}  (human should be HIGHER)")