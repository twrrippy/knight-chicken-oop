from typing import Annotated
from pydantic import Field
from source.utils.mcp_core import mcp
from source.restaurant import restaurant
from source.utils.enum import UserRole

"""Admin Controller Routes include:
- Log Management: (Manager) call Central Log or Audit Trail
- Simulation Management: controlling the simulation speed (time acceleration) Expired or Booking
- Staff Management: manage staff's permissions and etc.
- System Settings: etc.
"""

@mcp.tool
async def get_all_receipts(
    token: Annotated[str, Field(
        description="Staff access token (obtained via the 'login' tool)"
    )]
):
    """
    Retrieve all payment receipts. Requires ADMIN access.
    """
    try:
        restaurant.verify_token_and_role(token, [UserRole.ADMIN])
        return [r.generate() for r in restaurant.get_all_receipts()]
    except Exception as e:
        return f"Unable to proceed: {getattr(e, 'detail', str(e))}"

@mcp.tool
async def get_all_members(
    token: Annotated[str, Field(
        description="Staff access token (obtained via the 'login' tool)"
    )]
):
    """
    Retrieve a list of all registered members. Requires ADMIN access.
    """
    try:
        restaurant.verify_token_and_role(token, [UserRole.ADMIN])
        return [
            {
                "member_id": m.id,
                "name": m.name,
                "tier": m.tier
            } for m in restaurant.get_all_members()
        ]
    except Exception as e:
        return f"Unable to proceed: {getattr(e, 'detail', str(e))}"

@mcp.tool
async def get_all_rooms(
    token: Annotated[str, Field(
        description="Staff access token (obtained via the 'login' tool)"
    )]
):
    """
    Retrieve all rooms and their current statuses. Requires Staff access.
    """
    try:
        restaurant.verify_token_and_role(token, [UserRole.ADMIN, UserRole.STAFF])
        return [
            {
                "room_id": r.id,
                "name": r.type,
                "status": r.status,
                "price_per_hour": r.price_per_hour,
            } for r in restaurant.get_all_rooms()
        ]
    except Exception as e:
        return f"Unable to proceed: {getattr(e, 'detail', str(e))}"

@mcp.tool
async def get_all_staff(
    token: Annotated[str, Field(
        description="Staff access token (obtained via the 'login' tool)"
    )]
):
    """
    Retrieve a list of all staff members. Requires ADMIN access.
    """
    try:
        restaurant.verify_token_and_role(token, [UserRole.ADMIN])
        return [
            {
                "staff_id": s.id,
                "name": s.name,
            } for s in restaurant.get_all_staff()
        ]
    except Exception as e:
        return f"Unable to proceed: {getattr(e, 'detail', str(e))}"

@mcp.tool
async def get_all_orders(
    token: Annotated[str, Field(
        description="Staff access token (obtained via the 'login' tool)"
    )]
):
    """
    Retrieve all orders in the system. Requires ADMIN access.
    """
    try:
        restaurant.verify_token_and_role(token, [UserRole.ADMIN])
        return [
            {
                "order_id": o.id,
                "customer": o.customer.name,
                "status": o.status.value,
            } for o in restaurant.get_all_orders()
        ]
    except Exception as e:
        return f"Unable to proceed: {getattr(e, 'detail', str(e))}"

@mcp.tool
async def get_all_bookings(
    token: Annotated[str, Field(
        description="Staff access token (obtained via the 'login' tool)"
    )]
):
    """
    Retrieve all room bookings. Requires ADMIN access.
    """
    try:
        restaurant.verify_token_and_role(token, [UserRole.ADMIN])
        return [
            {
                "booking_id": b.id,
                "customer": b.member.name,
                "room": b.room.type,
                "status": b.status.value,
                "time_slot": b.time_slot.start_time.strftime("%Y-%m-%d %H:00:00")
            } for b in restaurant.get_all_bookings()
        ]
    except Exception as e:
        return f"Unable to proceed: {getattr(e, 'detail', str(e))}"

@mcp.tool
async def member_sign_up(
    token: Annotated[str, Field(description="Staff access token (obtained via the 'login' tool)")],
    username: Annotated[str, Field(description="Username")], 
    password: Annotated[str, Field(description="Password")], 
    display_name: Annotated[str, Field(description="Display name to use")], 
    phone: Annotated[str, Field(description="Phone number, exactly 10 digits")]
):
    """
    Register a new member for new customers. Requires Staff access.
    """
    try:
        restaurant.verify_token_and_role(token, [UserRole.ADMIN, UserRole.STAFF])
        member = restaurant.register_member(username, password, display_name, phone)
        return {
            "message": "Welcome to Party Hub!",
            "your_id": member.id,
            "username": member.username,
            "tier": member.tier
        }
    except Exception as e:
        return f"Unable to proceed: {getattr(e, 'detail', str(e))}"

@mcp.tool
async def staff_sign_up(
    token: Annotated[str, Field(description="Staff access token (obtained via the 'login' tool)")],
    username: Annotated[str, Field(description="Username")], 
    password: Annotated[str, Field(description="Password")], 
    name: Annotated[str, Field(description="Staff name")], 
    phone: Annotated[str, Field(description="Phone number, exactly 10 digits")]
):
    """
    Register new staff. Requires ADMIN access.
    """
    try:
        restaurant.verify_token_and_role(token, [UserRole.ADMIN])
        staff = restaurant.register_staff(username, password, name, phone)
        return {
            "message": "Staff registered successfully",
            "staff_id": staff.id,
            "name": staff.name
        }
    except Exception as e:
        return f"Unable to proceed: {getattr(e, 'detail', str(e))}"

@mcp.tool
async def void_order(
    order_id: Annotated[str, Field(description="Order ID (Expected format: ORD-xxx)")],
    token: Annotated[str, Field(description="Staff access token (obtained via the 'login' tool)")]
):
    """
    Void an unpaid order. Requires ADMIN access.
    """
    try:
        restaurant.verify_token_and_role(token=token, allowed_roles=[UserRole.ADMIN])
        restaurant.void_order_from_id(order_id)
    except Exception as e:
        return f"Unable to proceed: {getattr(e, 'detail', str(e))}"
    return {"message": "Voided order successfully"}