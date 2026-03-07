from fastapi import APIRouter
from typing import Optional, List, Tuple, Dict, Any, Annotated
from pydantic import Field
from fastapi import HTTPException, Query
from shared.utils.response import success_response_status, error_response_status
from main_system.restaurant import restaurant
from mcp_core import mcp
router = APIRouter(prefix="/payment", tags=["Payment"])


@mcp.tool
@router.post("/confirm_pay/{order_id}")
async def confirm_order_pay(
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
        result = restaurant.process_order_payment(order_id, coupon_code, method, payment_details)
        return result
    except HTTPException as e:
        return f"ไม่สามารถดำเนินการได้: {e.detail}"
    except Exception as e:
        return f"เกิดข้อผิดพลาดของระบบ: {str(e)}"

@mcp.tool
@router.post("/preview_order/{order_id}")
async def preview_order_bill(
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
        result = restaurant.preview_order_bill(order_id, coupon_code)
        return result
    except HTTPException as e:
        return f"ไม่สามารถดำเนินการได้: {e.detail}"
    except Exception as e:
        return f"เกิดข้อผิดพลาดของระบบ: {str(e)}"