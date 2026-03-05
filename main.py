import dotenv
dotenv.load_dotenv()

from fastapi import FastAPI, HTTPException
from fastmcp import FastMCP
from main_system.restaurant import restaurant
from controller.order_controller import router as order_router
from controller.resource_controller import router as resource_router
from controller.kitchen_controller import router as kitchen_router
from controller.payment_controller import router as payment_router
from controller.admin_controller import router as admin_router
from controller.booking_controller import router as booking_router

from datetime import timedelta
import uvicorn
from shared.utils.simulate import SimulationClock


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

@app.get("/menu", response_model=dict, tags=["Menu"])
async def get_menu():
    return restaurant.get_menu()

# # ==========================================
# # Mock Data Setup
# # ==========================================



if __name__ == "__main__":
    uvicorn.run("main:app",host="127.0.0.1",port=8000,reload=True)