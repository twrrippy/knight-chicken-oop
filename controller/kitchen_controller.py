from typing import Annotated
from pydantic import Field
from source.utils.mcp_core import mcp
from source.restaurant import restaurant
from source.utils.enum import UserRole

@mcp.tool
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
    
    