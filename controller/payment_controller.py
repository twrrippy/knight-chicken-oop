from fastapi import APIRouter
from shared.utils.response import success_response_status, error_response_status

router = APIRouter(prefix="/payment", tags=["payment"])