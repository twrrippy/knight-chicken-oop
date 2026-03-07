from fastapi import APIRouter, HTTPException
from shared.utils.response import success_response_status, error_response_status
from main_system.restaurant import restaurant
from main_system.restaurant import Guest, Order, OrderItem
from main_system.enum import OrderType
from typing import Union
import uuid
"""
Order Controller Module
- delivery Management: track and update delivery statuses
- dinein Management: handle table reservations and seating arrangements
- event Management: organize special events and promotions
"""
router = APIRouter(prefix="/order", tags=["order"])

@router.post("/guest/start/general")
async def start_order():
    try:
        current_customer = Guest()
        order = Order(OrderType.GENERAL, current_customer)
        restaurant.add_order(order)
        return {
            "Order ID": order.id,
            "Customer": current_customer.name
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.put("/orderitem/add", response_model=Union[Order.OrderDTO, dict])
async def add_order(orderitem: OrderItem.OrderItemDTO):
    try:
        current_order = restaurant.search_order_from_id(orderitem.order_id)
        menu = restaurant.search_menu_item_from_name(orderitem.menu)
        current_order.add_order_item(menu, orderitem.quantity)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=(str(e)))
    return current_order.order_to_dict()

@router.put("/ordering/guest", response_model=Union[Order.OrderDTO, dict])
async def ordering(order_id: str, guest_id: str):
    if restaurant.check_queue >= 50:
        raise HTTPException(status_code=418, detail="Queue Overload")
    try:
        current_customer = Guest(guest_id)
        order = restaurant.search_order_from_id(order_id)
        order.check_customer(current_customer)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    reserved_order = restaurant.reserve(order)
    reserved_order.update_price
    return reserved_order.order_to_dict()

@router.put("/confirm/guest", response_model=Union[Order.OrderDTO, dict])
async def confirm_order(order_id: str, guest_id: str):
    try:
        current_customer = Guest(guest_id)
        order = restaurant.search_order_from_id(order_id)
        order.check_customer(current_customer)
        confirmed_order = restaurant.confirm(order)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return confirmed_order.order_to_dict()