from typing import Annotated
from pydantic import Field
from source.utils.mcp_core import mcp
from source.restaurant import restaurant

@mcp.tool
async def login(
    username: Annotated[str, Field(description="Username")], 
    password: Annotated[str, Field(description="Password")]
):
    """
    Authenticate a user or staff member and retrieve an access token.
    """
    try:
        session = restaurant.login(username, password)
        token = session.token
        return {"access_token": token, "token_type": "bearer"}
    except Exception as e:
        return f"Unable to proceed: {getattr(e, 'detail', str(e))}"
    
@mcp.tool
async def guest_login():
    """
    Create a guest session and retrieve an access token.
    """
    try:
        session = restaurant.add_guest_session()
        token = session.token
        return {"access_token": token, "token_type": "bearer"}
    except Exception as e:
        return f"Unable to proceed: {getattr(e, 'detail', str(e))}"

@mcp.tool
async def logout(
    token: Annotated[str, Field(description="Token to invalidate")]
):
    """
    Invalidate the current access token and log out the user.
    """
    try:
        success = restaurant.logout(token)
        if success:
            return {"message": "Logged out successfully"}
        return f"Unable to proceed: Invalid Token"
    except Exception as e:
        return f"Unable to proceed: {getattr(e, 'detail', str(e))}"