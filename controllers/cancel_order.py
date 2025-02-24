from helper.db_connection import trades_collection 
from controllers.utils.exit_trade import exit_trade
from helper.Ibkr_connection import ensure_connected
from helper.event_loop import ensure_event_loop
from datetime import datetime
from bson import ObjectId
from ib_insync import IB, Stock

def cancel_order_by_mongo_id(ib: IB, mongo_id: str):

    try:
        trade_record = trades_collection.find_one({"_id": ObjectId(mongo_id)})
        if not trade_record:
            print(f"No record found for {mongo_id}")
            return 
        
        
        # Entery is not executed yet
        if trade_record.get("entryOrderId") is None:
            print("All Scheduled Trades Cancelled")
            trades_collection.update_one({"_id": ObjectId(mongo_id)},
                {"$set": {"cancel_requested": True, "status": "Cancelled"}})
            return
        
        ensure_event_loop()
        ensure_connected(ib, 0)

        contract = Stock(trade_record['symbol'], 'SMART', 'USD')
        exit_trade(
            ib, 
            mongo_id, 
            trade_record['quantity'], 
            trade_record['action'], 
            trade_record['symbol'], 
            contract
        )
        
        exit_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # Set cancellation flag in DB - Exit entry placed immediatley
        trades_collection.update_one({"_id": ObjectId(mongo_id)},
                                    {"$set": {"cancel_requested": True, "exit_time": exit_time }}
        )
    
    except Exception as e:
        print(f"Error Cancelling trade: {e}")
        trades_collection.update_one({"_id": ObjectId(mongo_id)},
                                    {"$set": { "status": "Cancellation Failed"}})

        


