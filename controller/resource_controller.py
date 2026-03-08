from fastapi import APIRouter, HTTPException
from shared.utils.response import success_response_status, error_response_status
from main_system.restaurant import restaurant
from main_system.ingredient import Item
from main_system.enum import ItemStatus
"""
Resource Controller Module
- inventory Management: manage stock levels, add or remove ingredients
- menu Management: add, update, or remove menu items
"""

router = APIRouter(prefix="/resource")



@router.get("/stock/all", tags=["Stock"])
async def check_stock_all():
    return restaurant.all_stock()

@router.get("/stock/check/{item_name}", tags=["Stock"])
async def check_stock_item(item_name: str):
    return restaurant.check_stock_item(item_name)

@router.post("/stock/add/item")
async def restock(item_name: str,price_per_unit: float, quantity: int):
    try:
        current_item = Item(item_name, price_per_unit)
        restaurant.add_stock(current_item, quantity)
    except ValueError as e:
        return {"message": e}
    
# @router.post("/stock/add/item")
# async def restock(item_name: str, quantity: int):
#     try:
#         current_item = restaurant.search_item_in_stock_from_name(item_name)
#         restaurant.add_stock(current_item, quantity)
#     except ValueError as e:
#         return {"message": e}