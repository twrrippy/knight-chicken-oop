from typing import Optional, Dict, Any, Annotated
from datetime import datetime
from pydantic import Field
from main_system.utils.mcp_core import mcp
from main_system.restaurant import restaurant
from main_system.utils.enum import UserRole

@mcp.tool
async def check_booking_availability(
    token: Annotated[str, Field(
        description="Staff access token (obtained via the 'login' tool)"
    )],
    room_id: Annotated[str, Field(
        description="Room ID to book, obtained via the 'get_all_rooms' tool"
    )],
    start_time: Annotated[datetime, Field(
        description="Start date and time (Format: YYYY-MM-DD HH:MM:SS)"
    )],
    hours: Annotated[int, Field(
        description="Number of hours to book (Integer)"
    )]
):
    """
    Check the availability of a room for a specific time period.
    """
    try:
        staff = restaurant.verify_token_and_role(token, allowed_roles=[UserRole.ADMIN, UserRole.STAFF])
        room = restaurant.get_room(room_id)
        is_available = restaurant.is_slot_avaliable(room, start_time, hours)
        return {"room_id": room_id,
                 "is_available": is_available,
                 "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"), 
                 "deposit_required": f"{room.price_per_hour * hours * 0.5} THB with no discount"
                }
    except Exception as e:
        return f"Unable to proceed: {getattr(e, 'detail', str(e))}"

@mcp.tool
async def book_room(
    token: Annotated[str, Field(
        description="Staff access token (obtained via the 'login' tool)"
    )],
    member_id: Annotated[str, Field(
        description="Member ID (Format: M-xxx)"
    )], 
    room_id: Annotated[str, Field(
        description="Room ID to book, obtained via the 'get_all_rooms' tool"
    )], 
    start_time: Annotated[datetime, Field(
        description="Start date and time (Format: YYYY-MM-DD HH:MM:SS)"
    )],
    hours: Annotated[int, Field(
        description="Number of hours to book (Integer)"
    )], 
    pay_method: Annotated[str, Field(
        description='Payment method. Only supports "qrcode", "creditcard", or "cash"'
    )],
    payment_details: Annotated[Dict[str, Any], Field(
        description='Additional required information depending on payment method: For qrcode, specify {"account_number": "xxx"}. For creditcard, specify {"card_number": "...", "cvv": "..."}. For cash, specify {"cash_received": xxx}.'
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
        return f"Unable to proceed: {getattr(e, 'detail', str(e))}"

@mcp.tool
async def preview_booking(
    token: Annotated[str, Field(
        description="Staff access token (obtained via the 'login' tool)"
    )],
    booking_id: Annotated[str, Field(
        description="Booking ID (Format: BK-xxx)"
    )]
):
    """
    Preview booking details. Requires Staff access.
    """
    try:
        restaurant.verify_token_and_role(token, [UserRole.ADMIN, UserRole.STAFF])
        return restaurant.preview_booking_details(booking_id)
    except Exception as e:
        return f"Unable to proceed: {getattr(e, 'detail', str(e))}"

@mcp.tool
async def check_in(token: str,
        order_id: Annotated[str, Field(
        description="Order ID (Format: ORD-xxx)"
    )], 
        booking_id: Annotated[str, Field(
        description="Booking ID (Format: BK-xxx)"
    )], 
        pay_method: Annotated[str, Field(
        description='Payment method. Only supports "qrcode", "creditcard", or "cash"'
    )], 
        coupon_code: Annotated[Optional[str], Field(
        description="Discount coupon code to use (if any)"
    )] = None, 
        payment_details: Annotated[Dict[str, Any], Field(
        description='Additional required information depending on payment method: For qrcode, specify {"account_number": "xxx"}. For creditcard, specify {"card_number": "...", "cvv": "..."}. For cash, specify {"cash_received": xxx}.'
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
        return f"Unable to proceed: {getattr(e, 'detail', str(e))}"

@mcp.tool
async def check_out(
    token: Annotated[str, Field(
        description="Staff access token performing the action"
    )], 
    booking_id: Annotated[str, Field(
        description="Booking ID to check out (Format: BK-xxx)"
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
        return f"Unable to proceed: {getattr(e, 'detail', str(e))}"

@mcp.tool
async def cancel_booking(
    token: Annotated[str, Field(
        description="Staff access token performing the action"
    )], 
    booking_id: Annotated[str, Field(
        description="Booking ID to cancel (Format: BK-xxx)"
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
        return f"Unable to proceed: {getattr(e, 'detail', str(e))}"
