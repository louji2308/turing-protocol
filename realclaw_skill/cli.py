import json
import sys
import os

import click

from .resolver import ScoreResolver, resolve_with_cold_start
from .decision import TrustDecision, resolve_tier, TIERS
from .narrative import build_narrative

EXIT_PROCEED = 0
EXIT_REJECT = 1
EXIT_INSUFFICIENT = 2
EXIT_ERROR = 3


@click.group()
def cli():
    """Turing Trust Layer — RealClaw Skill CLI.

    Behavioural proof-of-humanity trust gate for Mantle wallets.
    Given a wallet address, returns a Human Probability Score (0-10000),
    a trust/no-trust decision, and an optional plain-English explanation.
    """


@cli.command()
@click.argument("address")
@click.option("--threshold", type=int, default=None, help="Raw HPS threshold (0-10000).")
@click.option("--tier", type=str, default=None, help="Named tier: lenient | standard | strict.")
@click.option(
    "--require-fresh-proof",
    is_flag=True,
    help="Require a non-stale ProofOfBehavior NFT.",
)
@click.option("--explain", is_flag=True, help="Include a plain-English narrative.")
@click.option(
    "--enrich",
    is_flag=True,
    help="Include Nansen entity reputation overlay (Phase 2).",
)
@click.option(
    "--wait-for-score",
    is_flag=True,
    help="Block up to ~20s to score an unscored wallet.",
)
def check(address, threshold, tier, require_fresh_proof, explain, enrich, wait_for_score):
    """Check whether ADDRESS clears a trust threshold."""
    try:
        thr = resolve_tier(threshold, tier)
    except ValueError as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(EXIT_ERROR)

    resolver = ScoreResolver()
    score_data = resolve_with_cold_start(resolver, address, wait=wait_for_score)

    fresh_proof_status = None
    if require_fresh_proof:
        pob_addr = os.getenv("PROOF_OF_BEHAVIOR_ADDRESS")
        fresh_proof_status = resolver.resolve_with_fresh_proof(address, pob_addr)

    decision = TrustDecision(
        score_data, thr, require_fresh_proof=require_fresh_proof,
        fresh_proof_status=fresh_proof_status,
    ).evaluate()

    out = dict(decision)
    if explain:
        out["narrative"] = build_narrative(score_data, decision)
    if enrich:
        try:
            from .nansen_overlay import enrich_with_nansen
            out["nansen"] = enrich_with_nansen(address)
        except Exception as e:
            out["nansen"] = {"available": False, "reason": str(e)}

    click.echo(json.dumps(out, indent=2, default=str))

    if out["recommendation"] == "proceed":
        sys.exit(EXIT_PROCEED)
    elif out["recommendation"] == "reject":
        sys.exit(EXIT_REJECT)
    else:
        sys.exit(EXIT_INSUFFICIENT)


@cli.command()
@click.option("--me", required=True, help="Your agent's wallet address.")
@click.option("--counterparty", required=True, help="The counterparty's wallet address.")
@click.option("--tier", default="standard", help="Named tier: lenient | standard | strict.")
@click.option("--threshold", type=int, default=None, help="Raw HPS threshold override.")
def handshake(me, counterparty, tier, threshold):
    """Mutual trust handshake before a trade between two agents.

    Returns min(HPS_a, HPS_b) as deal_confidence — trust is only as strong
    as the weakest counterparty.
    """
    try:
        thr = resolve_tier(threshold, tier)
    except ValueError as e:
        click.echo(json.dumps({"error": str(e)}), err=True)
        sys.exit(EXIT_ERROR)

    resolver = ScoreResolver()
    a = resolver.resolve(me)
    b = resolver.resolve(counterparty)

    hps_a = a.get("hps") or 0
    hps_b = b.get("hps") or 0
    deal_confidence = min(hps_a, hps_b)

    if deal_confidence >= thr:
        rec, frac, slip_delta = "proceed", 1.0, 0
    elif deal_confidence >= thr * 0.7:
        rec, frac, slip_delta = "proceed_with_caution", 0.5, 25
    else:
        rec, frac, slip_delta = "reject", 0.0, 0

    result = {
        "address_a": me,
        "address_b": counterparty,
        "hps_a": hps_a,
        "hps_b": hps_b,
        "deal_confidence": deal_confidence,
        "tier": tier,
        "threshold": thr,
        "recommendation": rec,
        "suggested_adjustments": {
            "max_trade_fraction_of_normal": frac,
            "slippage_tolerance_bps_delta": slip_delta,
        },
    }

    click.echo(json.dumps(result, indent=2))

    if rec == "proceed":
        sys.exit(EXIT_PROCEED)
    elif rec == "reject":
        sys.exit(EXIT_REJECT)
    else:
        sys.exit(EXIT_INSUFFICIENT)


@cli.command(name="self-audit")
@click.option(
    "--addresses-file",
    type=click.Path(exists=True),
    required=True,
    help="Path to file with one wallet address per line.",
)
def self_audit(addresses_file):
    """Audit a fleet of agent wallets for Sybil-cluster signatures.

    Detects wallets with low HPS, weak funding_source/transaction_graph
    dimensions, and computes an overall cluster risk score.
    """
    resolver = ScoreResolver()
    with open(addresses_file) as f:
        addresses = [line.strip() for line in f if line.strip()]

    scores: list[int] = []
    flagged: list[dict] = []
    funding_scores: list[int] = []

    for addr in addresses:
        data = resolver.resolve(addr)
        hps = data.get("hps") or 0
        scores.append(hps)
        dims = data.get("dimension_scores") or {}
        if isinstance(dims, dict):
            weak = [
                k
                for k, v in dims.items()
                if v is not None and v < 30
                and k not in ("ip_fingerprint", "cross_chain")
            ]
            fs = dims.get("funding_source")
            if fs is not None:
                funding_scores.append(fs)
        else:
            weak = []

        if hps < 5000 or weak:
            flagged.append({
                "address": addr,
                "hps": hps,
                "weak_dims": weak,
            })

    mean_hps = round(sum(scores) / len(scores), 1) if scores else 0

    if funding_scores:
        mean_funding = sum(funding_scores) / len(funding_scores)
        hhi = sum((1 / len(funding_scores)) ** 2 for _ in funding_scores) * 10000
        if mean_funding < 30 and len(flagged) > len(addresses) / 3:
            cluster_risk = "high"
        elif mean_funding < 50 or len(flagged) > len(addresses) / 2:
            cluster_risk = "moderate"
        else:
            cluster_risk = "low"
    else:
        cluster_risk = "moderate" if flagged else "low"

    rec = (
        "Run NetworkTopologyModule-style EOA peer transfers and diversify "
        "funding sources for flagged wallets."
        if flagged
        else "Fleet looks behaviourally diverse."
    )

    click.echo(json.dumps({
        "fleet_size": len(addresses),
        "mean_hps": mean_hps,
        "flagged_wallets": flagged,
        "cluster_risk": cluster_risk,
        "recommendation": rec,
    }, indent=2))


if __name__ == "__main__":
    cli()
