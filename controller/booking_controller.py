from typing import Optional, List, Tuple, Dict, Any, Annotated
from fastapi import APIRouter
from datetime import datetime, timedelta
from pydantic import Field
from mcp_core import mcp

from fastapi.encoders import jsonable_encoder
from main_system.restaurant import restaurant
from shared.utils.response import success_response_status, error_response_status

router = APIRouter(prefix="/booking", tags=["Booking"])

@mcp.tool
@router.post("/booking-room") # เพิ่ม api อีกเส้นไหม ให้สามารถเช็คราคาห้อง วัน เวลาที่จะจอง ก่อนได้ แล้วค่อย ให้ อันนี้เป็น confirm booking + pay deposit
async def book_room(
    token: Annotated[str, Field(
        description="Token ของสมาชิกที่เข้าสู่ระบบ"
    )],
    member_id: Annotated[str, Field(
        description="รหัสสมาชิกผู้ทำการจอง"
    )], 
    room_id: Annotated[str, Field(
        description="รหัสห้องที่ต้องการจอง (เช่น R-VIP-01)"
    )], 
    hours: Annotated[int, Field(
        description="จำนวนชั่วโมงที่ต้องการใช้งาน"
    )], 
    amount_paid: Annotated[float, Field(
        description="จำนวนเงินมัดจำที่ชำระ (ต้องไม่น้อยกว่า 50% ของราคาห้อง)" ## amount_paid ไม่จำเป็นต้องมีก็ได้ไหม
    )],
    pay_method: Annotated[str, Field(
        description='วิธีการชำระเงินมัดจำ ("qrcode", "creditcard", "cash")'
    )],
    start_time: Annotated[datetime, Field(
        description="วันและเวลาที่ต้องการเริ่มใช้งาน (รูปแบบ: YYYY-MM-DD HH:MM:SS)"
    )],
    payment_details: Annotated[Dict[str, Any], Field(
        description='ข้อมูลรายละเอียดการชำระเงินตามประเภทที่เลือก'
    )]
):

    """
    Book a room and process the required 50% deposit payment. Do not calculate discounts yourself; the system handles it. Ask the user for room choice and payment details before calling.
    """
    # """# Description: There are 5 rooms for booking.\n
    # **R01**: VIP, Price: 2000 THB/hour\n
    # **R02**: Hall, Price: 5000 THB/hour\n
    # **R03**: Standard, Price: 500 THB/hour\n
    # **R04**: VIP, Price: 2000 THB/hour\n
    # **R05**: Standard, Price: 500 THB/hour\n
    # **room_price** = price_per_hour * hours\n
    # **deposit** = room_price * 50%\n
    # **GOLD members** get 15% discount on room price\n  ### ตอนนี้เหมือนยังไม่มี discount จาก tier ###
    # **SILVER members** get 10% discount on room price\n
    # **BRONZE members** get 5% discount on room price\n
    # - **payment_details**: ข้อมูลเพิ่มเติมตามประเภทการจ่ายเงิน เช่น 
    #     - qrcode: {"account_number": "xxx"} 
    #     - creditcard: {"card_number": "...", "cvv": "..."} 
    #     - cash: {"cash_received": xxx}\n
        
    # จองห้องและชำระเงินมัดจำ (Book Room & Pay Deposit)

    # ขั้นตอนการทำงาน:
    # 1. ตรวจสอบความว่างของห้องตามช่วงเวลาที่ระบุ
    # 2. คำนวณราคาสุทธิ (หักส่วนลดตาม Tier ของสมาชิก)
    # 3. ตรวจสอบยอดมัดจำ (ต้องจ่ายอย่างน้อย 50%)
    # 4. บันทึกข้อมูลการจองและมาร์คสถานะห้องเป็น RESERVED
    
    # Returns:
    #     Dict[str, Any]: ข้อมูลสรุปการจองและใบเสร็จมัดจำ
    # """
    try:
        payload = restaurant.booking_room(token, member_id, room_id, hours, amount_paid, pay_method, start_time=start_time, payment_details=payment_details)
        return success_response_status(status= status.HTTP_200_OK,payload= jsonable_encoder(payload))
    except Exception as e:
        raise error_response_status(status= status.HTTP_500_INTERNAL_SERVER_ERROR, message=str(e))

@mcp.tool
@router.get("/preview_booking/{booking_id}")
async def preview_booking(
    booking_id: Annotated[str, Field(
        description="รหัสการจองที่ต้องการดูรายละเอียด (Format: BK-xxx)"
    )]
):
    """
    Retrieve the details and current status of a specific room booking.
    """
    return restaurant.preview_booking_details(booking_id)

@mcp.tool
@router.post("/check-in/{booking_id}")
async def check_in(
    token: Annotated[str, Field(
        description="Token ของพนักงานผู้ทำรายการ"
    )], 
    order_id: Annotated[str, Field(
        description="รหัสออเดอร์ที่เกี่ยวข้องกับการจองห้องนี้ (Format: ORD-xxx-xxx)"
    )], 
    booking_id: Annotated[str, Field(
        description="รหัสการจองที่ต้องการเช็คอิน (Format: BK-xxx)"
    )], 
    coupon_code: Annotated[Optional[str], Field(
        description="โค้ดคูปองส่วนลดสำหรับยอดชำระที่เหลือ (ถ้ามี)"
    )] = None, 
    pay_method: Annotated[str, Field(
        description='วิธีการชำระเงินส่วนที่เหลือ ("qrcode", "creditcard", "cash")'
    )] = "cash", 
    payment_details: Annotated[Dict[str, Any], Field(
        description="ข้อมูลรายละเอียดการชำระเงิน"
    )] = {}
):
    """
    Check-in a customer to their booked room and process the payment for the remaining balance.
    """
    try:
        payload = restaurant.check_in_booking(token=token, order_id=order_id, booking_id=booking_id, coupon_code=coupon_code, pay_method=pay_method, payment_details=payment_details)
        return success_response_status(status=status.HTTP_200_OK, payload=jsonable_encoder(payload))
    except Exception as e:
        raise error_response_status(status=status.HTTP_500_INTERNAL_SERVER_ERROR, message=str(e))

@mcp.tool
@router.post("/check-out/{booking_id}")
async def check_out(
    token: Annotated[str, Field(
        description="Token ของพนักงานผู้ทำรายการ"
    )], 
    booking_id: Annotated[str, Field(
        description="รหัสการจองที่ต้องการเช็คเอาท์ (Format: BK-xxx)"
    )]
):
    """
    Check-out a customer from a room, finalize the booking, and set the room to cleaning status.
    """
    try:
        payload = restaurant.check_out_booking(token=token, booking_id=booking_id)
        return success_response_status(status=status.HTTP_200_OK, payload=jsonable_encoder(payload))
    except Exception as e:
        raise error_response_status(status=status.HTTP_500_INTERNAL_SERVER_ERROR, message=str(e))