from typing import Union, Annotated, Optional
from pydantic import Field
from mcp_core import mcp
from main_system.restaurant import restaurant, Order
from main_system.utils.enum import ItemStatus
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/auth", tags=["Authentication"])

@mcp.tool
@router.post("/login")
async def login(
    username: Annotated[str, Field(description="ชื่อผู้ใช้งาน")], 
    password: Annotated[str, Field(description="รหัสผ่าน")]
):
    """
    Authenticate a user or staff member and retrieve an access token.
    """
    try:
        session = restaurant.login(username, password)
        token = session.token
        return {"access_token": token, "token_type": "bearer"}
    except Exception as e:
        return f"ไม่สามารถดำเนินการได้: {getattr(e, 'detail', str(e))}"
    
@mcp.tool
@router.post("/guest")
async def guest_login():
    """
    Create a guest session and retrieve an access token.
    """
    try:
        session = restaurant.add_guest_session()
        token = session.token
        return {"access_token": token, "token_type": "bearer"}
    except Exception as e:
        return f"ไม่สามารถดำเนินการได้: {getattr(e, 'detail', str(e))}"

@mcp.tool
@router.post("/logout")
async def logout(
    token: Annotated[str, Field(description="Token ที่ต้องการทำลาย")]
):
    """
    Invalidate the current access token and log out the user.
    """
    try:
        success = restaurant.logout(token)
        if success:
            return {"message": "Logged out successfully"}
        return f"ไม่สามารถดำเนินการได้: Invalid Token"
    except Exception as e:
        return f"ไม่สามารถดำเนินการได้: {getattr(e, 'detail', str(e))}"