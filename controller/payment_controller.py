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
async def confirm_pay(
    order_id: Annotated[str, Field(
        description="รหัสออเดอร์ที่ต้องการชำระเงิน (รูปแบบที่คาดหวัง: ORD-xxx-xxx)"
    )],
    staff_id: Annotated[str, Field(
        description="รหัสพนักงานผู้ดำเนินการทำรายการ"
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
    ยืนยันการชำระเงิน คำนวณยอดสุทธิ และออกใบเสร็จรับเงิน (Execute Payment)

    ฟังก์ชันนี้ทำหน้าที่ยืนยันยอดชำระเงินและดำเนินการตัดเงินจริงตามวิธีการชำระเงิน (Payment Method) ที่เลือก
    พร้อมทั้งทริกเกอร์ (Trigger) การอัปเดตสถานะของออบเจ็กต์ที่เกี่ยวข้องทั้งหมดในระบบเมื่อการทำรายการสำเร็จ

    ข้อควรระวังสำคัญ (CRITICAL RULE):
    หากผู้ใช้งานไม่ได้ระบุวิธีการชำระเงิน (method) หรือ ข้อมูลรายละเอียดการชำระเงิน (payment_details) มาอย่างครบถ้วน
    ห้ามเดา สุ่ม หรือสร้างข้อมูลจำลองขึ้นมาเองโดยเด็ดขาด ระบบจะต้องหยุดการทำงานและสอบถามข้อมูลที่ขาดหายไปจากผู้ใช้งานก่อนเรียกใช้ฟังก์ชันนี้เสมอ

    Returns:
        Dict[str, Any]: ข้อมูล JSON ของใบเสร็จรับเงิน (Receipt) สำหรับส่งคืนค่าให้ Frontend

    Side Effects (กระบวนการอัปเดตระบบเมื่อทำรายการสำเร็จ):
        - Order: เปลี่ยนสถานะเป็น `PAID`
        - Transaction: บันทึกประวัติการทำรายการและอัปเดตสถานะเป็น `SUCCESS`
        - Booking & Room: หากเป็น EventOrder จะเปลี่ยนสถานะการจองเป็น `CHECKED_IN` และสถานะห้องเป็น `IN_USE`
        - Kitchen: ส่งคำสั่งทำอาหารเข้าสู่คิวของห้องครัว
        - Coupon: มาร์คสถานะคูปองที่ถูกใช้งานเป็น `NOT_AVAILABLE`
        - Receipt: สร้างใบเสร็จในระบบและจัดเก็บลงในประวัติของลูกค้า
    """
    try:
        result = restaurant.process_order_payment(order_id, staff_id, coupon_code, method, payment_details)
        return result
    except HTTPException as e:
        return f"ไม่สามารถดำเนินการได้: {e.detail}"
    except Exception as e:
        return f"เกิดข้อผิดพลาดของระบบ: {str(e)}"

@mcp.tool
@router.post("/preview_order/{order_id}")
async def preview_order(
    order_id: Annotated[str, Field(
        description="รหัสออเดอร์ที่ต้องการตรวจสอบยอด (รูปแบบที่คาดหวัง: ORD-xxx-xxx)"
    )],
    token: Annotated[str, Field(
        description="Token ของพนักงาน (ได้จากการเรียกใช้ tool login)"
    )],
    coupon_code: Annotated[Optional[str], Field(
        description="โค้ดคูปองส่วนลดที่ต้องการทดลองคำนวณเพื่อดูยอดก่อนจ่ายจริง (ถ้ามี)"
    )] = None
):
    """
    คำนวณยอดเงินที่ต้องชำระและแสดงรายละเอียดของออเดอร์ (Preview Bill)

    ฟังก์ชันนี้ทำงานแบบ Stateless เพื่อดึงข้อมูลสรุปของออเดอร์ให้พนักงานใช้แจ้งลูกค้าก่อนชำระเงินจริง
    โดยระบบจะยังไม่มีการบันทึกการใช้งานคูปองหรือเปลี่ยนแปลงสถานะใดๆ ของออเดอร์จนกว่าจะมีการเรียกใช้ฟังก์ชัน confirm_pay

    Returns:
        Dict[str, Any]: ข้อมูล JSON สรุปรายละเอียดออเดอร์ ซึ่งประกอบด้วย:
            - รายการอาหารและรายละเอียดการจอง/ค่าส่ง
            - ยอดรวมก่อนลด (Subtotal)
            - ส่วนลดจากคูปอง (Discount)
            - เงินมัดจำที่หักออก (Deposit Deduction)
            - ยอดชำระสุทธิ (Final Price)
    """

    try:
        result = restaurant.preview_order_bill(order_id, staff_id, coupon_code)
        return result
    except HTTPException as e:
        return f"ไม่สามารถดำเนินการได้: {e.detail}"
    except Exception as e:
        return f"เกิดข้อผิดพลาดของระบบ: {str(e)}"