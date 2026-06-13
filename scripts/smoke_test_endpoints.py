"""
Smoke test for all API endpoints. Run against a live oracle service.
Usage: python scripts/smoke_test_endpoints.py --base-url https://turing-oracle.onrender.com
"""

import argparse
import requests
import json
import sys
import time

BASE = "http://localhost:8080"
TIMEOUT = 15
SAMPLE_WALLET = "0x0000000000000000000000000000000000000001"
SAMPLE_PROTOCOL = "0x319B69888b0d11cEC22caA5034e25FfFBDc88421"


def test_endpoint(name: str, method: str, path: str, expected: int = 200,
                  body: dict = None, skip_on_4xx: bool = False) -> bool:
    url = f"{BASE}{path}"
    try:
        if method == "GET":
            r = requests.get(url, timeout=TIMEOUT)
        elif method == "POST":
            r = requests.post(url, json=body or {}, timeout=TIMEOUT)
        else:
            print(f"  SKIP {name}: unknown method {method}")
            return False

        ok = r.status_code == expected
        if skip_on_4xx and 400 <= r.status_code < 500:
            ok = True
        status = "PASS" if ok else f"FAIL (expected {expected}, got {r.status_code})"
        detail = ""
        if not ok:
            try:
                detail = f" — {r.json().get('detail', r.text[:100])}"
            except Exception:
                detail = f" — {r.text[:100]}"
        print(f"  {status:>6} {method:>4} {path}{detail}")
        return ok
    except requests.exceptions.RequestException as e:
        print(f"  FAIL  {method} {path} — connection error: {e}")
        return False


def main():
    global BASE
    parser = argparse.ArgumentParser(description="Smoke test all API endpoints")
    parser.add_argument("--base-url", default=BASE, help="Base URL of the oracle service")
    args = parser.parse_args()
    BASE = args.base_url.rstrip("/")

    print(f"\n=== Turing Protocol Endpoint Smoke Test ===\n")
    print(f"Target: {BASE}\n")

    results = []

    # Existing endpoints
    results.append(test_endpoint("Health", "GET", "/health"))
    results.append(test_endpoint("Score (invalid)", "GET", f"/score/invalid", expected=422))
    results.append(test_endpoint("Score (valid)", "GET", f"/score/{SAMPLE_WALLET}", skip_on_4xx=True))
    results.append(test_endpoint("Leaderboard", "GET", "/leaderboard"))
    results.append(test_endpoint("Stats", "GET", "/stats"))
    results.append(test_endpoint("Ghost telemetry", "GET", "/ghost/telemetry", skip_on_4xx=True))

    # Admin endpoints
    results.append(test_endpoint("Admin score status", "GET", "/admin/score-loop/status", expected=401))

    # Intelligence Layer - §3
    results.append(test_endpoint("Protocol PHS list", "GET", "/api/v1/intelligence/protocols", skip_on_4xx=True))
    results.append(test_endpoint("Protocol health detail", "GET",
                                  f"/api/v1/intelligence/protocols/{SAMPLE_PROTOCOL}/health", skip_on_4xx=True))
    results.append(test_endpoint("Protocol holders", "GET",
                                  f"/api/v1/intelligence/protocols/{SAMPLE_PROTOCOL}/holders", skip_on_4xx=True))
    results.append(test_endpoint("Smart money flows", "GET", "/api/v1/intelligence/smart-money/flows?days=14",
                                  skip_on_4xx=True))
    results.append(test_endpoint("Smart money wallets", "GET", "/api/v1/intelligence/smart-money/wallets?limit=10",
                                  skip_on_4xx=True))
    results.append(test_endpoint("Smart money alerts", "GET", "/api/v1/intelligence/smart-money/alerts"))
    results.append(test_endpoint("Emerging protocols", "GET", "/api/v1/intelligence/emerging?days=7", skip_on_4xx=True))
    results.append(test_endpoint("Airdrop exposure", "POST", "/api/v1/intelligence/airdrop-exposure",
                                  body={"protocol_address": SAMPLE_PROTOCOL}, skip_on_4xx=True))

    # Sybil - §5
    results.append(test_endpoint("Sybil clusters list", "GET", "/api/v1/intelligence/sybil-clusters", skip_on_4xx=True))
    results.append(test_endpoint("Sybil wallet check", "GET",
                                  f"/api/v1/intelligence/sybil-clusters/address/{SAMPLE_WALLET}"))

    passed = sum(results)
    total = len(results)
    print(f"\n=== Results: {passed}/{total} passed ===")
    if passed < total:
        print(f"FAILURES: {total - passed} endpoint(s) failed")
        sys.exit(1)
    print("ALL ENDPOINTS PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()
