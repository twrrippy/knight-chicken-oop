from fastapi import APIRouter
from shared.utils.response import success_response_status, error_response_status

"""
Resource Controller Module
- inventory Management: manage stock levels, add or remove ingredients
- menu Management: add, update, or remove menu items
"""

router = APIRouter(prefix="/resource", tags=["resource"])