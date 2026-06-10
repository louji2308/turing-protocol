import sys
sys.path.insert(0, '.')

from data_pipeline.mantle_fetcher import MantleDataFetcher
from dotenv import load_dotenv
import os

load_dotenv()

rpc = os.getenv('MANTLE_TESTNET_RPC')
fetcher = MantleDataFetcher(rpc)

test_address = '0x31f692c240dEf9300a824C4b28dfE056584dB305'

df = fetcher.fetch_wallet_transactions(test_address, max_txs=50)

print(f'Rows fetched: {len(df)}')
print(f'Columns: {list(df.columns)}')

if len(df) == 0:
    print('No transactions returned from explorer.')
else:
    print(f'Date range: {df["timestamp"].min()} to {df["timestamp"].max()}')
    print(f'Is sender rows: {df["is_sender"].sum()}')
    print(f'Known protocol rows: {df["is_known_protocol"].sum()}')
    print(f'Missing time_since_prev_tx: {df["time_since_prev_tx"].isna().sum()}')