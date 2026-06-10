"""
Finds real bot wallets on Mantle Sepolia using the Etherscan API.
Much faster than RPC block scanning.

Usage:
  python find_bots_fast.py
"""
import sys; sys.path.insert(0, '.')
import os, json, time
import requests
from pathlib import Path
from collections import Counter
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("ETHERSCAN_API_KEY", "").strip()
CHAIN_ID = 5003

# Known contracts on Mantle Sepolia (from mantle_fetcher.py)
CONTRACTS = [
    "0xeaEE7EE68874218c3558b40063c42B82D3E7232a",  # Merchant Moe router
    "0xa6630671775c4EA2743840F9A5016dCf2A104054",  # Merchant Moe factory
    "0x5c0d2247F93c6901f782Ca7fFB1B0E3df6aBb53f",  # Agni pool
    "0xe6829d9a7eE3040e1276Fa75293Bde931859e8fA",  # mETH staking
]

def fetch_txs(address, max_pages=3):
    all_txs = []
    for page in range(1, max_pages + 1):
        params = {
            "chainid": CHAIN_ID, "module": "account", "action": "txlist",
            "address": address, "startblock": 0, "endblock": "latest",
            "page": page, "offset": 50, "sort": "asc", "apikey": API_KEY,
        }
        try:
            r = requests.get("https://api.etherscan.io/v2/api", params=params, timeout=15)
            if r.status_code != 200: break
            data = r.json()
            if data.get("status") != "1": break
            results = data.get("result", [])
            if not results: break
            all_txs.extend(results)
            if len(results) < 50: break
        except: break
        time.sleep(0.2)
    return all_txs

# Find senders
print("Fetching transactions from known contracts...")
senders = Counter()
for contract in CONTRACTS:
    txs = fetch_txs(contract, max_pages=2)
    for tx in txs:
        if tx.get("from"):
            senders[tx["from"].lower()] += 1
    print(f"  {contract[:10]}... → {len(txs)} txs, {len(senders)} unique senders so far")

# Filter: wallets with frequent interactions
bot_candidates = [(addr, count) for addr, count in senders.items() if count >= 3]
bot_candidates.sort(key=lambda x: -x[1])

print(f"\nBot candidates (≥3 interactions): {len(bot_candidates)}")
print(f"\n{'Rank':<5} {'Address':<45} {'TX Count':<10}")
print("-" * 60)
for i, (addr, count) in enumerate(bot_candidates[:20], 1):
    print(f"{i:<5} {addr:<45} {count:<10}")

# Save
out = Path("interrogator/data/bot_candidates.json")
out.parent.mkdir(parents=True, exist_ok=True)
with open(out, "w") as f:
    json.dump({"candidates": [{"address": a, "tx_count": c} for a, c in bot_candidates[:30]]}, f, indent=2)
print(f"\nSaved to {out}")
