from fastapi import APIRouter, HTTPException
from shared.utils.response import success_response_status, error_response_status
from main_system.restaurant import restaurant, Order, OrderItem, Guest
from main_system.enum import OrderType
from typing import Union, Annotated
import uuid
from mcp_core import mcp
from pydantic import Field
from main_system.enum import DeliveryStatus

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

@router.put("/orderitem/custom", response_model=Union[Order.OrderDTO, dict])
async def custom_orderitem(custom: OrderItem.OrderItemCustomDTO):
    try:
        current_order = restaurant.search_order_from_id(custom.order_id)
        current_order.custom(custom.order_item_id, custom.item_name, custom.quantity)
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
        reserved_order = restaurant.reserve(order)
        reserved_order.update_price
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
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

@mcp.tool()
async def create_random_delivery_order(
    token: Annotated[str, Field(
        description="Token ของพนักงาน (ได้จากการเรียกใช้ tool login)"
    )]
):
    """
    สร้าง delivery order แบบสุ่ม อัตโนมัติ (สุ่ม provider, เมนู, จ่ายเงินผ่าน creditcard)
    """
    restaurant.verify_token_and_role(token, ["Admin"])
    return restaurant.create_random_delivery_order()

@mcp.tool()
async def update_delivery_status(
    token: Annotated[str, Field(
        description="Token ของพนักงาน"
    )],
    order_id: Annotated[str, Field(
        description="รหัสออเดอร์ของ delivery_order"
    )],
    new_status: Annotated[DeliveryStatus, Field(
        description="สถานะใหม่ที่ต้องการเปลี่ยน เช่น Driver Assigned, Delivered, Canceled"
    )]
):
    """
    อัปเดตสถานะของ delivery_order 
    """
    restaurant.verify_token_and_role(token, ["Admin", "Staff"])
    return restaurant.update_delivery_status(order_id, new_status)