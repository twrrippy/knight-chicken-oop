from fastapi import APIRouter
from main_system.restaurant import restaurant, Order, OrderItem, Guest
from main_system.enum import UserRole
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
@router.post("/start/general")
async def start_general_order(
    token: Annotated[str, Field(
        description="Token ของลูกค้า (ได้จากการเรียกใช้ tool login หรือ guest)"
    )]
):
    """
    เริ่มต้นการสั่งอาหารสำหรับลูกค้า ต้องการสิทธ์ Member หรือ Guest
    """
    try:
        current_customer = restaurant.verify_token_and_role(token=token, allowed_roles=[UserRole.MEMBER, UserRole.GUEST])
        order = Order(current_customer)
        restaurant.add_order(order)
        return {
            "Order ID": order.id,
            "Customer": current_customer.name
        }
    except Exception as e:
        return f"ไม่สามารถดำเนินการได้: {getattr(e, 'detail', str(e))}"

@mcp.tool()
@router.post("/start/delivery")
async def start_delivery_order(
    token: Annotated[str, Field(
        description="Token ของลูกค้า (ได้จากการเรียกใช้ tool login หรือ guest)"
    )],
    provider_name: Annotated[str, Field(
        description="ชื่อ Delivery Provider เช่น Grab, LineMan, ShopeeFood"
    )],
    distance: Annotated[float, Field(
        description="ระยะทางจากร้านถึงลูกค้า (กิโลเมตร)"
    )]
):
    """
    เริ่มต้นการสั่งอาหารแบบ Delivery สำหรับลูกค้า ต้องการสิทธ์ Member หรือ Guest
    """
    try:
        current_customer = restaurant.verify_token_and_role(token=token, allowed_roles=[UserRole.MEMBER, UserRole.GUEST])
        return restaurant.create_delivery_order(current_customer, provider_name, distance)
    except Exception as e:
        return f"ไม่สามารถดำเนินการได้: {getattr(e, 'detail', str(e))}"

@mcp.tool  
@router.put("/orderitem/add")
async def add_item_to_order(
    token: Annotated[str, Field(
        description="Token ของลูกค้า (ได้จากการเรียกใช้ tool login หรือ guest)"
    )],
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
    try:
        current_customer = restaurant.verify_token_and_role(token=token, allowed_roles=[UserRole.MEMBER, UserRole.GUEST])
        current_order = restaurant.search_order_from_id(order_id)
        current_order.check_customer(current_customer)
        current_menu = restaurant.search_menu_item_from_name(menu)
        current_order.add_order_item(current_menu, quantity)
    except Exception as e:
        return f"ไม่สามารถดำเนินการได้: {getattr(e, 'detail', str(e))}"
    return current_order.order_to_dict()

@mcp.tool
@router.put("/orderitem/remove")
async def remove_item_in_order(
    token: Annotated[str, Field(
        description="Token ของลูกค้า (ได้จากการเรียกใช้ tool login หรือ guest)"
    )],
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
        current_customer = restaurant.verify_token_and_role(token=token, allowed_roles=[UserRole.MEMBER, UserRole.GUEST])
        current_order = restaurant.search_order_from_id(order_id)
        current_order.check_customer(current_customer)
        current_order.remove_order_item(order_item_id)
    except Exception as e:
        return f"ไม่สามารถดำเนินการได้: {getattr(e, 'detail', str(e))}"
    return current_order.order_to_dict()

@mcp.tool
@router.put("/orderitem/custom")
async def custom_item_in_order(
    token: Annotated[str, Field(
        description="Token ของลูกค้า (ได้จากการเรียกใช้ tool login หรือ guest)"
    )],
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
        current_customer = restaurant.verify_token_and_role(token=token, allowed_roles=[UserRole.MEMBER, UserRole.GUEST])
        current_order = restaurant.search_order_from_id(order_id)
        current_order.check_customer(current_customer)
        current_order.custom(order_item_id, item_name, quantity)
        current_order.update_price()
    except Exception as e:
        return f"ไม่สามารถดำเนินการได้: {getattr(e, 'detail', str(e))}"
    return current_order.order_to_dict()
    

@mcp.tool
@router.put("/ordering")
async def check_and_reserve_stock(
    order_id: Annotated[str, Field(
        description="รหัสออเดอร์(รูปแบบที่คาดหวัง: ORD-xxx)"
    )], 
    token: Annotated[str, Field(
        description="Token ของลูกค้า (ได้จากการเรียกใช้ tool login หรือ guest)"
    )]
):
    """
    ขั้นตอน Pre-order สำหรับสมาชิก เพื่อจองวัตถุดิบ/สินค้าก่อนการยืนยัน
    """
    if restaurant.check_queue >= 50:
        return f"Queue Overload"
        # raise HTTPException(status_code=418, detail="Queue Overload")
    try:
        current_customer = restaurant.verify_token_and_role(token=token, allowed_roles=[UserRole.MEMBER, UserRole.GUEST])
        current_order = restaurant.search_order_from_id(order_id)
        current_order.check_customer(current_customer)
        reserved_order = restaurant.reserve(current_order)
        reserved_order.update_price()
    except Exception as e:
        return f"ไม่สามารถดำเนินการได้: {getattr(e, 'detail', str(e))}"
    return reserved_order.order_to_dict()

@mcp.tool
@router.put("/confirm")
async def confirm_order(
    order_id: Annotated[str, Field(
        description="รหัสออเดอร์(รูปแบบที่คาดหวัง: ORD-xxx)"
    )], 
    token: Annotated[str, Field(
        description="Token ของลูกค้า (ได้จากการเรียกใช้ tool login หรือ guest)"
    )]
):
    """
    ยืนยันคำสั่งซื้อในขั้นตอนสุดท้าย สำหรับสมาชิก (หลังจากการ reserve สำเร็จแล้ว)
    """
    try:
        current_customer = restaurant.verify_token_and_role(token=token, allowed_roles=[UserRole.MEMBER, UserRole.GUEST])
        current_order = restaurant.search_order_from_id(order_id)
        current_order.check_customer(current_customer)
        confirmed_order = restaurant.confirm(current_order)
    except Exception as e:
        return f"ไม่สามารถดำเนินการได้: {getattr(e, 'detail', str(e))}"
    return confirmed_order.order_to_dict()

@mcp.tool
@router.put("/serve", response_model=Union[Order.OrderDTO, dict])
async def serve(
    order_id: Annotated[str, Field(
        description="รหัสออเดอร์ที่ต้องการเสิร์ฟ (Format: ORD-xxx)"
    )],
    token: Annotated[str, Field(
        description="Token ของพนักงาน (ได้จากการเรียกใช้ tool login)"
    )]
):
    """
    Update status Order. Changes the order status from Ready to Served. 
    """
    try:
        restaurant.verify_token_and_role(token,[UserRole.ADMIN,UserRole.STAFF])
        order = restaurant.search_order_from_id(order_id)
        is_success = restaurant.serve_order(order)
        if not is_success:
            return f"Status is not READY"
        return order.order_to_dict()
    except Exception as e:
        return f"ไม่สามารถดำเนินการได้: {getattr(e, 'detail', str(e))}"

@router.get("/{order_id}")
async def get_order_from_id(order_id: str):
    current_order = restaurant.search_order_from_id(order_id)
    return current_order.order_to_dict()

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
        restaurant.verify_token_and_role(token, [UserRole.ADMIN, UserRole.STAFF])
        return restaurant.update_delivery_status(order_id, new_status)
    except Exception as e:
        return f"ไม่สามารถดำเนินการได้: {getattr(e, 'detail', str(e))}"

