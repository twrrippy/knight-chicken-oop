from fastapi import APIRouter, HTTPException, Query, status, Body
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime, timedelta

from fastapi.encoders import jsonable_encoder
from main_system.restaurant import restaurant
from shared.utils.response import success_response_status, error_response_status

router = APIRouter(prefix="/booking", tags=["Booking"])

@router.post("/check-booking-availability")
async def check_booking_availability(
    token: str,
    room_id: str,
    start_time: datetime = Query(..., example="2026-02-09 10:00:00"),
    hours: int = Query(..., example=1)
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
    token: str,
    member_id: str, 
    room_id: str, 
    hours: int, 
    pay_method: str = Query(..., description="Payment strategy to use (e.g. QRCode, CreditCard)"),
    start_time: datetime = Query(..., example="2026-02-09 10:00:00"),
    payment_details: Dict[str, Any] = Body(
        ..., 
        example={"account_number": "000-0-00000-0"}
    )
):
    """# Description: There are 5 rooms for booking.\n
    **R01**: VIP, Price: 2000 THB/hour\n
    **R02**: Hall, Price: 5000 THB/hour\n
    **R03**: Standard, Price: 500 THB/hour\n
    **R04**: VIP, Price: 2000 THB/hour\n
    **R05**: Standard, Price: 500 THB/hour\n
    **room_price** = price_per_hour * hours\n
    **deposit** = room_price * 50%\n
    **GOLD members** get 15% discount on room price\n
    **SILVER members** get 10% discount on room price\n
    **BRONZE members** get 5% discount on room price\n
    - **payment_details**: ข้อมูลเพิ่มเติมตามประเภทการจ่ายเงิน เช่น 
        - qrcode: {"account_number": "xxx"} 
        - creditcard: {"card_number": "...", "cvv": "..."} 
        - cash: {"cash_received": xxx}\n
    """
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
async def check_in(token: str, order_id: str, booking_id: str, coupon_code: Optional[str] = Query(default=None), pay_method: str = Query(..., description="Payment strategy to use (e.g. QRCode, CreditCard)"), payment_details: Dict[str, Any] = Body(
        ..., 
        example={"account_number": "000-0-00000-0"}
    )):
    """
    ## Check in a guest for their booking.
    **order_id**: รหัสออเดอร์ที่เกี่ยวข้องกับการจองนี้ (Format: ORD-xxx-xxx)\n
    **booking_id**: รหัสการจองที่ต้องการเช็คอิน (Format: BK-xxx)\n
    **coupon_code**: (Optional) โค้ดคูปองที่ลูกค้าอาจมีและต้องการใช้สำหรับส่วนลด\n
    **pay_method**: วิธีการชำระเงินที่ลูกค้าใช้สำหรับการจ่ายเงินที่เหลือ (เช่น "qrcode", "creditcard", "cash")\n
    **payment_details**: ข้อมูลเพิ่มเติมตามประเภทการจ่ายเงิน เช่น 
        - qrcode: {"account_number": "xxx"} 
        - creditcard: {"card_number": "...", "cvv": "..."} 
        - cash: {"cash_received": xxx}\n
    """
    try:
        payload = restaurant.check_in_booking(token=token, order_id=order_id, booking_id=booking_id, coupon_code=coupon_code, pay_method=pay_method, payment_details=payment_details)
        return success_response_status(status=status.HTTP_200_OK, payload=jsonable_encoder(payload))
    except Exception as e:
        raise error_response_status(status=status.HTTP_500_INTERNAL_SERVER_ERROR, message=str(e))

@router.post("/check-out/{booking_id}")
async def check_out(token: str, booking_id: str):
    """
    ## Check out a guest from their booking.
    **booking_id**: รหัสการจองที่ต้องการเช็คเอาท์ (Format: BK-xxx)\n
    """
    try:
        payload = restaurant.check_out_booking(token=token, booking_id=booking_id)
        return success_response_status(status=status.HTTP_200_OK, payload=jsonable_encoder(payload))
    except Exception as e:
        raise error_response_status(status=status.HTTP_500_INTERNAL_SERVER_ERROR, message=str(e))