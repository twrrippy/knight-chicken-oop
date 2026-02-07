from fastapi import APIRouter, status
from shared.utils.response import success_response_status, error_response_status

"""Admin Controller Routes include:
- Log Management: (Manager) call Central Log or Audit Trail
- Simulation Management: controlling the simulation speed (time acceleration) Expired or Booking
- Staff Management: manage staff's permissions and etc.
- System Settings: etc.
"""

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/logs")
async def get_logs():
    try:
        return success_response_status(status.HTTP_200_OK, {"message": "Retrieve system logs"})
    except Exception as e:
        raise error_response_status(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))