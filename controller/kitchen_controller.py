from fastapi import APIRouter
from shared.utils.response import success_response_status, error_response_status

router = APIRouter(prefix="/kitchen", tags=["kitchen"])

# Example endpoint for kitchen status
@router.get("/status")
def get_kitchen_status():
    """
    Endpoint to get the current status of the kitchen.
    """
    # Placeholder logic for kitchen status
    kitchen_status = {
        "status": "operational",
        "active_orders": 5,
        "pending_orders": 2
    }
    return success_response_status(status=200, payload=kitchen_status)