from fastapi import APIRouter
from typing import Optional, List, Tuple, Dict, Any
from fastapi import HTTPException, Query
from shared.utils.response import success_response_status, error_response_status

from main import restaurant_system, mcp
router = APIRouter(prefix="/payment", tags=["payment"])


@mcp.tool
@router.post("/payment/confirm_pay/{order_id}")
async def confirm_pay(order_id: str, staff_id: str, method: str, coupon_code: Optional[str] = Query(default=None), payment_details: Dict[str, Any] = {}):
    """
    ยืนยันการชำระเงิน คำนวณยอดสุดท้าย และออกใบเสร็จ (Execute Payment)

    หน้าที่:
    - ยืนยันยอดชำระสุทธิและตัดเงินจริงตาม Payment Method ที่เลือก
    - อัปเดตสถานะของออบเจ็กต์ต่างๆ ที่เกี่ยวข้องในระบบเมื่อชำระเงินสำเร็จ
    
    Arguments:
    - order_id: รหัสออเดอร์ (Format: ORD-xxx-xxx)
    - staff_id: รหัสพนักงานผู้ทำรายการ
    - method: วิธีการชำระเงิน (เช่น "qrcode", "creditcard", "cash")
    - coupon_code: (Optional) โค้ดคูปองที่ต้องการใช้งาน
    - payment_details: ข้อมูลเพิ่มเติมตามประเภทการจ่ายเงิน เช่น 
        - qrcode: {"account_number": "xxx" } 
        - creditcard: {"card_number": "...", "cvv": "..."} 
        - cash: {"cash_received": xxx}

    ผลลัพธ์เมื่อทำรายการสำเร็จ:
    1. Order -> เปลี่ยนสถานะเป็น PAID
    2. Transaction -> บันทึกประวัติและเปลี่ยนสถานะเป็น SUCCESS
    3. Booking & Room -> หากเป็น EventOrder จะเปลี่ยนสถานะจองเป็น CHECKED_IN และห้องเป็น IN_USE
    4. Kitchen -> ส่งรายการอาหารเข้าคิวห้องครัว
    5. Coupon -> ถูกมาร์คว่าใช้งานแล้ว (NOT_AVAILABLE)
    6. Receipt -> สร้างใบเสร็จ เก็บลงประวัติลูกค้า และคืนค่า JSON ให้ Frontend
    """
    return restaurant_system.process_order_payment(order_id, staff_id, coupon_code, method, payment_details)

@mcp.tool
@router.post("/payment/preview_order/{order_id}")
async def preview_order(order_id: str, staff_id: str, coupon_code: Optional[str] = Query(default=None)):
    """
    คำนวณยอดเงินที่ต้องชำระสำหรับ Order (Preview)
    
    หน้าที่:
    - ดึงข้อมูล Order ตาม ID (Format: ORD-xxx-xxx)
    - ตรวจสอบสิทธิ์พนักงาน (staff_id) ว่าสามารถเข้าถึงประเภท Order นั้นๆ ได้หรือไม่
    - (Optional) ทดลองคำนวณส่วนลดถ้าใส่ coupon_code มา เพื่อดูยอดก่อนจ่ายจริง
    
    การทำงาน:
    - ระบบจะคืนค่า JSON สรุปรายละเอียดออเดอร์ทั้งหมด (รายการอาหาร, รายละเอียดการจองห้อง, ค่าส่ง ฯลฯ)
    - แสดงยอดรวมก่อนลด, ส่วนลดจากคูปอง, เงินมัดจำที่หักออก (ถ้ามี), และยอดสุทธิ (Final Price) เพื่อให้พนักงานแจ้งลูกค้า
    - ฟังก์ชันนี้เป็นแบบ Stateless จะยังไม่บันทึกการใช้คูปองหรือเปลี่ยนแปลงสถานะใดๆ จนกว่าจะเรียก /confirm_pay
    """

    return restaurant_system.preview_order_bill(order_id, staff_id, coupon_code)