from fastapi import APIRouter, HTTPException
from typing import Annotated
from pydantic import Field
from mcp_core import mcp
from shared.utils.response import success_response_status, error_response_status
from main_system.restaurant import restaurant
router = APIRouter(prefix="/kitchen", tags=["Kitchen"])

@mcp.tool
@router.post("/cook/{order_id}")
async def cook_order(
    order_id: Annotated[str, Field(
        description="รหัสออเดอร์ที่ต้องการทำอาหาร (Format: ORD-xxx)"
    )]
):
    """
    Start cooking a specific order. Changes the order status to COOKING in the kitchen.
    """
    try:
        order = restaurant.search_order_from_id(order_id)
        success = order.cook_order(order)
        if success:
            return {"message": "Cooking finished. Order is READY.", "status": order.status.value}
        else:
            raise HTTPException(status_code=400, detail=f"Cannot cook order. Current status: {order.status.value}")
    except HTTPException as e:
        return f"ไม่สามารถดำเนินการได้: {e.detail}"
    except ValueError as e:
        return f"ไม่สามารถดำเนินการได้: {str(e)}"
    except Exception as e:
        return f"ไม่สามารถดำเนินการได้: {str(e)}"
    except ValueError as e:
        raise HTTPException(status_code=400, detail=(str(e)))
    success = order.cook_order(  )
    if success:
        return {"message": "Cooking finished. Order is READY.", "status": order.status.value}
    else:
        raise HTTPException(status_code=400, detail=f"Cannot cook order. Current status: {order.status.value}")
   
@router.get("queue")
async def view_kitchen_queue():
    queue = restaurant.get_kitchen_queue()
    if queue["total_queue"]==0:
        return {"message": "No order in queue ","queue": queue}
    return {"message": "Current queue ","queue": queue}
    
    