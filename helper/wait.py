from helper.db_connection import trades_collection
from datetime import datetime, timezone
from bson import ObjectId
import time

def wait_until(target_time: datetime, mongo_id) -> bool:
    target_time = target_time.astimezone(timezone.utc)  # Convert to UTC
    print("Waiting until (UTC):", target_time)

    while datetime.now(timezone.utc) < target_time:
        trade_record = trades_collection.find_one({"_id": ObjectId(mongo_id)})
        print("Current UTC time:", datetime.now(timezone.utc))

        if trade_record and trade_record.get("cancel_requested"):
            print(f"Trade {mongo_id} was canceled at {datetime.now(timezone.utc)}.")
            return False  # Stop waiting, trade was canceled

        time.sleep(1)

    return True
