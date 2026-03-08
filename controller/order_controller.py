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

@mcp.tool
@router.post("/guest/start/general")
async def guest_start_general_order():
    """
    เริ่มต้นการสั่งอาหารสำหรับลูกค้า Walk-in (Guest)
    """
    # """
    # [Intent]: เริ่มต้นการสั่งอาหารสำหรับลูกค้า Walk-in (Guest) ที่หน้าร้าน\n
    # [State Change]: \n
    #     1. สร้าง instance ของ `Guest`\n
    #     2. สร้าง `Order` ใหม่ประเภท GENERAL โดยผูกกับ `Guest`\n
    #     3. บันทึก Order ลงใน Restaurant ผ่าน `restaurant.add_order()`\n
    # [Returns]: Dictionary ข้อมูล Order ID และชื่อลูกค้า\n
    # """
    try:
        current_customer = Guest()
        order = Order(OrderType.GENERAL, current_customer)
        restaurant.add_order(order)
        return {
            "Order ID": order.id,
            "Customer": current_customer.name
        }
    except Exception as e:
        return f"ไม่สามารถดำเนินการได้: {getattr(e, 'detail', str(e))}"

@mcp.tool
@router.post("/member/start/general")
async def member_start_general_order(
    token: Annotated[str, Field(
        description="Token ของสมาชิก (ได้จากการเรียกใช้ tool login)"
    )]
):
    """
    เริ่มต้นการสั่งอาหารสำหรับลูกค้า Member ต้องการสิทธ์ Member
    """

    # """
    # [Intent]: เริ่มต้นการสั่งอาหารสำหรับลูกค้า (Member) ที่หน้าร้าน\n
    # [State Change]: \n
    #     1. ตรวจสอบสิทธิ์และหาเจ้าของ 'token' จาก 'restaurant.verify_token_and_role()'\n
    #     2. สร้าง `Order` ใหม่ประเภท GENERAL โดยผูกกับ `Member`\n
    #     3. บันทึก Order ลงใน Restaurant ผ่าน `restaurant.add_order()`\n
    # [Returns]: Dictionary ข้อมูล Order ID และชื่อลูกค้า\n
    # """
    try:
        current_customer = restaurant.verify_token_and_role(token=token, allowed_roles=["Member"])
        order = Order(OrderType.GENERAL, current_customer)
        restaurant.add_order(order)
        return {
            "Order ID": order.id,
            "Customer": current_customer.name
        }
    except Exception as e:
        return f"ไม่สามารถดำเนินการได้: {getattr(e, 'detail', str(e))}"

@mcp.tool  
@router.put("/orderitem/add", response_model=Union[Order.OrderDTO, dict])
async def add_item_to_order(
    order_id: Annotated[str, Field(
        description="รหัสออเดอร์(รูปแบบที่คาดหวัง: ORD-xxx)"
    )], 
    menu: Annotated[str, Field(
        description="ชื่อเมนูอาหาร ได้จากการเรียกใช้ tool (get_menu)"
    )], 
    quantity: Annotated[int, Field(
        description="จำนวนอาหารที่ต้องการเพิ่ม 1 ขึ้นไป"
    )]
):
    """
    เพิ่มเมนูอาหารพร้อมจำนวน ลงในออเดอร์ที่มีอยู่แล้ว 
    """

    # """
    # [Intent]: เพิ่มเมนูอาหารพร้อมจำนวน (OrderItem) ลงในออเดอร์ (Order) ที่มีอยู่แล้ว\n
    # [Dependencies]: \n
    #     - `restaurant.search_order_from_id()` เพื่อหา Order ปัจจุบัน\n
    #     - `restaurant.search_menu_item_from_name()` เพื่อดึงข้อมูล MenuItem จากชื่อ\n
    # [State Change]: อัปเดตรายการอาหารภายในออเดอร์ ผ่าน `current_order.add_order_item()`\n
    # """
    try:
        current_order = restaurant.search_order_from_id(order_id)
        current_menu = restaurant.search_menu_item_from_name(menu)
        current_order.add_order_item(current_menu, quantity)
    except Exception as e:
        return f"ไม่สามารถดำเนินการได้: {getattr(e, 'detail', str(e))}"
    return current_order.order_to_dict()

@mcp.tool
@router.put("/orderitem/remove", response_model=Union[Order.OrderDTO, dict])
async def remove_item_in_order(
    order_id: Annotated[str, Field(
        description="รหัสออเดอร์(รูปแบบที่คาดหวัง: ORD-xxx)"
    )], 
    order_item_id: Annotated[int, Field(
        description="ลำดับของเมนูอาหาร (order_item) ที่ต้องการลบใน order"
    )]
):
    """
    ลบรายการอาหาร (OrderItem) จากออเดอร์ (Order) ที่มีอยู่แล้ว
    """
    try:
        current_order = restaurant.search_order_from_id(order_id)
        current_order.remove_order_item(order_item_id)
    except Exception as e:
        return f"ไม่สามารถดำเนินการได้: {getattr(e, 'detail', str(e))}"
    return current_order.order_to_dict()

@mcp.tool
@router.put("/orderitem/custom", response_model=Union[Order.OrderDTO, dict])
async def custom_item_in_order(
    order_id: Annotated[str, Field(
        description="รหัสออเดอร์(รูปแบบที่คาดหวัง: ORD-xxx)"
    )], 
    order_item_id: Annotated[int, Field(
        description="ลำดับของเมนูอาหาร (order_item) ที่ต้องการ custom ใน order"
    )], 
    item_name: Annotated[str, Field(
        description="ชื่อของ item ที่ต้องการแก้"
    )], 
    quantity: Annotated[int, Field(
        description="จำนวนของ item ที่ต้องการ"
    )]
):
    """
    ปรับแต่ง Ingredient ของเมนูอาหารที่อยู่ใน Order
    """
    # """
    # [Intent]: ปรับแต่งส่วนผสม (Customizable Ingredient) ของเมนูอาหารที่อยู่ใน Order\n
    # [Logic]: ใช้สำหรับเมนูประเภท SingleMenuItem ที่สืบทอดจาก MenuItem\n
    # [State Change]: ค้นหา Order ตาม ID และเรียกใช้ `current_order.custom()` เพื่อปรับจำนวนของ ingredient (ที่มี item ชื่อ item_name) ของ SingleMenuItem ใน OrderItem ที่มี order_item_id นั้นๆ\n
    # """
    try:
        current_order = restaurant.search_order_from_id(order_id)
        current_order.custom(order_item_id, item_name, quantity)
    except Exception as e:
        return f"ไม่สามารถดำเนินการได้: {getattr(e, 'detail', str(e))}"
    return current_order.order_to_dict()
    

@mcp.tool
@router.put("/ordering/guest", response_model=Union[Order.OrderDTO, dict])
async def guest_check_and_reserve_stock(
    order_id: Annotated[str, Field(
        description="รหัสออเดอร์(รูปแบบที่คาดหวัง: ORD-xxx)"
    )], 
    guest_id: Annotated[str, Field(
        description="รหัส Guest (รูปแบบที่คาดหวัง: GUEST-xxx)"
    )]
):
    """
    ขั้นตอน Pre-order สำหรับ Guest เพื่อจองวัตถุดิบ/สินค้าก่อนการยืนยัน
    """
    
    if restaurant.check_queue >= 50:
        return f"Queue Overload"
    try:
        current_customer = Guest(guest_id)
        order = restaurant.search_order_from_id(order_id)
        order.check_customer(current_customer)
        reserved_order = restaurant.reserve(order)
        reserved_order.update_price()
    except Exception as e:
        return f"ไม่สามารถดำเนินการได้: {getattr(e, 'detail', str(e))}"
    return reserved_order.order_to_dict()

@mcp.tool
@router.put("/ordering/member", response_model=Union[Order.OrderDTO, dict])
async def member_check_and_reserve_stock(
    order_id: Annotated[str, Field(
        description="รหัสออเดอร์(รูปแบบที่คาดหวัง: ORD-xxx)"
    )], 
    token: Annotated[str, Field(
        description="Token ของสมาชิก (ได้จากการเรียกใช้ tool login)"
    )]
):
    """
    ขั้นตอน Pre-order สำหรับสมาชิก เพื่อจองวัตถุดิบ/สินค้าก่อนการยืนยัน
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
    except Exception as e:
        return f"ไม่สามารถดำเนินการได้: {getattr(e, 'detail', str(e))}"
    return reserved_order.order_to_dict()

@mcp.tool
@router.put("/confirm/guest", response_model=Union[Order.OrderDTO, dict])
async def confirm_order(
    order_id: Annotated[str, Field(
        description="รหัสออเดอร์(รูปแบบที่คาดหวัง: ORD-xxx)"
    )], 
    guest_id: Annotated[str, Field(
        description="รหัส Guest (รูปแบบที่คาดหวัง: GUEST-xxx)"
    )]
):
    """
    ยืนยันคำสั่งซื้อในขั้นตอนสุดท้าย สำหรับ Guest (หลังจากการ reserve สำเร็จแล้ว)
    """
    try:
        current_customer = Guest(guest_id)
        order = restaurant.search_order_from_id(order_id)
        order.check_customer(current_customer)
        confirmed_order = restaurant.confirm(order)
    except Exception as e:
        return f"ไม่สามารถดำเนินการได้: {getattr(e, 'detail', str(e))}"
    return confirmed_order.order_to_dict()

@mcp.tool
@router.put("/confirm/member", response_model=Union[Order.OrderDTO, dict])
async def member_confirm_order(
    order_id: Annotated[str, Field(
        description="รหัสออเดอร์(รูปแบบที่คาดหวัง: ORD-xxx)"
    )], 
    token: Annotated[str, Field(
        description="Token ของสมาชิก (ได้จากการเรียกใช้ tool login)"
    )]
):
    """
    ยืนยันคำสั่งซื้อในขั้นตอนสุดท้าย สำหรับสมาชิก (หลังจากการ reserve สำเร็จแล้ว)
    """
    try:
        current_customer = restaurant.verify_token_and_role(token=token, allowed_roles=["Member"])
        order = restaurant.search_order_from_id(order_id)
        order.check_customer(current_customer)
        confirmed_order = restaurant.confirm(order)
    except Exception as e:
        return f"ไม่สามารถดำเนินการได้: {getattr(e, 'detail', str(e))}"
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
    try:
        restaurant.verify_token_and_role(token, ["Admin"])
        return restaurant.create_random_delivery_order()
    except Exception as e:
        return f"ไม่สามารถดำเนินการได้: {getattr(e, 'detail', str(e))}"

@mcp.tool()
async def update_delivery_status(
    token: Annotated[str, Field(
        description="Token ของพนักงาน (ได้จากการเรียกใช้ tool login)"
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
    try:
        restaurant.verify_token_and_role(token, ["Admin", "Staff"])
        return restaurant.update_delivery_status(order_id, new_status)
    except Exception as e:
        return f"ไม่สามารถดำเนินการได้: {getattr(e, 'detail', str(e))}"