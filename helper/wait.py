from helper.db_connection import trades_collection
from datetime import datetime, timezone
from bson import ObjectId
import time
import pytz

def wait_until(target_time: datetime, mongo_id) -> bool:
    est = pytz.timezone("America/New_York")
    utc = pytz.utc

    if target_time.tzinfo is None:
        target_time = est.localize(target_time)  # Convert naive EST time to timezone-aware
        target_time = target_time.astimezone(utc)  # Convert to UTC


    print("Waiting until (UTC):", target_time)
    print("Current time (UTC):", datetime.now(pytz.utc))

    while datetime.now(pytz.utc) < target_time:
        trade_record = trades_collection.find_one({"_id": ObjectId(mongo_id)})
        print("Current time:", datetime.now(pytz.utc))

        if trade_record and trade_record.get("cancel_requested"):
            print(f"Trade {mongo_id} was canceled at {datetime.now(timezone.utc)}.")
            return False  # Stop waiting, trade was canceled

        time.sleep(1)

    return True
