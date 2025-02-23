from bson import ObjectId
from ib_insync import IB, StopOrder, MarketOrder
from helper.db_connection import trades_collection
from helper.market_data import Market_data

# Checking if stop is already executed
def cancel_stop(ib: IB, mongo_id):
    # Retrieve stop-loss price from DB
    trade_record = trades_collection.find_one({"_id": ObjectId(mongo_id)})
    if trade_record and trade_record.get("stopLossOrder") is not None:
        
        stop_loss_order_data = trade_record.get("stopLossOrder")

        # Deserialize the StopOrder from the stored dictionary
        stop_loss_order = StopOrder(
            orderId=stop_loss_order_data.get("orderId"),
            clientId=stop_loss_order_data.get("clientId"),
            action=stop_loss_order_data.get("action"),
            totalQuantity=stop_loss_order_data.get("totalQuantity"),
            stopPrice=trade_record.get("stop_loss_price")
        )

        # Checking if stop order is stil open - 
        # if yes than it means stop loss is not executed yet
        open_orders = ib.openOrders()
        for open_order in open_orders:
            if open_order.orderId == stop_loss_order_data.get("orderId"):
                print("StopOrder is still Open with ID: ", open_order.orderId, "and",
                    stop_loss_order_data.get("orderId"))
                stop_order_open = True
                break
            
        # Exit the trade if stoploss trade is not executed till exit time.
        # else if stop loss is executed than execute exit trade
        if stop_order_open and stop_order_open == True:
            print("Canceling StopLoss trade, and executing exit ")
            ib.cancelOrder(stop_loss_order)   
            ib.sleep(2)
            return True
        else:
            print("StopLoss was executed. Not executing exit now.")
            trades_collection.update_one({"_id": ObjectId(mongo_id)},
                                {"$set": {"exit_price": trade_record.get("stop_loss_price"),
                                        "status": "Stop Executed", "StopLossExecuted": True, 
                                        "exitOrderId": stop_loss_order_data.get("orderId")}})
            return False
    else:
        print("Data for the trade is not in database. Cannot determine exit condition.")
        trades_collection.update_one({"_id": ObjectId(mongo_id)},
                                {"$set": {"status": "Exit failed"}})
        return False
    
# Exit Execution - If stop is not already executed.
def exit_trade(ib: IB, mongo_id, quantity, action, symbol, contract):      
    try:
        
        # if Stop order was opened and got canceled 
        if cancel_stop(ib, mongo_id):

            # Place exit order if condition met.
            exit_order = MarketOrder('SELL' if action.upper() == "BUY" else 'BUY', quantity)
            exit_trade = ib.placeOrder(contract, exit_order)
            print(f"Placed exit order for {symbol}")

            # Fetch market price to calculate stop loss price
            exit_price = Market_data(ib, contract, symbol)

            while exit_trade.orderStatus.orderId == 0:
                ib.sleep(1)
            
            exit_order_id = exit_trade.orderStatus.orderId

            print(f"Exit order acknowledged with orderId: {exit_order_id}")
            trades_collection.update_one({"_id": ObjectId(mongo_id)},
                                            {"$set": {"exitOrderId": exit_order_id,
                                                    "exit_price": exit_price,
                                                    "status": "Exit Executed"}})
    except Exception as e:
        print("Error in exit_thread:", e)
    finally:
        print("Exit ended")

    