from fastapi import APIRouter, status, HTTPException
from shared.utils.response import success_response_status, error_response_status
from main import restaurant_system, mcp

router = APIRouter(prefix="/simulate", tags=["simulation"])

@app.post("/simulate/advance-time", tags=["Simulation"])
async def advance_time(minutes: int):
    """advance the simulation clock by specified minutes"""
    new_time = SimulationClock.get_time() + timedelta(minutes=minutes)
    SimulationClock.set_time(new_time)
    return {"current_simulation_time": SimulationClock.get_time()}
