import dotenv
dotenv.load_dotenv()

from fastapi import FastAPI
from main_system.restaurant import Restaurant
from controller.order_controller import router as order_router
from controller.resource_controller import router as resource_router
from controller.kitchen_controller import router as kitchen_router
from controller.payment_controller import router as payment_router
from controller.admin_controller import router as admin_router
from controller.booking_controller import router as booking_router

app = FastAPI()
restaurant_system = Restaurant()

app.include_router(order_router)
app.include_router(resource_router)
app.include_router(kitchen_router)
app.include_router(payment_router)
app.include_router(admin_router)
app.include_router(booking_router)