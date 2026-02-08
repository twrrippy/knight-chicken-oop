import dotenv
dotenv.load_dotenv()

from fastapi import FastAPI
from controller.order_controller import router as order_router
from controller.resource_controller import router as resource_router
from controller.kitchen_controller import router as kitchen_router
from controller.payment_controller import router as payment_router
from controller.admin_controller import router as admin_router

app = FastAPI()

# app.include_router(order_router)
# app.include_router(resource_router)
# app.include_router(kitchen_router)
# app.include_router(payment_router)
app.include_router(admin_router)