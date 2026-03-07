from fastapi import APIRouter, HTTPException
from shared.utils.response import success_response_status, error_response_status
from main_system.restaurant import restaurant
from typing import Annotated
from pydantic import Field
from mcp_core import mcp

router = APIRouter(prefix="/kitchen", tags=["Kitchen"])

@mcp.tool
@router.post("/cook/{order_id}")
async def cook_order(
    order_id: Annotated[str, Field(
        description="รหัสออเดอร์ที่ต้องการเริ่มทำอาหาร (Format: ORD-xxx-xxx)"
    )]
):
    """
    Start cooking a specific order. Changes the order status to COOKING in the kitchen.
    """
    try:
        order = restaurant.search_order_from_id(order_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=(str(e)))
    success = order.cook_order()
    if success:
        return {"message": "Cooking finished. Order is READY.", "status": order.status.value}
    else:
        raise HTTPException(status_code=400, detail=f"Cannot cook order. Current status: {order.status.value}")

# มี api อีกเส้นไหม เอาไว้ดูว่ามีออเดอร์ไหนอยู่ในคิวบ้าง (ที่จ่ายเงินแล้ว)