"""
Deploys a simple agent bot on Mantle Sepolia.
Sends 5 transactions every 30 seconds so you have labeled agent data.
Run this in a separate terminal and let it run for 5-10 minutes.
"""
import sys; sys.path.insert(0, '.')
import os, time
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

w3 = Web3(Web3.HTTPProvider(os.getenv("MANTLE_TESTNET_RPC")))
acct = w3.eth.account.from_key(os.getenv("GHOST_PRIVATE_KEY"))

print(f"Bot address: {acct.address}")
print("Sending 5 tiny transactions every 30 seconds...")
print("Press Ctrl+C to stop after you have enough data.\n")

nonce = w3.eth.get_transaction_count(acct.address)
for i in range(200):
    txs = []
    for _ in range(5):
        tx = {
            "chainId": 5003,
            "from": acct.address,
            "to": "0xDeaDDEaDDeAdDeAdDEAdDEaddeAddEAdDEAd0001",
            "value": w3.to_wei(0.0001, "ether"),
            "gas": 21000,
            "gasPrice": w3.eth.gas_price,
            "nonce": nonce,
        }
        signed = acct.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        txs.append(tx_hash.hex())
        nonce += 1

    print(f"Batch {i+1}: sent {len(txs)} txs — waiting 30s...")
    time.sleep(30)
