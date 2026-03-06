from fastapi import APIRouter, status, HTTPException
from shared.utils.response import success_response_status, error_response_status
from mcp_core import mcp
from datetime import timedelta
import uvicorn
from shared.utils.simulate import SimulationClock

router = APIRouter(prefix="/simulate", tags=["simulation"])


@mcp.tool()
@router.post("/advance-time")
async def advance_time(minutes: int):
    """
    ขยับเวลาไปยังอนาคต โดยรับเวลามาเป็นหน่วย นาที
    """
    new_time = SimulationClock.get_time() + timedelta(minutes=minutes)
    SimulationClock.set_time(new_time)
    return {"current_simulation_time": SimulationClock.get_time()}
