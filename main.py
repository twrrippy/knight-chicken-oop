import dotenv
dotenv.load_dotenv()

from fastapi import FastAPI
from fastmcp import FastMCP
from main_system.restaurant import restaurant
from controller.order_controller import router as order_router
from controller.resource_controller import router as resource_router
from controller.kitchen_controller import router as kitchen_router
from controller.payment_controller import router as payment_router
from controller.admin_controller import router as admin_router
from controller.booking_controller import router as booking_router

from shared.utils.simulate import SimulationClock
from datetime import timedelta

app = FastAPI()
mcp = FastMCP()

app.include_router(order_router)
app.include_router(resource_router)
app.include_router(kitchen_router)
app.include_router(payment_router)
app.include_router(admin_router)
app.include_router(booking_router)


@app.post("/simulate/advance-time", tags=["Simulation"])
async def advance_time(minutes: int):
    """advance the simulation clock by specified minutes"""
    new_time = SimulationClock.get_time() + timedelta(minutes=minutes)
    SimulationClock.set_time(new_time)
    return {"current_simulation_time": SimulationClock.get_time()}

# # ==========================================
# # Mock Data Setup
# # ==========================================

# restaurant_system = restaurant
