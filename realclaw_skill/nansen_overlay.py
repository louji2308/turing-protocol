import os
import httpx

NANSEN_API_KEY = os.environ.get("NANSEN_API_KEY")
NANSEN_BASE = "https://api.nansen.ai/v1"


def enrich_with_nansen(address: str) -> dict:
    if not NANSEN_API_KEY:
        return {"available": False, "reason": "NANSEN_API_KEY not configured"}

    try:
        resp = httpx.get(
            f"{NANSEN_BASE}/profiler/address/{address}/labels",
            headers={"X-API-Key": NANSEN_API_KEY},
            params={"chain": "mantle"},
            timeout=6.0,
        )
        if resp.status_code != 200:
            return {"available": False, "reason": f"nansen_http_{resp.status_code}"}
        data = resp.json()
        labels = data.get("labels", [])
        return {
            "available": True,
            "labels": labels,
            "is_smart_money": any("Smart" in l for l in labels),
            "is_known_entity": bool(labels),
        }
    except httpx.HTTPError as e:
        return {"available": False, "reason": str(e)}
