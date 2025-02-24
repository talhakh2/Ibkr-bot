from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from datetime import datetime
from ib_insync import IB
from controllers.place_order import place_order
import os
import uvicorn
import helper.db_connection as db_connection 
from controllers.cancel_order import cancel_order_by_mongo_id

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
@app.get("/api/check")
def read_root():
    return {"message": "Hello! from IBKR-BOT"}

@app.post("/api/place_order")
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


@app.post("/api/cancel_order")
def cancel_order_endpoint(cancel_req: CancelOrderRequest):
    try:
        cancel_order_by_mongo_id(ib, cancel_req.mongo_id)
        return {"message": "Order cancelled"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

if __name__ == "__main__":
    app_port = int(os.environ.get("APP_PORT"))  # Use PORT from env, default to 8000
    uvicorn.run(app, host="0.0.0.0", port=app_port)