TIERS = {
    "lenient": 3000,
    "standard": 7000,
    "strict": 8000,
}

TIER_DESCRIPTIONS = {
    "lenient": "likely human, unverified",
    "standard": "ProofOfBehavior mint bar",
    "strict": "high-confidence human band",
}


def resolve_tier(threshold: int | None, tier: str | None) -> int:
    if threshold is not None and tier is not None:
        tier_val = TIERS.get(tier)
        if tier_val is not None and threshold != tier_val:
            raise ValueError(
                f"Conflicting trust spec: threshold={threshold} AND tier={tier!r} "
                f"(resolves to {tier_val}). Specify exactly one."
            )
        return threshold

    if tier is not None:
        if tier not in TIERS:
            raise ValueError(
                f"Unknown tier {tier!r}. Valid tiers: {', '.join(TIERS)}"
            )
        return TIERS[tier]

    return threshold if threshold is not None else TIERS["standard"]


class TrustDecision:
    def __init__(
        self,
        score_data: dict,
        threshold: int,
        require_fresh_proof: bool = False,
        fresh_proof_status: bool | None = None,
    ):
        self.score_data = score_data
        self.threshold = threshold
        self.require_fresh_proof = require_fresh_proof
        self.fresh_proof_status = fresh_proof_status

    def evaluate(self) -> dict:
        hps = self.score_data.get("hps")
        confidence = self.score_data.get("confidence", "unknown")
        source = self.score_data.get("source")
        uncertainty = self.score_data.get("uncertainty")

        if hps is None or source == "error":
            return self._result(
                trusted=False,
                recommendation="insufficient_data",
                uncertainty=uncertainty,
            )

        if self.require_fresh_proof:
            fresh = self.fresh_proof_status
            if fresh is not None and not fresh:
                return self._result(
                    trusted=False,
                    recommendation="reject",
                    uncertainty=uncertainty,
                )

        trusted = hps >= self.threshold

        if not trusted:
            if confidence == "low":
                rec = "insufficient_data"
            else:
                rec = "reject"
        elif confidence == "low" or (uncertainty is not None and uncertainty > 1500):
            rec = "proceed_with_caution"
        else:
            rec = "proceed"

        return self._result(
            trusted=trusted,
            recommendation=rec,
            uncertainty=uncertainty,
        )

    def _result(self, trusted: bool, recommendation: str, uncertainty=None) -> dict:
        base = dict(self.score_data)
        base.pop("error", None)
        return {
            **base,
            "tier_required": self.threshold,
            "trusted": trusted,
            "confidence": self.score_data.get("confidence", "unknown"),
            "uncertainty": uncertainty,
            "recommendation": recommendation,
        }
