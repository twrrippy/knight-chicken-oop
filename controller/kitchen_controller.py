from fastapi import APIRouter, HTTPException
import asyncio
from typing import Annotated
from pydantic import Field
from mcp_core import mcp
from shared.utils.response import success_response_status, error_response_status
from main_system.restaurant import restaurant
router = APIRouter(prefix="/kitchen", tags=["Kitchen"])

@mcp.tool
@router.post("/cook/{order_id}")
async def cook_order(
    token: Annotated[str, Field(
        description="Token ของพนักงาน (ได้จากการเรียกใช้ tool login)"
    )],
    order_id: Annotated[str, Field(
        description="รหัสออเดอร์ที่ต้องการทำอาหาร (Format: ORD-xxx)"
    )]
):
    """
    Start cooking a specific order. Changes the order status to COOKING in the kitchen. 
    """
    try:
        restaurant.verify_token_and_role(token, ["Admin", "Staff"])
        order = restaurant.search_order_from_id(order_id)
        success = order.cook_order()
        if success:
            if order.delivery:
                asyncio.create_task(restaurant.simulate_delivery(order_id))
            return {"message": "Cooking finished. Order is READY.", "status": order.status.value}
        else:
            raise HTTPException(status_code=400, detail=f"Cannot cook order. Current status: {order.status.value}")
    except Exception as e:
        return f"ไม่สามารถดำเนินการได้: {getattr(e, 'detail', str(e))}"
   
@mcp.tool
@router.get("/queue")
async def view_kitchen_queue(
    token: Annotated[str, Field(
        description="Token ของพนักงาน (ได้จากการเรียกใช้ tool login)"
    )]
):
    """
    View the kitchen queue (orders that are ready to be cooked).
    """
    try:
        restaurant.verify_token_and_role(token, ["Admin", "Staff"])
        queue = restaurant.get_kitchen_queue()
        if queue["total_queue"]==0:
            return {"message": "No order in queue ","queue": queue}
        return {"message": "Current queue ","queue": queue}
    except Exception as e:
        return f"ไม่สามารถดำเนินการได้: {getattr(e, 'detail', str(e))}"
    
    