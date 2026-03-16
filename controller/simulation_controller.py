from datetime import timedelta
from source.utils.mcp_core import mcp
from source.utils.simulate import SimulationClock

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

@mcp.tool()
async def get_current_time():
    """
    Get the current simulation time.
    """
    return {"current_simulation_time": SimulationClock.get_time().strftime("%Y-%m-%d %H:%M:%S")}