from fastapi import APIRouter
from datetime import timedelta
from mcp_core import mcp
from main_system.utils.simulate import SimulationClock

router = APIRouter(prefix="/simulate", tags=["Simulation"])

@mcp.tool()
@router.post("/simulate/advance-time", tags=["Simulation"])
async def advance_time(
    minutes: int
):
    """
    ขยับเวลาไปยังอนาคต โดยรับเวลามาเป็นหน่วย นาที
    """
    new_time = SimulationClock.get_time() + timedelta(minutes=minutes)
    SimulationClock.set_time(new_time)
    return {"current_simulation_time": SimulationClock.get_time().strftime("%Y-%m-%d %H:%M:%S")}