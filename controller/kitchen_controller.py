from fastapi import APIRouter, HTTPException
import asyncio
from typing import Annotated
from pydantic import Field
from mcp_core import mcp
from main_system.restaurant import restaurant
from main_system.utils.enum import UserRole
router = APIRouter(prefix="/kitchen", tags=["Kitchen"])

@mcp.tool
@router.post("/cook/{order_id}")
async def cook_order(
    token: Annotated[str, Field(
        description="Staff access token (obtained via the 'login' tool)"
    )],
    order_id: Annotated[str, Field(
        description="Order ID to start cooking (Format: ORD-xxx)"
    )]
):
    """
    Start cooking a specific order. Changes the order status to COOKING in the kitchen. 
    """
    try:
        restaurant.verify_token_and_role(token, [UserRole.ADMIN, UserRole.STAFF])
        return restaurant.cook_order(order_id)
    except Exception as e:
        return f"Unable to proceed: {getattr(e, 'detail', str(e))}"
   
@mcp.tool
@router.get("/queue")
async def view_kitchen_queue(
    token: Annotated[str, Field(
        description="Staff access token (obtained via the 'login' tool)"
    )]
):
    """
    View the kitchen queue (orders that are ready to be cooked).
    """
    try:
        restaurant.verify_token_and_role(token, [UserRole.ADMIN, UserRole.STAFF])
        return restaurant.display_kitchen_queue()
    except Exception as e:
        return f"Unable to proceed: {getattr(e, 'detail', str(e))}"
    
    