from fastapi import APIRouter
from typing import Optional, Dict, Any, Annotated
from pydantic import Field
from main_system.restaurant import restaurant
from main_system.enum import UserRole
from mcp_core import mcp
router = APIRouter(prefix="/payment", tags=["Payment"])


@mcp.tool
@router.post("/confirm_pay/{order_id}")
async def confirm_order_pay(
    token: Annotated[str, Field(
        description="Token ของลูกค้า (ได้จากการเรียกใช้ tool login หรือ guest)"
    )],
    order_id: Annotated[str, Field(
        description="รหัสออเดอร์ที่ต้องการชำระเงิน (รูปแบบที่คาดหวัง: ORD-xxx)"
    )],
    method: Annotated[str, Field(
        description='วิธีการชำระเงิน รองรับเฉพาะ "qrcode", "creditcard" หรือ "cash"'
    )],
    coupon_code: Annotated[Optional[str], Field(
        description="โค้ดคูปองส่วนลดที่ต้องการใช้งาน (ถ้ามี)"
    )] = None,
    payment_details: Annotated[Dict[str, Any], Field(
        description='ข้อมูลเพิ่มเติมที่บังคับใช้ตามประเภทการจ่ายเงิน: กรณี qrcode ต้องระบุ {"account_number": "xxx"}, กรณี creditcard ต้องระบุ {"card_number": "...", "cvv": "..."}, กรณี cash ต้องระบุ {"cash_received": xxx}'
    )] = {}
):

    """
    Execute final payment and generate a receipt. CRITICAL: Do not guess parameters. You must explicitly ask the user for 'method' and 'payment_details' before executing this tool.
    """

    try:
        current_customer = restaurant.verify_token_and_role(token=token, allowed_roles=[UserRole.MEMBER, UserRole.GUEST])
        current_order = restaurant.search_order_from_id(order_id)
        current_order.check_customer(current_customer)
        result = restaurant.process_order_payment(order_id, coupon_code, method, payment_details)
        return result
    except Exception as e:
        return f"ไม่สามารถดำเนินการได้: {getattr(e, 'detail', str(e))}"

@mcp.tool
@router.post("/preview_order/{order_id}")
async def preview_order_bill(
    token: Annotated[str, Field(
        description="Token ของลูกค้า (ได้จากการเรียกใช้ tool login หรือ guest)"
    )],
    order_id: Annotated[str, Field(
        description="รหัสออเดอร์ที่ต้องการตรวจสอบยอด (รูปแบบที่คาดหวัง: ORD-xxx)"
    )],
    coupon_code: Annotated[Optional[str], Field(
        description="โค้ดคูปองส่วนลดที่ต้องการทดลองคำนวณเพื่อดูยอดก่อนจ่ายจริง (ถ้ามี)"
    )] = None
):

    """
    Calculate and preview the total bill for an order (subtotal, discounts, final price) before payment. This is a read-only action.
    """

    try:
        current_customer = restaurant.verify_token_and_role(token=token, allowed_roles=[UserRole.MEMBER, UserRole.GUEST])
        current_order = restaurant.search_order_from_id(order_id)
        current_order.check_customer(current_customer)
        restaurant.verify_token_and_role(token=token, allowed_roles=[UserRole.MEMBER, UserRole.GUEST])
        result = restaurant.preview_order_bill(order_id, coupon_code)
        return result
    except Exception as e:
        return f"ไม่สามารถดำเนินการได้: {getattr(e, 'detail', str(e))}"