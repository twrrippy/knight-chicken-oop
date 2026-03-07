from fastapi import APIRouter, HTTPException, Query, status, Body
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime, timedelta

from fastapi.encoders import jsonable_encoder
from main_system.restaurant import restaurant
from shared.utils.response import success_response_status, error_response_status

router = APIRouter(prefix="/booking", tags=["Booking"])

# @mcp.tool
@router.post("/booking-room")
async def book_room(
    token: str,
    member_id: str, 
    room_id: str, 
    hours: int, 
    amount_paid: float,
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
        payload = restaurant.booking_room(token, member_id, room_id, hours, amount_paid, pay_method, start_time=start_time, payment_details=payment_details)
        return success_response_status(status= status.HTTP_200_OK,payload= jsonable_encoder(payload))
    except Exception as e:
        raise error_response_status(status= status.HTTP_500_INTERNAL_SERVER_ERROR, message=str(e))

# @mcp.tool
@router.get("/preview_booking/{booking_id}")
async def preview_booking(booking_id: str):
    """
    
    """
    return restaurant.preview_booking_details(booking_id)
