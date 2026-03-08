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
async def guest_start_general_order():
    """
    [Intent]: เริ่มต้นการสั่งอาหารสำหรับลูกค้า Walk-in (Guest) ที่หน้าร้าน\n
    [State Change]: \n
        1. สร้าง instance ของ `Guest`\n
        2. สร้าง `Order` ใหม่ประเภท GENERAL โดยผูกกับ `Guest`\n
        3. บันทึก Order ลงใน Restaurant ผ่าน `restaurant.add_order()`\n
    [Returns]: Dictionary ข้อมูล Order ID และชื่อลูกค้า\n
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
        return f"{e}"
        # raise HTTPException(status_code=400, detail=str(e))
    
@router.post("/member/start/general")
async def member_start_general_order(token: str):
    """
    [Intent]: เริ่มต้นการสั่งอาหารสำหรับลูกค้า (Member) ที่หน้าร้าน\n
    [State Change]: \n
        1. ตรวจสอบสิทธิ์และหาเจ้าของ 'token' จาก 'restaurant.verify_token_and_role()'\n
        2. สร้าง `Order` ใหม่ประเภท GENERAL โดยผูกกับ `Member`\n
        3. บันทึก Order ลงใน Restaurant ผ่าน `restaurant.add_order()`\n
    [Returns]: Dictionary ข้อมูล Order ID และชื่อลูกค้า\n
    """
    try:
        current_customer = restaurant.verify_token_and_role(token=token, allowed_roles=["Member"])
        order = Order(OrderType.GENERAL, current_customer)
        restaurant.add_order(order)
        return {
            "Order ID": order.id,
            "Customer": current_customer.name
        }
    except HTTPException as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@router.put("/orderitem/add", response_model=Union[Order.OrderDTO, dict])
async def add_item_to_order(order_id: str, menu: str, quantity: int):
    """
    [Intent]: เพิ่มเมนูอาหารพร้อมจำนวน (OrderItem) ลงในออเดอร์ (Order) ที่มีอยู่แล้ว\n
    [Dependencies]: \n
        - `restaurant.search_order_from_id()` เพื่อหา Order ปัจจุบัน\n
        - `restaurant.search_menu_item_from_name()` เพื่อดึงข้อมูล MenuItem จากชื่อ\n
    [State Change]: อัปเดตรายการอาหารภายในออเดอร์ ผ่าน `current_order.add_order_item()`\n
    """
    try:
        current_order = restaurant.search_order_from_id(order_id)
        current_menu = restaurant.search_menu_item_from_name(menu)
        current_order.add_order_item(current_menu, quantity)
    except ValueError as e:
        return f"{e}"
        # raise HTTPException(status_code=400, detail=(str(e)))
    return current_order.order_to_dict()
 
@router.put("/orderitem/remove", response_model=Union[Order.OrderDTO, dict])
async def remove_item_in_order(order_id: str, order_item_id: int):
    """
    [Intent]: ลบรายการอาหาร (OrderItem) จากออเดอร์ (Order) ที่มีอยู่แล้ว\n
    [Dependencies]: `restaurant.search_order_from_id()` เพื่อหา Order ปัจจุบัน\n
    [State Change]: อัปเดตรายการอาหารภายในออเดอร์ ผ่าน `current_order.remove_order_item()`\n
    """
    try:
        current_order = restaurant.search_order_from_id(order_id)
        current_order.remove_order_item(order_item_id)
    except ValueError as e:
        return f"{e}"
        # raise HTTPException(status_code=400, detail=(str(e)))
    return current_order.order_to_dict()

@router.put("/orderitem/custom", response_model=Union[Order.OrderDTO, dict])
async def custom_item_in_order(order_id: str, order_item_id: int, item_name: str, quantity: int):
    """
    [Intent]: ปรับแต่งส่วนผสม (Customizable Ingredient) ของเมนูอาหารที่อยู่ใน Order\n
    [Logic]: ใช้สำหรับเมนูประเภท SingleMenuItem ที่สืบทอดจาก MenuItem\n
    [State Change]: ค้นหา Order ตาม ID และเรียกใช้ `current_order.custom()` เพื่อปรับจำนวนของ ingredient (ที่มี item ชื่อ item_name) ของ SingleMenuItem ใน OrderItem ที่มี order_item_id นั้นๆ\n
    """
    try:
        current_order = restaurant.search_order_from_id(order_id)
        current_order.custom(order_item_id, item_name, quantity)
    except ValueError as e:
        return f"{e}"
        # raise HTTPException(status_code=400, detail=(str(e)))
    except TypeError as e:
            raise TypeError(str(e))
    return current_order.order_to_dict()
    


@router.put("/ordering/guest", response_model=Union[Order.OrderDTO, dict])
async def check_and_reserve_stock(order_id: str, guest_id: str):
    """
    [Intent]: ขั้นตอน Pre-order เพื่อจองวัตถุดิบ/สินค้าก่อนการยืนยัน\n
    [Business Rules]: \n
        - หาก `restaurant.check_queue` >= 50 จะปฏิเสธการสั่ง\n
        - ต้องตรวจสอบสิทธิ์ว่า `guest_id` ตรงกับเจ้าของ Order (`order.check_customer()`)\n
    [State Change]: เรียก `restaurant.reserve()` เพื่อจองสต็อก\n
    """
    if restaurant.check_queue >= 50:
        return f"Queue Overload"
        # raise HTTPException(status_code=418, detail="Queue Overload")
    try:
        current_customer = Guest(guest_id)
        order = restaurant.search_order_from_id(order_id)
        order.check_customer(current_customer)
        reserved_order = restaurant.reserve(order)
        reserved_order.update_price()
    except ValueError as e:
        return f"{e}"
        # raise HTTPException(status_code=400, detail=str(e))
    return reserved_order.order_to_dict()

@router.put("/ordering/member", response_model=Union[Order.OrderDTO, dict])
async def check_and_reserve_stock(order_id: str, token: str):
    """
    [Intent]: ขั้นตอน Pre-order เพื่อจองวัตถุดิบ/สินค้าก่อนการยืนยัน\n
    [Business Rules]: \n
        - หาก `restaurant.check_queue` >= 50 จะปฏิเสธการสั่ง\n
        - ต้องตรวจสอบสิทธิ์ว่าเจ้าของ `token` ตรงกับเจ้าของ Order (`order.check_customer()`)\n
    [State Change]: เรียก `restaurant.reserve()` เพื่อจองสต็อก\n
    """
    if restaurant.check_queue >= 50:
        return f"Queue Overload"
        # raise HTTPException(status_code=418, detail="Queue Overload")
    try:
        current_customer = restaurant.verify_token_and_role(token=token, allowed_roles=["Member"])
        order = restaurant.search_order_from_id(order_id)
        order.check_customer(current_customer)
        reserved_order = restaurant.reserve(order)
        reserved_order.update_price()
    except ValueError as e:
        return f"{e}"
        # raise HTTPException(status_code=400, detail=str(e))
    return reserved_order.order_to_dict()

@router.put("/confirm/guest", response_model=Union[Order.OrderDTO, dict])
async def confirm_order(order_id: str, guest_id: str):
    """
    [Intent]: ยืนยันคำสั่งซื้อในขั้นตอนสุดท้าย (หลังจากการ reserve สำเร็จแล้ว)\n
    [Dependencies]: `restaurant.confirm(order)`\n
    [State Change]: เปลี่ยนสถานะ Order เป็น Confirmed และเตรียมจ่ายเงิน\n
    """
    try:
        current_customer = Guest(guest_id)
        order = restaurant.search_order_from_id(order_id)
        order.check_customer(current_customer)
        confirmed_order = restaurant.confirm(order)
    except ValueError as e:
        return f"{e}"
        # raise HTTPException(status_code=400, detail=str(e))
    return confirmed_order.order_to_dict()
@router.put("/confirm/member", response_model=Union[Order.OrderDTO, dict])
async def confirm_order(order_id: str, token: str):
    """
    [Intent]: ยืนยันคำสั่งซื้อในขั้นตอนสุดท้าย (หลังจากการ reserve สำเร็จแล้ว)\n
    [Dependencies]: `restaurant.confirm(order)`\n
    [State Change]: เปลี่ยนสถานะ Order เป็น Confirmed และเตรียมจ่ายเงิน\n
    """
    try:
        current_customer = restaurant.verify_token_and_role(token=token, allowed_roles=["Member"])
        order = restaurant.search_order_from_id(order_id)
        order.check_customer(current_customer)
        confirmed_order = restaurant.confirm(order)
    except ValueError as e:
        return f"{e}"
        # raise HTTPException(status_code=400, detail=str(e))
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