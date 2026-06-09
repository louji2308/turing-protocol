from web3 import Web3
from dotenv import load_dotenv
import os

load_dotenv()

rpc = os.getenv("MANTLE_TESTNET_RPC")
w3 = Web3(Web3.HTTPProvider(rpc))

if w3.is_connected():
    block = w3.eth.block_number
    print(f"✅ Connected to Mantle Testnet")
    print(f"   Chain ID: {w3.eth.chain_id}")
    print(f"   Latest Block: {block}")
else:
    print("❌ Connection failed. Check your RPC URL.")