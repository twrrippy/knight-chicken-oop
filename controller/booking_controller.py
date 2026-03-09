from fastapi import APIRouter, HTTPException, Query, status, Body
from typing import Optional, List, Tuple, Dict, Any, Annotated
from datetime import datetime, timedelta
from pydantic import Field
from mcp_core import mcp
from main_system.restaurant import restaurant
from main_system.enum import UserRole


router = APIRouter(prefix="/booking", tags=["Booking"])

@mcp.tool
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
        staff = restaurant.verify_token_and_role(token, allowed_roles=[UserRole.ADMIN, UserRole.STAFF])
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
        return f"ไม่สามารถดำเนินการได้: {getattr(e, 'detail', str(e))}"

@mcp.tool
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
    try:
        restaurant.verify_token_and_role(token, allowed_roles=[UserRole.STAFF, UserRole.ADMIN])
        payload = restaurant.booking_room(member_id, room_id, hours, pay_method, start_time=start_time, payment_details=payment_details)
        return payload
    except Exception as e:
        return f"ไม่สามารถดำเนินการได้: {getattr(e, 'detail', str(e))}"

@mcp.tool
@router.get("/preview_booking/{booking_id}")
async def preview_booking(
    token: Annotated[str, Field(
        description="Token ของพนักงาน (ได้จากการเรียกใช้ tool login)"
    )],
    booking_id: Annotated[str, Field(
        description="รหัสการจอง (Format: BK-xxx)"
    )]
):
    """
    ดูรายละเอียดการจอง ต้องการสิทธ์พนักงาน
    """
    try:
        restaurant.verify_token_and_role(token, [UserRole.ADMIN, UserRole.STAFF])
        return restaurant.preview_booking_details(booking_id)
    except Exception as e:
        return f"ไม่สามารถดำเนินการได้: {getattr(e, 'detail', str(e))}"

@mcp.tool
@router.post("/check-in/{booking_id}")
async def check_in(token: str,
        order_id: Annotated[str, Field(
        description="รหัสออเดอร์ (Format: ORD-xxx)"
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
    try:
        restaurant.verify_token_and_role(token, [UserRole.ADMIN, UserRole.STAFF])
        payload = restaurant.check_in_booking(order_id=order_id, booking_id=booking_id, coupon_code=coupon_code, pay_method=pay_method, payment_details=payment_details)
        return payload
    except Exception as e:
        return f"ไม่สามารถดำเนินการได้: {getattr(e, 'detail', str(e))}"

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
    Check out a guest from their booking.
    """
    try:
        restaurant.verify_token_and_role(token, [UserRole.ADMIN, UserRole.STAFF])
        payload = restaurant.check_out_booking(booking_id=booking_id)
        return payload
    except Exception as e:
        return f"ไม่สามารถดำเนินการได้: {getattr(e, 'detail', str(e))}"

@mcp.tool
@router.post("/cancel/{booking_id}")
async def cancel_booking(
    token: Annotated[str, Field(
        description="Token ของพนักงานผู้ทำรายการ"
    )], 
    booking_id: Annotated[str, Field(
        description="รหัสการจองที่ต้องการยกเลิก (Format: BK-xxx)"
    )]
):
    """
    Cancel a room booking.
    """
    try:
        restaurant.verify_token_and_role(token, ["Admin", "Staff"])
        payload = restaurant.cancel_booking(booking_id=booking_id)
        return payload
    except Exception as e:
        return f"ไม่สามารถดำเนินการได้: {getattr(e, 'detail', str(e))}"
