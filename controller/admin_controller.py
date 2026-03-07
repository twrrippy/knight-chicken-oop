from typing import Optional

from fastapi import APIRouter, Query, status, HTTPException
from shared.utils.response import success_response_status, error_response_status
from main_system.enum import ItemStatus
from main_system.restaurant import Order
from typing import Union
# from main import restaurant_system, 
from main_system.restaurant import restaurant, Order
"""Admin Controller Routes include:
- Log Management: (Manager) call Central Log or Audit Trail
- Simulation Management: controlling the simulation speed (time acceleration) Expired or Booking
- Staff Management: manage staff's permissions and etc.
- System Settings: etc.
"""

router = APIRouter(prefix="/admin")

@router.get("/get-logs", tags=["Data"])
async def get_logs():
    """retrieve all audit logs from the centralized logging system"""
    return {"logs": restaurant.get_all_receipts}

@router.get("/get-all-members", tags=["Data"])
async def get_all_members():
    """show all members in the system"""
    return [
        {
            "member_id": m.id,
            "name": m.name,
            "tier": m.tier
        } for m in restaurant.get_all_members()
    ]

@router.get("/get-all-rooms", tags=["Data"])
async def get_all_rooms():
    """get all rooms in the system"""
    return [
        {
            "room_id": r.id,
            "name": r.type,
            "status": r.status,
            "price_per_hour": r.price_per_hour,
        } for r in restaurant.get_all_rooms()
    ]

@router.get("/get-all-staff", tags=["Data"])
async def get_all_staff():
    """get all staff"""
    return [
        {
            "staff_id": s.id,
            "name": s.name,
        } for s in restaurant.get_all_staff()
    ]

@router.get("/get-all-orders", tags=["Data"])
async def get_all_orders():
    """get all orders in the system"""
    return [
        {
            "order_id": o.id,
            "customer": o.customer.name,
            "status": o.status.value,
        } for o in restaurant.get_all_orders()
    ]

@router.get("/get-all-bookings", tags=["Data"])
async def get_all_bookings():
    """get all bookings in the system"""
    return [
        {
            "booking_id": b.id,
            "customer": b.member.name,
            "room": b.room.type,
            "status": b.status.value,
            "time_slot": b.time_slot.start_time.strftime("%Y-%m-%d %H:00:00")
        } for b in restaurant.get_all_bookings()
    ]

@router.post("/auth/login", tags=["Authentication"])
async def login(username: str, password: str):
    """เข้าสู่ระบบด้วย username และ password เพื่อรับ Token"""
    token = restaurant.login(username, password)
    return {"access_token": token, "token_type": "bearer"}

@router.post("/auth/logout", tags=["Authentication"])
async def logout(token: str = Query(...)):
    """ออกจากระบบและทำลาย Token"""
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
    order = restaurant.get_queue()
    if order == False:
        raise HTTPException(status_code=400, detail="Queue not Found")
    return order.order_to_dict(restaurant)
