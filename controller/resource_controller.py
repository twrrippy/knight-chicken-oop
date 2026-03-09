from fastapi import APIRouter
from main_system.restaurant import restaurant
from main_system.ingredient import Item
from main_system.utils.enum import UserRole
from typing import Annotated
from pydantic import Field
from mcp_core import mcp

"""
Resource Controller Module
- inventory Management: manage stock levels, add or remove ingredients
- menu Management: add, update, or remove menu items
"""

router = APIRouter(prefix="/resource")


@mcp.tool
@router.get("/stock/all", tags=["Stock"])
async def check_stock_all(
    token: Annotated[str, Field(description="Staff access token (obtained via the 'login' tool)")]
):  
    """
    View all items in stock. Requires Staff access.
    """
    try:
        restaurant.verify_token_and_role(token, [UserRole.ADMIN, UserRole.STAFF])
        return restaurant.all_stock()
    except Exception as e:
        return f"Unable to proceed: {getattr(e, 'detail', str(e))}"

@mcp.tool
@router.get("/stock/check/{item_name}", tags=["Stock"])
async def check_stock_item(
    token: Annotated[str, Field(description="Staff access token (obtained via the 'login' tool)")],
    item_name: Annotated[str, Field(description="Item name obtained via the 'check_stock_all' tool")]
):  
    """
    View quantity of an item in stock. Requires Staff access.
    """
    try:
        restaurant.verify_token_and_role(token, [UserRole.ADMIN, UserRole.STAFF])
        return restaurant.check_stock_item(item_name)
    except Exception as e:
        return f"Unable to proceed: {getattr(e, 'detail', str(e))}"

@mcp.tool
@router.post("/stock/add/item")
async def restock(
    token: Annotated[str, Field(description="Staff access token (obtained via the 'login' tool)")],
    item_name: Annotated[str, Field(description="Item name obtained via the 'get_all_item_names' tool")],
    price_per_unit: Annotated[float, Field(description="Price per unit of the item")],
    quantity: Annotated[int, Field(description="Quantity to restock")]
):
    """
    Restock an item. Requires Staff access.
    """
    try:
        restaurant.verify_token_and_role(token, [UserRole.ADMIN, UserRole.STAFF])
        current_item = Item(item_name, price_per_unit)
        restaurant.add_stock(current_item, quantity)
    except Exception as e:
        return f"Unable to proceed: {getattr(e, 'detail', str(e))}"
    
# @router.post("/stock/add/item")
# async def restock(item_name: str, quantity: int):
#     try:
#         current_item = restaurant.search_item_in_stock_from_name(item_name)
#         restaurant.add_stock(current_item, quantity)
#     except ValueError as e:
#         return {"message": e}