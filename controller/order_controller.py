from fastapi import APIRouter, HTTPException
from shared.utils.response import success_response_status, error_response_status
"""
Order Controller Module
- delivery Management: track and update delivery statuses
- dinein Management: handle table reservations and seating arrangements
- event Management: organize special events and promotions
"""
router = APIRouter(prefix="/order", tags=["order"])