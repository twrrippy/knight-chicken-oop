from datetime import timedelta
from main_system.utils.mcp_core import mcp
from main_system.utils.simulate import SimulationClock

@mcp.tool()
async def advance_time(
    minutes: int
):
    """
    Advance simulation time by a specified number of minutes.
    """
    new_time = SimulationClock.get_time() + timedelta(minutes=minutes)
    SimulationClock.set_time(new_time)
    return {"current_simulation_time": SimulationClock.get_time().strftime("%Y-%m-%d %H:%M:%S")}