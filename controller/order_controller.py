from fastapi import APIRouter, HTTPException
from shared.utils.response import success_response_status, error_response_status
from main_system.restaurant import restaurant, Order, OrderItem, Guest
from main_system.enum import OrderType
from typing import Union, Annotated
from pydantic import Field
from mcp_core import mcp
import uuid
from fastapi import APIRouter
"""
Order Controller Module
- delivery Management: track and update delivery statuses
- dinein Management: handle table reservations and seating arrangements
- event Management: organize special events and promotions
"""
router = APIRouter(prefix="/order", tags=["Order"])

## ---- ##

@mcp.tool
@router.post("/guest/order/quick")
async def quick_guest_order(
    items: Annotated[list[dict], Field(
        description='List of items: [{"menu": "name", "quantity": x}, ...]'
    )]
):
    """
    Create a guest order and add multiple items at once, then reserve stock.
    Example: [{"menu": "Cola", "quantity": 2}, {"menu": "Fried Chicken", "quantity": 1}]
    """
    try:
        current_customer = Guest()
        order = Order(OrderType.GENERAL, current_customer)
        restaurant.add_order(order)
        for item in items:
            menu = restaurant.search_menu_item_from_name(item["menu"])
            order.add_order_item(menu, item["quantity"])
        
        # Reserve stock immediately
        # Note: In restaurant.py, reserve() seems to be the method
        reserved_order = restaurant.reserve(order)
        reserved_order.update_price()
        return reserved_order.order_to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

## ---- ##

""" ------- Tools เยอะไป LLM งง -------- """

@mcp.tool
@router.post("/guest/start/general")
async def start_guest_order():
    """
    Create a new empty order for a guest customer. Use this first before adding items to an order.
    """
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
    
@mcp.tool
@router.put("/orderitem/add", response_model=Union[Order.OrderDTO, dict])
async def add_item_to_order( #ควรเป็นชื่อ add item to order
    orderitem: Annotated[OrderItem.OrderItemDTO, Field(
        description='Format: {"order_id": "ORD-xxx", "menu": "menu_name", "quantity": x}'
    )]
):
    """
    2. เพิ่ม order item ใน order
    
    input เป็น json body
    Format: {"order_id": "ORD-xxx", "menu": "menu_name", "quantity": x}

    โดย ชื่อเมนู นำมาจาก ฟังก์ชั่น menu
    ไปต่อที่ 3. check_and_reserve_stock เพื่อตรวจสอบ stock และจอง stock ก่อนยืนยัน
    """
    try:
        current_order = restaurant.search_order_from_id(orderitem.order_id)
        menu = restaurant.search_menu_item_from_name(orderitem.menu)
        current_order.add_order_item(menu, orderitem.quantity)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=(str(e)))
    return current_order.order_to_dict()

# @router.put("/orderitem/custom/add/{order_id}", response_model=Union[Order.OrderDTO, dict])
# async def custom_add_orderitem(custom: OrderItem.CustomDTO):


@mcp.tool
@router.put("/ordering/guest", response_model=Union[Order.OrderDTO, dict]) # (ควรแก้ชื่อเป็น /reserve_stock ให้ระบุชัดเจนว่าใช้จองสต็อก)
async def check_and_reserve_stock(
    order_id: Annotated[str, Field(
        description='หมายเลขออเดอร์ FORMAT ORD-xxx')], 
    guest_id: Annotated[str, Field(
        description='id ของ guest FORMAT GUEST-xxx')]
): # (ควรแก้เป็น reserve_order_stock)
    """
    3. ตรวจสอบ stock และ eserve_order_stock ก่อนยืนยันออเดอร์
    ไปต่อที่ 4. confirm_order เพื่อ ยืนยันออเดอร์
    """
    if restaurant.check_queue >= 50:
        raise HTTPException(status_code=418, detail="Queue Overload")
    try:
        current_customer = Guest(guest_id)
        order = restaurant.search_order_from_id(order_id)
        order.check_customer(current_customer)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    reserved_order = restaurant.reserve(order) # (ควรแก้เป็น reserve_stock)
    reserved_order.update_price
    return reserved_order.order_to_dict()

@mcp.tool
@router.put("/confirm/guest", response_model=Union[Order.OrderDTO, dict]) # (ควรแก้เป็น /finalize ให้ดูเป็นการสรุปยอดตัดบิลจริงๆ)
async def confirm_order(
    order_id: Annotated[str, Field(
        description='หมายเลขออเดอร์ FORMAT ORD-xxx')], 
    guest_id: Annotated[str, Field(
        description='id ของ guest FORMAT GUEST-xxx')]
): # (ควรแก้เป็น finalize_order)
    """
    4. ยืนยันออเดอร์ เพื่อพร้อมจ่ายเงินต่อไป
    """
    try:
        current_customer = Guest(guest_id)
        order = restaurant.search_order_from_id(order_id)
        order.check_customer(current_customer)
        confirmed_order = restaurant.confirm(order) # (ควรแก้เป็น finalize_order)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return confirmed_order.order_to_dict()