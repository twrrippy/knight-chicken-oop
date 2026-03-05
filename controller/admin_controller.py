from fastapi import APIRouter, status, HTTPException
from shared.utils.response import success_response_status, error_response_status
from main import restaurant_system, mcp
"""Admin Controller Routes include:
- Log Management: (Manager) call Central Log or Audit Trail
- Simulation Management: controlling the simulation speed (time acceleration) Expired or Booking
- Staff Management: manage staff's permissions and etc.
- System Settings: etc.
"""

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/get-logs")
async def get_logs():
    """retrieve all audit logs from the centralized logging system"""
    return {"logs": restaurant_system.__receipts}

@router.get("/get-all-members")
async def get_all_members():
    """show all members in the system"""
    return [
        {
            "member_id": m.id,
            "name": m.name,
            "tier": m.tier
        } for m in restaurant_system.__members
    ]

@router.get("/get-all-rooms")
async def get_all_rooms():
    """get all rooms in the system"""
    return [
        {
            "room_id": r.id,
            "name": r.type,
            "status": r.status,
            "price_per_hour": r.price_per_hour,
        } for r in restaurant_system.__room_list
    ]

@router.get("/get-all-staff")
async def get_all_staff():
    """get all staff"""
    return [
        {
            "staff_id": s.id,
            "name": s.name,
        } for s in restaurant_system.__staff_list
    ]