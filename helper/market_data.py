from ib_insync import IB
from helper.Ibkr_connection import ensure_connected
import math

ib_market = IB()

def Market_data(ib: IB, contract, symbol):
    ensure_connected(ib_market, 1)
    # Subscribe to market data with a snapshot
    market_data = ib_market.reqMktData(contract, snapshot=True)
    print(f"Fetching market data for {market_data}")

    # Wait for market data to update
    timeout = 10 
    elapsed = 0

    while not market_data.last and elapsed < timeout:
        ib_market.sleep(1)
        ib_market.pendingTickers()  # Refresh tickers
        elapsed += 1
        print("Waiting for market data...")

    if not market_data.last:
        print(f"Warning: Market data for {symbol} is unavailable or delayed.")
        return None
    
    if math.isnan(market_data.last):
        print(f"Market is not Live, or subscription is expired. ")

    current_price = market_data.last
    print(f"Current price of {symbol}: {current_price}")

    return current_price
