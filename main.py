import dotenv
dotenv.load_dotenv()

from fastapi import FastAPI, HTTPException
from mcp_core import mcp
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

app.include_router(order_router)
app.include_router(resource_router)
app.include_router(kitchen_router)
app.include_router(payment_router)
app.include_router(admin_router)
app.include_router(booking_router)

@mcp.tool()
@app.post("/simulate/advance-time", tags=["Simulation"])
async def advance_time(minutes: int):
    """
    ขยับเวลาไปยังอนาคต โดยรับเวลามาเป็นหน่วย นาที
    """
    new_time = SimulationClock.get_time() + timedelta(minutes=minutes)
    SimulationClock.set_time(new_time)
    return {"current_simulation_time": SimulationClock.get_time()}

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
from actor.staff import Staff
from actor.customer import Member, PercentCoupon, FixedAmountCoupon
from main_system.enum import MemberTier, OrderType, OrderStatus
from main_system.order.order import Order
from main_system.menu.menu_item import SingleMenuItem
from main_system.external_platform.payment_method import Cash, QRCode

# 1. Staff
mock_staff = Staff("S-001", "Alice", "0801234567", "alice", "password")
restaurant.add_staff(mock_staff)

# 2. Member
mock_member = Member("M-001", "Bob Customer", MemberTier.GOLD, "bob", "password", "0812345678")
restaurant.add_member(mock_member)

# 3. Menu Item
mock_menu = SingleMenuItem("Fried Chicken", 150.0, timedelta(minutes=15), [])
restaurant.add_menu(mock_menu)

# 4. Order
mock_order = Order("ORD-001", OrderType.GENERAL, mock_member)
if not hasattr(mock_order, "_Order__order_item_list"):
    mock_order._Order__order_item_list = []
mock_order.add_order_item(mock_menu, 2) # Total 300
mock_order.status = OrderStatus.PENDING
restaurant.add_order(mock_order)

# 5. Coupons
mock_coupon1 = PercentCoupon("CPN-01", "DISCOUNT20", 200.0, 20.0) # 20% off
mock_coupon2 = FixedAmountCoupon("CPN-02", "MINUS50", 100.0, 50.0) # 50 THB off
mock_member.add_coupon(mock_coupon1)
mock_member.add_coupon(mock_coupon2)

# 6. Payment Methods
restaurant.add_payment_method(Cash("PAY-01", "cash"))
restaurant.add_payment_method(QRCode("PAY-02", "qrcode"))

print("Mock Data Initialized - Order: ORD-001, Staff: S-001")
# # ==========================================

if __name__ == "__main__":
    mcp.run()
    #uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)