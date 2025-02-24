from ib_insync import IB, Stock, MarketOrder, StopOrder
import math
import threading
from bson import ObjectId
from helper.Ibkr_connection import ensure_connected
from helper.event_loop import ensure_event_loop
from helper.db_connection import trades_collection
from helper.wait import wait_until
from helper.market_data import Market_data
from controllers.utils.exit_trade import exit_trade


# Entry Execution
def enter_trade(ib: IB, action, quantity, contract, symbol, mongo_id):
    entry_order = MarketOrder(action, quantity)
    trade = ib.placeOrder(contract, entry_order)
    print(f"Placed entry order: {action} {quantity} {symbol}")
    
    current_price = Market_data(ib, contract, symbol)
    
    if math.isnan(current_price):
        current_price = 245
        # return 0
    while trade.orderStatus.orderId == 0:
        ib.sleep(1)
    parent_order_id = trade.orderStatus.orderId

    print(f"Entry order acknowledged with orderId: {parent_order_id}")
    trades_collection.update_one({"_id": ObjectId(mongo_id)},
                                    {"$set": {"entryOrderId": parent_order_id, "entry_price": current_price,
                                            "status": "Entry Placed"}})
    
    return current_price

# Calculating Stop and placing
def place_stoploss(ib: IB, action, quantity, current_price, contract, stop_loss_ticks, mongo_id):
    if action.upper() == "BUY":
        stop_loss_price = current_price - (stop_loss_ticks * 0.01)
    else:
        stop_loss_price = current_price + (stop_loss_ticks * 0.01)
    
    print(f"Calculated stop-loss price: {stop_loss_price}")
    stop_order = StopOrder('SELL' if action.upper() == "BUY" else 'BUY', quantity, stop_loss_price)
    stop_order_placed = ib.placeOrder(contract, stop_order)
    
    # Serialize stop-loss order (extract relevant fields)
    stop_order_data = {
        "orderId": stop_order.orderId,
        "clientId": stop_order.clientId,
        "action": stop_order.action,
        "totalQuantity": stop_order.totalQuantity,
        "auxPrice": stop_loss_price
    }

    print(f"Stop-loss order placed for: {stop_order_placed}")
    trades_collection.update_one({"_id": ObjectId(mongo_id)},
                                {"$set": {"stop_loss_order_placed": True,
                                "stop_loss_price": stop_loss_price, "stopLossOrder": stop_order_data }})

# Route Function.
def place_order(ib: IB, symbol, action, quantity, entry_time, exit_time, stop_loss_ticks):
    try:
        ensure_event_loop() 
        

        print(f"Order received. Entry time: {entry_time}, Exit time: {exit_time}")

        # Create an initial trade record (status "Waiting for Entry")
        pending_record = {
            "entryOrderId": None,
            "exitOrderId": None,
            "stopLossOrder": {},
            "symbol": symbol,
            "action": action,
            "quantity": quantity,
            "entry_time": entry_time.strftime('%Y-%m-%d %H:%M:%S'),
            "exit_time": exit_time.strftime('%Y-%m-%d %H:%M:%S'),
            "stop_loss_ticks": stop_loss_ticks,
            "entry_price": None,
            "stop_loss_order_placed": False,
            "StopLossExecuted": False, 
            "stop_loss_price": None,
            "exit_price": None,
            "status": "Waiting for Entry",
            "cancel_requested": False
        }

        # Insert pending record; obtain its _id as a string (our cancel key).
        result = trades_collection.insert_one(pending_record)
        mongo_id = str(result.inserted_id)
        print("Stored pending trade record with mongo_id:", mongo_id)

        # Wait until Entry Time
        if not wait_until(entry_time, mongo_id):
            print("Order cancelled before entry time.")
            trades_collection.update_one({"_id": ObjectId(mongo_id)},
                                         {"$set": {"status": "Cancelled"}})
            return

        print(f"\n WAIT ENDED {entry_time}...\n")

        ensure_connected(ib, clientId=0)
        
        contract = Stock(symbol, 'SMART', 'USD')
        print("contract: ", contract)
        qualified = ib.qualifyContracts(contract)

        print("Qualification of Stock (0 if not): ", len(qualified))
        if len(qualified) == 0:
            trades_collection.update_one({"_id": ObjectId(mongo_id)},
                                         {"$set": {"status": "Stock Not Qualified"}})
            return
        #Execute trade time reached.
        current_price = enter_trade(ib, action, quantity, contract, symbol, mongo_id)

        #Calculating Stop loss and placing it.
        place_stoploss(ib, action, quantity, current_price, contract, stop_loss_ticks, mongo_id)


        
        if not wait_until(exit_time, mongo_id):
            print("Order cancelled before entry time.")
            trades_collection.update_one({"_id": ObjectId(mongo_id)},
                                        {"$set": {"status": "Cancelled"}})

        exit_trade(ib, mongo_id, quantity, action, symbol, contract)


    except Exception as e:
        print("Error placing order:", e)

    finally:
        # ib.disconnect()
        print("Main IBKR.")
