from ib_insync import IB
import os
from dotenv import load_dotenv
from itertools import count

# Load environment variables from .env file
load_dotenv()

# Get IBKR connection parameters
port = os.getenv("PORT")  # Use default IBKR TWS port
ibkr_api = str(os.getenv("IBKR_API"))

clientId_counter = count(2)

def ensure_connected(ib_instance: IB, clientId=0):
    try:
        print("ib_instance: ", ib_instance)
        if not ib_instance.isConnected():
            try:
                cid = next(clientId_counter)
                ib_instance.connect(ibkr_api, port, clientId=cid)
                print(f"Connected to IBKR (Client ID: {cid}) at {ib_instance.reqCurrentTime()}")
            except Exception as e:
                print(f"Error connecting to IBKR: {e}")
                raise
        else:
            print(f"Already Connected to IBKR..)")

    except Exception as e:
        print(f"Error IN API: {e}")

def disconnect_from_ibkr(ib_instance: IB):
    try:
        ib_instance.disconnect()
        print(f"{ib_instance} Disconnected from IBKR.")
    except Exception as e:
        print(f"Error disconnecting from IBKR: {e}")
