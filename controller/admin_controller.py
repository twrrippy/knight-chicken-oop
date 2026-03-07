from typing import Union, Annotated, Optional
from pydantic import Field
from mcp_core import mcp
from main_system.restaurant import restaurant, Order
from fastapi import APIRouter

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
        description="Token ของพนักงาน (ได้จากการเรียกใช้ tool login)"
    )]
):
    """
    Retrieve all payment receipts. Requires ADMIN access.
    """
    restaurant.verify_token_and_role(token, ["Admin"])
    return [r.generate() for r in restaurant.get_all_receipts()]

@mcp.tool
@router.get("/get-all-members", tags=["Data"])
async def get_all_members(
    token: Annotated[str, Field(
        description="Token ของพนักงาน (ได้จากการเรียกใช้ tool login)"
    )]
):
    """
    Retrieve a list of all registered members. Requires ADMIN access.
    """
    restaurant.verify_token_and_role(token, ["Admin"])
    return [
        {
            "member_id": m.id,
            "name": m.name,
            "tier": m.tier
        } for m in restaurant.get_all_members()
    ]

@mcp.tool
@router.get("/get-all-rooms", tags=["Data"])
async def get_all_rooms(
    token: Annotated[str, Field(
        description="Token ของพนักงาน (ได้จากการเรียกใช้ tool login)"
    )]
):
    """
    Retrieve all rooms and their current statuses. Requires ADMIN access.
    """
    restaurant.verify_token_and_role(token, ["Admin"])
    return [
        {
            "room_id": r.id,
            "name": r.type,
            "status": r.status,
            "price_per_hour": r.price_per_hour,
        } for r in restaurant.get_all_rooms()
    ]

@mcp.tool
@router.get("/get-all-staff", tags=["Data"])
async def get_all_staff(
    token: Annotated[str, Field(
        description="Token ของพนักงาน (ได้จากการเรียกใช้ tool login)"
    )]
):
    """
    Retrieve a list of all staff members. Requires ADMIN access.
    """
    restaurant.verify_token_and_role(token, ["Admin"])
    return [
        {
            "staff_id": s.id,
            "name": s.name,
        } for s in restaurant.get_all_staff()
    ]


@mcp.tool
@router.get("/get-all-orders", tags=["Data"])
async def get_all_orders(
    token: Annotated[str, Field(
        description="Token ของพนักงาน (ได้จากการเรียกใช้ tool login)"
    )]
):
    """
    Retrieve all orders in the system. Requires ADMIN access.
    """
    restaurant.verify_token_and_role(token, ["Admin"])
    return [
        {
            "order_id": o.id,
            "customer": o.customer.name,
            "status": o.status.value,
        } for o in restaurant.get_all_orders()
    ]

@mcp.tool
@router.get("/get-all-bookings", tags=["Data"])
async def get_all_bookings(
    token: Annotated[str, Field(
        description="Token ของพนักงาน (ได้จากการเรียกใช้ tool login)"
    )]
):
    """
    Retrieve all room bookings. Requires ADMIN access.
    """
    restaurant.verify_token_and_role(token, ["Admin"])
    return [
        {
            "booking_id": b.id,
            "customer": b.member.name,
            "room": b.room.type,
            "status": b.status.value,
            "time_slot": b.time_slot.start_time.strftime("%Y-%m-%d %H:00:00")
        } for b in restaurant.get_all_bookings()
    ]

@mcp.tool
@router.post("/auth/login", tags=["Authentication"])
async def login(
    username: Annotated[str, Field(description="ชื่อผู้ใช้งาน")], 
    password: Annotated[str, Field(description="รหัสผ่าน")]
):
    """
    Authenticate a user or staff member and retrieve an access token.
    """
    session = restaurant.login(username, password)
    token = session.token
    return {"access_token": token, "token_type": "bearer"}


@mcp.tool
@router.post("/auth/logout", tags=["Authentication"])
async def logout(
    token: Annotated[str, Field(description="Token ที่ต้องการทำลาย")]
):
    """
    Invalidate the current access token and log out the user.
    """
    success = restaurant.logout(token)
    if success:
        return {"message": "Logged out successfully"}
    raise HTTPException(status_code=400, detail="Invalid Token")

@router.post("/register/member", tags=["Registration"])
async def member_sign_up(
    username: str, 
    password: str, 
    display_name: str, 
    phone: Optional[str] = None
):
    """ลงทะเบียนลูกค้าใหม่: ระบบจะ Generate ID และตั้ง Tier เป็น Bronze ให้เอง"""
    member = restaurant.register_member(username, password, display_name, phone)
    return {
        "message": "Welcome to Party Hub!",
        "your_id": member.id,
        "username": member.username,
        "tier": member.tier
    }

@router.post("/register/staff", tags=["Registration"])
async def staff_sign_up(username: str, password: str, name: str, phone: str = "0000000000"):
    """ลงทะเบียนพนักงานใหม่: ระบบจะ Generate ID (S-xxx) ให้อัตโนมัติ"""
    staff = restaurant.register_staff(username, password, name, phone)
    return {
        "message": "Staff registered successfully",
        "staff_id": staff.id,
        "name": staff.name
    }

@router.get("/stock/check/{item_name}", tags=["Stock"])
async def get_stock(item_name: str):
    item_available = restaurant.check_stock(item_name, ItemStatus.AVAILABLE)
    item_reserved = restaurant.check_stock(item_name, ItemStatus.RESERVED)
    return {
        "Available": item_available,
        "Reserved": item_reserved
    }

@router.get("/queue/check", tags=["Queue"])
async def check_queue():
    return { "Queue": restaurant.check_queue}

@router.get("/queue/get/{queue_order}", response_model=Union[Order.OrderDTO, dict], tags=["Queue"])
async def get_queue(queue_order: int):
    if queue_order > 50 or queue_order < 1:
        raise HTTPException(status_code=400, detail="Queue not Found")
    order = restaurant.get_queue(queue_order)
    if order == False:
        raise HTTPException(status_code=400, detail="Queue not Found")
    return order.order_to_dict()
