from typing import Union, Annotated, Optional
from pydantic import Field
from mcp_core import mcp
from main_system.restaurant import restaurant, Order
from main_system.utils.enum import ItemStatus, UserRole
from fastapi import APIRouter, HTTPException

"""Admin Controller Routes include:
- Log Management: (Manager) call Central Log or Audit Trail
- Simulation Management: controlling the simulation speed (time acceleration) Expired or Booking
- Staff Management: manage staff's permissions and etc.
- System Settings: etc.
"""

router = APIRouter(prefix="/admin")

@mcp.tool
@router.get("/get-all-receipts", tags=["Data"])
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
@router.get("/get-all-members", tags=["Data"])
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
@router.get("/get-all-rooms", tags=["Data"])
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
@router.get("/get-all-staff", tags=["Data"])
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
@router.get("/get-all-orders", tags=["Data"])
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
@router.get("/get-all-bookings", tags=["Data"])
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
@router.post("/register/member", tags=["Registration"])
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
@router.post("/register/staff", tags=["Registration"])
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

# @mcp.tool
# @router.get("/queue/check", tags=["Queue"])
# async def check_queue(
#     token: Annotated[str, Field(description="Staff access token (obtained via the 'login' tool)")]
# ):
#     """
#     ดูจำนวนคิวของออเดอร์ที่จ่ายเงินแล้ว และกำลังทำ ต้องการสิทธ์พนักงาน
#     """
#     try:
#         restaurant.verify_token_and_role(token, [UserRole.ADMIN, UserRole.STAFF])
#         return {"Queue": restaurant.check_queue}
#     except Exception as e:
#         return f"Unable to proceed: {getattr(e, 'detail', str(e))}"

# @mcp.tool
# @router.get("/queue/get/{queue_order}", response_model=Union[Order.OrderDTO, dict], tags=["Queue"])
# async def get_queue(
#     token: Annotated[str, Field(description="Staff access token (obtained via the 'login' tool)")],
#     queue_order: Annotated[int, Field(description="หมายเลขคิว ตามลำดับ 1-50")]
# ):
#     """
#     ดูรายละเอียดออเดอร์ในคิว ต้องการสิทธ์พนักงาน
#     """
#     try:
#         restaurant.verify_token_and_role(token, [UserRole.ADMIN, UserRole.STAFF])
#         if queue_order > 50 or queue_order < 1:
#             return f"Unable to proceed: Queue not Found"
#         order = restaurant.get_queue(queue_order)
#         if order == False:
#             return f"Unable to proceed: Queue not Found"
#         return order.order_to_dict()
#     except Exception as e:
#         return f"Unable to proceed: {getattr(e, 'detail', str(e))}"

@mcp.tool
@router.put("/order/void", tags=["Order"])
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