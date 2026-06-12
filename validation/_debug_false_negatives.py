#!/usr/bin/env python3
"""Deep-dive into the 2 false negatives: kristoph.eth & ihorkhyzhniak.eth"""

import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from interrogator.scorer import WalletScorer
from data_pipeline.mantle_fetcher import MantleDataFetcher
from data_pipeline.feature_engineer import BehavioralFeatureEngineer
from data_pipeline.preprocessing import FeaturePreprocessor
from scorers.dimension_scorer import DimensionScorer, hybrid_hps
from interrogator.model import InterrogatorModel
from dotenv import load_dotenv

load_dotenv()

MAINNET_RPC = "https://rpc.mantle.xyz"
MODELS_DIR = "interrogator/models"

addrs = {
    "kristoph.eth": "0xb3397a6feedff2b9fce9ca1086cb1bdd617c16bf",
    "ihorkhyzhniak.eth": "0x8c9a169f0a4e3daa2e8d885f1f170dda11db771b",
}

fetcher = MantleDataFetcher(MAINNET_RPC)
engineer = BehavioralFeatureEngineer()
preprocessor = FeaturePreprocessor(MODELS_DIR)
model = InterrogatorModel(MODELS_DIR)
model.load()
dim_scorer = DimensionScorer()

for name, addr in addrs.items():
    print(f"\n{'='*80}")
    print(f"  {name}")
    print(f"  {addr}")
    print(f"{'='*80}")

    df_tx = fetcher.fetch_wallet_transactions_adaptive(addr, min_txs=50, max_txs=500, target_days=90)
    feats = engineer.compute_all_features(df_tx, addr)
    
    print(f"\n  Raw data: {len(df_tx)} txs fetched, {df_tx['is_sender'].sum()} outgoing")

    # ── Dimension scores (0-100 each) ──
    raw_dims = dim_scorer.score_all(feats)
    print(f"\n  Dimension Scores (0-100):")
    for k in sorted(raw_dims.keys()):
        s = raw_dims[k]
        w = dim_scorer.WEIGHTS.get(k, 1.0)
        bar = "#" * int(s // 10) + "." * (10 - int(s // 10))
        excl = " [EXCLUDED weight=0]" if w == 0.0 else ""
        print(f"    {k:25s} {s:5.1f} {bar}{excl}")

    # ── Overall dimension score with boost ──
    dim_boosted, dim_scores = dim_scorer.overall_score(feats, block_time=2.0)
    
    # Manual avg calc for display
    total_w = sum(dim_scorer.WEIGHTS.get(k, 1.0) for k in raw_dims)
    weighted_sum = sum(raw_dims[k] * dim_scorer.WEIGHTS.get(k, 1.0) for k in raw_dims)
    dim_raw_avg = weighted_sum / total_w
    
    # Age boost
    age_log = feats.get("net_3_wallet_age_blocks_log", 0)
    age_sec = (2.718 ** age_log) * 2.0 if age_log > 0 else 0  # exp(log) ≈ age_blocks * block_time(2s)
    age_days = age_sec / 86400
    boost = dim_scorer._wallet_age_boost(feats, block_time=2.0)
    
    dim_hps = int(dim_boosted * 100)
    
    print(f"\n  Dimension Summary:")
    print(f"    Weighted avg (10 active dims): {dim_raw_avg:.2f}/100")
    print(f"    Age: {age_days:.0f} days ({age_days/365:.1f} yr)")
    print(f"    Age boost: x{boost:.4f}")
    print(f"    Boosted avg: {dim_boosted:.2f}/100")
    print(f"    Dim_HPS (boosted_avg x 100): {dim_hps}")

    # ── ML score ──
    X = preprocessor.transform(feats)
    ml_hps = model.score_wallet(X)
    print(f"\n  ML_HPS: {ml_hps}")
    print(f"  ML probability: {ml_hps/10000:.4f}")

    # ── Hybrid ──
    diff = abs(ml_hps - dim_hps)
    print(f"\n  |ML_HPS - Dim_HPS| = |{ml_hps} - {dim_hps}| = {diff}")
    if diff < 1000:
        mw, dw = 0.5, 0.5
        mode = "50/50 (agree)"
    elif diff > 3000:
        mw, dw = 0.2, 0.8
        mode = "20/80 (disagree >3000)"
    else:
        t = (diff - 1000) / 2000.0
        mw = 0.5 - t * 0.3
        dw = 0.5 + t * 0.3
        mode = f"blended ({diff:.0f} diff)"
    
    final = int(round(ml_hps * mw + dim_hps * dw))
    final = max(0, min(10000, final))
    
    print(f"  Hybrid mode: {mode}")
    print(f"  Weights: ML={mw:.4f}  Dim={dw:.4f}")
    print(f"  Final HPS: {final}")
    print(f"  Threshold: 7000")
    print(f"  {'PASS HUMAN' if final >= 7000 else 'FAIL bot-like'} ({final - 7000} from threshold)")

    # ── Top features that hurt them ──
    contributions = model.explain_wallet(X, model.feature_names)
    print(f"\n  Top-10 SHAP contributions (pushing toward BOT):")
    bot_push = [c for c in contributions if c["contribution"] < 0]
    for c in bot_push[:10]:
        print(f"    {c['feature']:35s} {c['value']:>10.4f}  contribution={c['contribution']:+.4f}")
