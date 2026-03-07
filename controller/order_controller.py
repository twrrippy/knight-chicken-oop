from fastapi import APIRouter, HTTPException
from shared.utils.response import success_response_status, error_response_status
from main_system.restaurant import restaurant, Order, OrderItem, Guest
from main_system.enum import OrderType
from typing import Union
import uuid
"""
Order Controller Module
- delivery Management: track and update delivery statuses
- dinein Management: handle table reservations and seating arrangements
- event Management: organize special events and promotions
"""
router = APIRouter(prefix="/order", tags=["Order"])

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
    
# @router.post("/member/start/general")
# async def start_order():
#     try:
#         current_customer = restaurant
#         order = Order(OrderType.GENERAL, current_customer)
#         restaurant.add_order(order)
#         return {
#             "Order ID": order.id,
#             "Customer": current_customer.name
#         }
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))
    
@router.put("/orderitem/add", response_model=Union[Order.OrderDTO, dict])
async def add_order(orderitem: OrderItem.OrderItemDTO):
    try:
        current_order = restaurant.search_order_from_id(orderitem.order_id)
        menu = restaurant.search_menu_item_from_name(orderitem.menu)
        current_order.add_order_item(menu, orderitem.quantity)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=(str(e)))
    return current_order.order_to_dict()

# @router.put("/orderitem/custom/add/{order_id}", response_model=Union[Order.OrderDTO, dict])
# async def custom_add_orderitem(custom: OrderItem.CustomDTO):


@router.put("/reserve_stock/guest", response_model=Union[Order.OrderDTO, dict]) # (เปลี่ยนจาก /ordering เป็น /reserve_stock ให้ระบุชัดเจนว่าใช้จองสต็อก)
async def reserve_order_stock(order_id: str, guest_id: str): # (เปลี่ยนจาก ordering -> reserve_order_stock)
    if restaurant.check_queue >= 50:
        raise HTTPException(status_code=418, detail="Queue Overload")
    try:
        current_customer = Guest(guest_id)
        order = restaurant.search_order_from_id(order_id)
        order.check_customer(current_customer)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    reserved_order = restaurant.reserve_stock(order) # (เปลี่ยนเมทอด restaurant.reserve -> reserve_stock)
    reserved_order.update_price
    return reserved_order.order_to_dict()

@router.put("/finalize/guest", response_model=Union[Order.OrderDTO, dict]) # (เปลี่ยนจาก /confirm เป็น /finalize ให้ดูเป็นการสรุปยอดตัดบิลจริงๆ)
async def finalize_order(order_id: str, guest_id: str): # (เปลี่ยนจาก confirm_order -> finalize_order)
    try:
        current_customer = Guest(guest_id)
        order = restaurant.search_order_from_id(order_id)
        order.check_customer(current_customer)
        confirmed_order = restaurant.finalize_order(order) # (เปลี่ยนเมทอดจาก confirm เป็น finalize_order)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return confirmed_order.order_to_dict()