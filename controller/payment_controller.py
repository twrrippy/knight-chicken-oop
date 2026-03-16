from typing import Optional, Dict, Any, Annotated
from pydantic import Field
from source.restaurant import restaurant
from source.utils.enum import UserRole
from source.utils.mcp_core import mcp

@mcp.tool
async def confirm_order_pay(
    token: Annotated[str, Field(
        description="Customer access token (obtained via 'login' tool or as guest)"
    )],
    order_id: Annotated[str, Field(
        description="Order ID to be paid (Expected format: ORD-xxx)"
    )],
    method: Annotated[str, Field(
        description='Payment method. Only supports "qrcode", "creditcard", or "cash"'
    )],
    coupon_code: Annotated[Optional[str], Field(
        description="Discount coupon code to use (if any)"
    )] = None,
    payment_details: Annotated[Dict[str, Any], Field(
        description='Additional required information depending on payment method: For qrcode, specify {"account_number": "xxx"}. For creditcard, specify {"card_number": "...", "cvv": "..."}. For cash, specify {"cash_received": xxx}.'
    )] = {}
):

    """
    Execute final payment and generate a receipt. CRITICAL: Do not guess parameters. You must explicitly ask the user for 'method' and 'payment_details' before executing this tool.
    """

    try:
        restaurant.check_order_customer(order_id=order_id, token=token, allowed_roles=[UserRole.MEMBER, UserRole.GUEST])
        result = restaurant.process_order_payment(order_id, coupon_code, method, payment_details)
        return result
    except Exception as e:
        return f"Unable to proceed: {getattr(e, 'detail', str(e))}"

@mcp.tool
async def preview_order_bill(
    token: Annotated[str, Field(
        description="Customer access token (obtained via 'login' tool or as guest)"
    )],
    order_id: Annotated[str, Field(
        description="Order ID to preview bill for (Expected format: ORD-xxx)"
    )],
    coupon_code: Annotated[Optional[str], Field(
        description="Discount coupon code to trial calculate before actual payment (if any)"
    )] = None
):

    """
    Calculate and preview the total bill for an order (subtotal, discounts, final price) before payment. This is a read-only action.
    """

    try:
        restaurant.check_order_customer(order_id=order_id, token=token, allowed_roles=[UserRole.MEMBER, UserRole.GUEST])
        result = restaurant.preview_order_bill(order_id, coupon_code)
        return result
    except Exception as e:
        return f"Unable to proceed: {getattr(e, 'detail', str(e))}"