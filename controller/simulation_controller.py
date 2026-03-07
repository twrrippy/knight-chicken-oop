from fastapi import APIRouter, status, HTTPException
from shared.utils.response import success_response_status, error_response_status
from datetime import timedelta
from mcp_core import mcp
from shared.utils.simulate import SimulationClock
from typing import Annotated
from pydantic import Field

router = APIRouter(prefix="/simulate", tags=["Simulation"])

@mcp.tool()
@router.post("/advance-time", tags=["Simulation"])
async def advance_time(
    minutes: Annotated[int, Field(
        description="จำนวนนาทีที่ต้องการให้เวลาในระบบขยับไปข้างหน้า"
    )]
):
    """
    Advance the system simulation clock by a specific number of minutes (e.g., to simulate cooking time passing or coupon expiration).
    """
    new_time = SimulationClock.get_time() + timedelta(minutes=minutes)
    SimulationClock.set_time(new_time)
    return {"current_simulation_time": SimulationClock.get_time().strftime("%Y-%m-%d %H:%M:%S")}