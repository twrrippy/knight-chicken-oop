from fastapi import APIRouter, HTTPException, Query, status, Body
from typing import Optional, List, Tuple, Dict, Any, Annotated
from datetime import datetime, timedelta
from pydantic import Field
from mcp_core import mcp

from fastapi.encoders import jsonable_encoder
from main_system.restaurant import restaurant
from shared.utils.response import success_response_status, error_response_status

router = APIRouter(prefix="/booking", tags=["Booking"])

@router.post("/check-booking-availability")
async def check_booking_availability(
    token: Annotated[str, Field(
        description="Token ของพนักงาน (ได้จากการเรียกใช้ tool login)"
    )],
    room_id: Annotated[str, Field(
        description="รหัสห้องที่ต้องการจอง ได้จากการใช้ tool (get_all_rooms)"
    )],
    start_time: Annotated[datetime, Field(
        description="วันและเวลาที่ต้องการเริ่มใช้งาน (รูปแบบ: YYYY-MM-DD HH:MM:SS)"
    )],
    hours: Annotated[int, Field(
        description="จำนวนชั่วโมงที่ต้องการใช้งาน (จำนวนเต็ม)"
    )]
):
    """
    Check the availability of a room for a specific time period.
    """
    try:
        # Validate the token (assuming you have a function to validate it)
        staff = restaurant.verify_token_and_role(token, allowed_roles=["Admin", "Staff"])
        if not staff:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token or insufficient permissions")
        room = restaurant.get_room(room_id)
        if not room:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
        is_available = restaurant.is_slot_avaliable(room, start_time, hours)
        return {"room_id": room_id,
                 "is_available": is_available,
                 "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"), 
                 "deposit_required": f"{room.price_per_hour * hours * 0.5} THB with no discount"
                }
    except Exception as e:
        raise error_response_status(status=status.HTTP_500_INTERNAL_SERVER_ERROR, message=str(e))

# @mcp.tool
@router.post("/booking-room")
async def book_room(
    token: Annotated[str, Field(
        description="Token ของพนักงาน (ได้จากการเรียกใช้ tool login)"
    )],
    member_id: Annotated[str, Field(
        description="รหัสสมาชิก (Format: M-xxx)"
    )], 
    room_id: Annotated[str, Field(
        description="รหัสห้องที่ต้องการจอง ได้จากการใช้ tool (get_all_rooms)"
    )], 
    start_time: Annotated[datetime, Field(
        description="วันและเวลาที่ต้องการเริ่มใช้งาน (รูปแบบ: YYYY-MM-DD HH:MM:SS)"
    )],
    hours: Annotated[int, Field(
        description="จำนวนชั่วโมงที่ต้องการใช้งาน (จำนวนเต็ม)"
    )], 
    pay_method: Annotated[str, Field(
        description='วิธีการชำระเงิน รองรับเฉพาะ "qrcode", "creditcard" หรือ "cash"'
    )],
    payment_details: Annotated[Dict[str, Any], Field(
        description='ข้อมูลเพิ่มเติมที่บังคับใช้ตามประเภทการจ่ายเงิน: กรณี qrcode ต้องระบุ {"account_number": "xxx"}, กรณี creditcard ต้องระบุ {"card_number": "...", "cvv": "..."}, กรณี cash ต้องระบุ {"cash_received": xxx}'
    )] = {}
):
    """
    Book a room and process the required 50% deposit payment. Do not calculate discounts yourself; the system handles it. Ask the user for room choice and payment details before calling.
    """
    # # Description: There are 5 rooms for booking.\n
    # **R01**: VIP, Price: 2000 THB/hour\n
    # **R02**: Hall, Price: 5000 THB/hour\n
    # **R03**: Standard, Price: 500 THB/hour\n
    # **R04**: VIP, Price: 2000 THB/hour\n
    # **R05**: Standard, Price: 500 THB/hour\n
    # **room_price** = price_per_hour * hours\n
    # **deposit** = room_price * 50%\n
    # **GOLD members** get 15% discount on room price\n
    # **SILVER members** get 10% discount on room price\n
    # **BRONZE members** get 5% discount on room price\n
    # - **payment_details**: ข้อมูลเพิ่มเติมตามประเภทการจ่ายเงิน เช่น 
    #     - qrcode: {"account_number": "xxx"} 
    #     - creditcard: {"card_number": "...", "cvv": "..."} 
    #     - cash: {"cash_received": xxx}\n
    # """
    try:
        payload = restaurant.booking_room(token, member_id, room_id, hours, pay_method, start_time=start_time, payment_details=payment_details)
        return success_response_status(status= status.HTTP_200_OK,payload= jsonable_encoder(payload))
    except Exception as e:
        raise error_response_status(status= status.HTTP_500_INTERNAL_SERVER_ERROR, message=str(e))

# @mcp.tool
@router.get("/preview_booking/{booking_id}")
async def preview_booking(booking_id: str):
    """
    
    """
    return restaurant.preview_booking_details(booking_id)

@router.post("/check-in/{booking_id}")
async def check_in(token: str,
        order_id: Annotated[str, Field(
        description="รหัสออเดอร์ที่เกี่ยวข้องกับการจองห้องนี้ (Format: ORD-xxx)"
    )], 
        booking_id: Annotated[str, Field(
        description="รหัสการจอง (Format: BK-xxx)"
    )], 
        pay_method: Annotated[str, Field(
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
    Check-in a customer to their booked room and process the payment for the remaining balance.
    """
    # """
    # ## Check in a guest for their booking.
    # **order_id**: รหัสออเดอร์ที่เกี่ยวข้องกับการจองนี้ (Format: ORD-xxx-xxx)\n
    # **booking_id**: รหัสการจองที่ต้องการเช็คอิน (Format: BK-xxx)\n
    # **coupon_code**: (Optional) โค้ดคูปองที่ลูกค้าอาจมีและต้องการใช้สำหรับส่วนลด\n
    # **pay_method**: วิธีการชำระเงินที่ลูกค้าใช้สำหรับการจ่ายเงินที่เหลือ (เช่น "qrcode", "creditcard", "cash")\n
    # **payment_details**: ข้อมูลเพิ่มเติมตามประเภทการจ่ายเงิน เช่น 
    #     - qrcode: {"account_number": "xxx"} 
    #     - creditcard: {"card_number": "...", "cvv": "..."} 
    #     - cash: {"cash_received": xxx}\n
    # """
    try:
        payload = restaurant.check_in_booking(token=token, order_id=order_id, booking_id=booking_id, coupon_code=coupon_code, pay_method=pay_method, payment_details=payment_details)
        return success_response_status(status=status.HTTP_200_OK, payload=jsonable_encoder(payload))
    except Exception as e:
        raise error_response_status(status=status.HTTP_500_INTERNAL_SERVER_ERROR, message=str(e))

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
    Check out a guest from their booking.
    """
    try:
        payload = restaurant.check_out_booking(token=token, booking_id=booking_id)
        return success_response_status(status=status.HTTP_200_OK, payload=jsonable_encoder(payload))
    except Exception as e:
        raise error_response_status(status=status.HTTP_500_INTERNAL_SERVER_ERROR, message=str(e))