from fastapi import APIRouter
from fastmcp import FastMCP
from typing import Optional, List, Tuple, Dict, Any

from main import restaurant_system
from shared.utils.response import success_response_status, error_response_status

router = APIRouter(prefix="/booking", tags=["booking"])
mcp = FastMCP()

@mcp.tool
@router.get("/booking/preview_booking/{booking_id}")
async def preview_booking(booking_id: str):
    """
    
    """
    return restaurant_system.preview_booking_details(booking_id)

@mcp.tool
@router.post("/booking/pay_deposit/{booking_id}")
async def pay_deposit(booking_id: str, method: str, payment_details: Dict[str, Any]):
    """
    
    """
    return restaurant_system.process_pay_deposit(booking_id, method, payment_details)