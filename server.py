from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from datetime import datetime
from ib_insync import IB, ExecutionFilter
from controllers.place_order import place_order
import os
import uvicorn
from helper.db_connection import trades_collection
from helper.Ibkr_connection import ensure_connected, disconnect_from_ibkr
from controllers.cancel_order import cancel_order_by_mongo_id
from helper.event_loop import ensure_event_loop

app = FastAPI()
ib = IB()

# -----------------------------
# Data Models for Endpoints
# -----------------------------
class OrderDetails(BaseModel):
    symbol: str
    action: str
    quantity: int
    entry_time: datetime  # ISO-formatted string expected
    exit_time: datetime   # ISO-formatted string expected
    stop_loss_ticks: int

class CancelOrderRequest(BaseModel):
    mongo_id: str  # MongoDB record ID for the pending order


# -----------------------------
# API Endpoints
# -----------------------------
@app.get("/check")
def read_root():
    return {"message": "Hello! from IBKR-BOT"}


@app.post("/place_order")
async def place_order_endpoint(order: OrderDetails, background_tasks: BackgroundTasks):
    try:
        background_tasks.add_task(
            place_order,
            ib,
            order.symbol,
            order.action,
            order.quantity,
            order.entry_time,
            order.exit_time,
            order.stop_loss_ticks,
        )
        return {"message": "Order processing started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/cancel_order")
def cancel_order_endpoint(cancel_req: CancelOrderRequest):
    try:
        cancel_order_by_mongo_id(ib, cancel_req.mongo_id)
        return {"message": "Order cancelled"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/orders")
def get_orders():
    try:
        orders = list(trades_collection.find({"entryOrderId": {"$exists": True}}))
        ensure_event_loop()
        ensure_connected(ib, 1)
        # Example usage
        exec_filter = ExecutionFilter()
        executions = ib.reqExecutions(exec_filter)

        for order in orders:
            # Extract order IDs
            entry_id = order.get("entryOrderId")
            exit_id = order.get("exitOrderId")
            stop_id = order.get("stopLossOrder", {}).get("orderId") or ""

            # Initialize updated values
            updated_entry_price = None
            updated_exit_price = None
            updated_stop_loss_price = None

            # Loop through executions to find matching orders
            for fill in executions:
                order_id = fill.execution.orderId
                price = fill.execution.price

                if order_id == entry_id:
                    updated_entry_price = price
                elif order_id == exit_id:
                    updated_exit_price = price
                elif order_id == stop_id:
                    updated_stop_loss_price = price

            # Apply updates only if values were found
            if updated_entry_price is not None:
                order["entry_price"] = round(updated_entry_price, 2)
            if updated_exit_price is not None:
                order["exit_price"] = round(updated_exit_price, 2)
            if updated_stop_loss_price is not None:
                order["stop_loss_price"] = round(updated_stop_loss_price, 2)
                order["status"] = "Stop Executed"
                order["StopLossExecuted"] = True

        for order in orders:
            order["_id"] = str(order["_id"])

        return orders
    except Exception as e:
        print("ex: ", e)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        print("ib_order disconnected")
        disconnect_from_ibkr(ib)

if __name__ == "__main__":
    app_port = int(os.environ.get("APP_PORT"))  # Use PORT from env, default to 8000
    uvicorn.run(app, host="0.0.0.0", port=app_port)