from fastapi import APIRouter
from main_system.restaurant import restaurant, Order, OrderItem, Guest
from main_system.utils.enum import UserRole
from typing import Union, Annotated
import uuid
from mcp_core import mcp
from pydantic import Field
from main_system.utils.enum import DeliveryStatus

"""
Order Controller Module
- delivery Management: track and update delivery statuses
- dinein Management: handle table reservations and seating arrangements
- event Management: organize special events and promotions
"""
router = APIRouter(prefix="/order", tags=["Order"])


@mcp.tool
@router.post("/start/general")
async def start_general_order(
    token: Annotated[str, Field(
        description="Customer access token (obtained via 'login' tool or as guest)"
    )]
):
    """
    Start ordering food for a customer. Requires Member or Guest access.
    """
    try:
        current_customer = restaurant.verify_token_and_role(token=token, allowed_roles=[UserRole.MEMBER, UserRole.GUEST])
        return restaurant.create_general_order(current_customer)
        
    except Exception as e:
        return f"Unable to proceed: {getattr(e, 'detail', str(e))}"

@mcp.tool()
@router.post("/start/delivery")
async def start_delivery_order(
    token: Annotated[str, Field(
        description="Customer access token (obtained via 'login' tool or as guest)"
    )],
    provider_name: Annotated[str, Field(
        description="Delivery Provider name, e.g., Grab, LineMan, ShopeeFood"
    )],
    distance: Annotated[float, Field(
        description="Distance from restaurant to customer (kilometers)"
    )]
):
    """
    Start ordering food via Delivery for a customer. Requires Member or Guest access.
    """
    try:
        current_customer = restaurant.verify_token_and_role(token=token, allowed_roles=[UserRole.MEMBER, UserRole.GUEST])
        return restaurant.create_delivery_order(current_customer, provider_name, distance)
    except Exception as e:
        return f"Unable to proceed: {getattr(e, 'detail', str(e))}"

@mcp.tool  
@router.put("/orderitem/add")
async def add_item_to_order(
    token: Annotated[str, Field(
        description="Customer access token (obtained via 'login' tool or as guest)"
    )],
    order_id: Annotated[str, Field(
        description="Order ID (Expected format: ORD-xxx)"
    )], 
    menu: Annotated[str, Field(
        description="Menu item name, obtained via the 'get_menu' tool"
    )], 
    quantity: Annotated[int, Field(
        description="Quantity of food to add (1 or more)"
    )]
):
    """
    Add a menu item with quantity to an existing order.
    """
    try:
        current_order = restaurant.check_order_customer(order_id=order_id, token=token, allowed_roles=[UserRole.MEMBER, UserRole.GUEST])
        return restaurant.add_item_in_order(current_order, menu, quantity)
    except Exception as e:
        return f"Unable to proceed: {getattr(e, 'detail', str(e))}"

@mcp.tool
@router.put("/orderitem/remove")
async def remove_item_in_order(
    token: Annotated[str, Field(
        description="Customer access token (obtained via 'login' tool or as guest)"
    )],
    order_id: Annotated[str, Field(
        description="Order ID (Expected format: ORD-xxx)"
    )], 
    order_item_id: Annotated[int, Field(
        description="Index of the menu item (order_item) to remove from the order"
    )]
):
    """
    Remove a food item (OrderItem) from an existing order (Order).
    """
    try:
        current_order = restaurant.check_order_customer(order_id=order_id, token=token, allowed_roles=[UserRole.MEMBER, UserRole.GUEST])
        return restaurant.remove_item_in_order(current_order, order_item_id)
    except Exception as e:
        return f"Unable to proceed: {getattr(e, 'detail', str(e))}"

@mcp.tool
@router.put("/orderitem/custom")
async def custom_item_in_order(
    token: Annotated[str, Field(
        description="Customer access token (obtained via 'login' tool or as guest)"
    )],
    order_id: Annotated[str, Field(
        description="Order ID (Expected format: ORD-xxx)"
    )], 
    order_item_id: Annotated[int, Field(
        description="Index of the menu item (order_item) to customize in the order"
    )], 
    item_name: Annotated[str, Field(
        description="Name of the item to modify"
    )], 
    quantity: Annotated[int, Field(
        description="Desired quantity of the item"
    )]
):
    """
    Customize the ingredient of a menu item in an Order.
    """
    # """
    # [Intent]: Customize a customizable ingredient of a menu item in an Order\n
    # [Logic]: Used for SingleMenuItem type menus inherited from MenuItem\n
    # [State Change]: Search Order by ID and call `current_order.custom()` to adjust the ingredient quantity (with item name item_name) of SingleMenuItem in the OrderItem with that order_item_id\n
    # """
    try:
        current_order = restaurant.check_order_customer(order_id=order_id, token=token, allowed_roles=[UserRole.MEMBER, UserRole.GUEST])
        return restaurant.custom_item_in_order(order=current_order, order_item_id=order_item_id, item_name=item_name, quantity=quantity)
    except Exception as e:
        return f"Unable to proceed: {getattr(e, 'detail', str(e))}"
    return current_order.order_to_dict()
    

@mcp.tool
@router.put("/ordering")
async def check_and_reserve_stock(
    order_id: Annotated[str, Field(
        description="Order ID (Expected format: ORD-xxx)"
    )], 
    token: Annotated[str, Field(
        description="Customer access token (obtained via 'login' tool or as guest)"
    )]
):
    """
    Pre-order step for members to reserve ingredients/products before confirmation.
    """
    try:
        current_order = restaurant.check_order_customer(order_id=order_id, token=token, allowed_roles=[UserRole.MEMBER, UserRole.GUEST])
        return restaurant.reserve(current_order)
    except Exception as e:
        return f"Unable to proceed: {getattr(e, 'detail', str(e))}"

@mcp.tool
@router.put("/confirm")
async def confirm_order(
    order_id: Annotated[str, Field(
        description="Order ID (Expected format: ORD-xxx)"
    )], 
    token: Annotated[str, Field(
        description="Customer access token (obtained via 'login' tool or as guest)"
    )]
):
    """
    Final confirmation of the order for members (after successful reservation).
    """
    try:
        current_order = restaurant.check_order_customer(order_id=order_id, token=token, allowed_roles=[UserRole.MEMBER, UserRole.GUEST])
        return restaurant.confirm(current_order)
    except Exception as e:
        return f"Unable to proceed: {getattr(e, 'detail', str(e))}"

@mcp.tool
@router.put("/serve", response_model=Union[Order.OrderDTO, dict])
async def serve(
    order_id: Annotated[str, Field(
        description="Order ID to be served (Format: ORD-xxx)"
    )],
    token: Annotated[str, Field(
        description="Staff access token (obtained via the 'login' tool)"
    )]
):
    """
    Update status Order. Changes the order status from Ready to Served. 
    """
    try:
        restaurant.verify_token_and_role(token,[UserRole.ADMIN,UserRole.STAFF])
        return restaurant.serve_order(order_id)
    except Exception as e:
        return f"Unable to proceed: {getattr(e, 'detail', str(e))}"

@router.get("/{order_id}")
async def get_order_from_id(order_id: str):
    current_order = restaurant.search_order_from_id(order_id)
    return current_order.order_to_dict()

@mcp.tool()
async def update_delivery_status(
    token: Annotated[str, Field(
        description="Staff access token (obtained via the 'login' tool)"
    )],
    order_id: Annotated[str, Field(
        description="Order ID of the delivery_order"
    )],
    new_status: Annotated[DeliveryStatus, Field(
        description="New status to change to, e.g., Driver Assigned, Delivered, Canceled"
    )]
):
    """
    Update the status of a delivery_order.
    """
    try:
        restaurant.verify_token_and_role(token, [UserRole.ADMIN, UserRole.STAFF])
        return restaurant.update_delivery_status(order_id, new_status)
    except Exception as e:
        return f"Unable to proceed: {getattr(e, 'detail', str(e))}"

