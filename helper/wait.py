from helper.db_connection import trades_collection
from datetime import datetime
from bson import ObjectId
import time
import asyncio

def wait_until(target_time: datetime, mongo_id) -> bool:
    print("Waiting until:", target_time)
    trade_record = trades_collection.find_one({"_id": ObjectId(mongo_id)})
    while datetime.now() < target_time:
        # print("Current time: ", datetime.now())
        if trade_record and trade_record.get("cancel_requested"):
            print(f"Trade {mongo_id} was canceled.")
            return False  # Stop waiting, trade was canceled
        time.sleep(1)
    return True