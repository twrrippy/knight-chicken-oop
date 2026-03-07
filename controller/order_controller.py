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

@router.post("/general/guest/start", response_model=str)
async def start_order(guest: Guest.GuestDTO):
    try:
        current_customer = Guest(guest.id, guest.name, guest.phone_number)
        order = Order(f"TXN-{uuid.uuid4().hex[:12].upper()}", OrderType.GENERAL, current_customer)
        restaurant.add_order(order)
        return order.id
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
    return current_order.order_to_dict(restaurant)

@router.put("/ordering/guest", response_model=Union[Order.OrderDTO, dict])
async def ordering(order_id: str, guest: Guest.GuestDTO):
    if restaurant.check_queue >= 50:
        raise HTTPException(status_code=418, detail="Queue Overload")
    try:
        current_customer = Guest(guest.id, guest.name, guest.phone_number)
        order = restaurant.search_order_from_id(order_id)
        order.check_customer(current_customer)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    reserved_order = restaurant.reserve(order)
    reserved_order.update_price
    return reserved_order.order_to_dict(restaurant)

@router.put("/confirm/guest", response_model=Union[Order.OrderDTO, dict])
async def confirm_order(order_id: str, guest: Guest.GuestDTO):
    try:
        current_customer = Guest(guest.id, guest.name, guest.phone_number)
        order = restaurant.search_order_from_id(order_id)
        order.check_customer(current_customer)
        confirmed_order = restaurant.confirm(order)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return confirmed_order.order_to_dict(restaurant)