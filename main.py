import dotenv
dotenv.load_dotenv()
import uvicorn
from fastapi import FastAPI, HTTPException
from mcp_core import mcp
from main_system.restaurant import restaurant
from controller.order_controller import router as order_router
from controller.resource_controller import router as resource_router
from controller.kitchen_controller import router as kitchen_router
from controller.payment_controller import router as payment_router
from controller.admin_controller import router as admin_router
from controller.booking_controller import router as booking_router
from controller.simulation_controller import router as simulation_router

app = FastAPI()

app.include_router(order_router)
app.include_router(resource_router)
app.include_router(kitchen_router)
app.include_router(payment_router)
app.include_router(admin_router)
app.include_router(booking_router)
app.include_router(simulation_router)
@mcp.tool()
@app.get("/menu", response_model=dict, tags=["Menu"])
async def get_menu():
    """
    ดึงรายการอาหารทั้งหมด
    """
    return restaurant.get_menu()

# # ==========================================
# # Mock Data Setup
# # ==========================================
from mock_data import initialize_mock_data

initialize_mock_data()
print("Mock Data Initialized comprehensively from mock_data.py")

# # ==========================================

if __name__ == "__main__":
    mcp.run()
    #uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)