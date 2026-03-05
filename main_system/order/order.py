from main_system.menu.menu_item import MenuItem
from main_system.order.order_extention.booking import Booking
from main_system.order.order_extention.delivery import Delivery
from actor.customer import Customer, Coupon, Member, CouponStatus
from main_system.external_platform.payment_method import PaymentMethod
from main_system.enum import OrderStatus, OrderType
from fastapi import HTTPException
from typing import TYPE_CHECKING, Optional, List, Dict, Any

if TYPE_CHECKING:
    from main_system.log.receipt import Receipt

class OrderItem:
    def __init__(self, menu_item: MenuItem, quantity: int):
        self.__menu_item = menu_item
        self.__quantity = quantity
    @property
    def menu_item(self): return self.__menu_item
    @property
    def quantity(self): return self.__quantity
    @property
    def price(self): return self.__menu_item.price * self.__quantity

    def get_details(self) -> Dict[str, Any]:
        return {
            "name": self.menu_item.name,
            "quantity": self.quantity,
            "price": self.menu_item.price
        }
    
class Order:
    def __init__(self, order_id: str, customer: Customer):
        self.__id = order_id
        self.__customer: Customer = customer
        self.__order_list: List[OrderItem] = []
        self.__status = OrderStatus.PENDING
        self.__coupon_used: Optional[Coupon] = None
        self.__booking: Optional[Booking] = None
        self.__delivery: Optional[Delivery] = None
        self.__subtotal = 0.0
        self.__discount = 0.0
        self.__final_price = 0.0

    def add_item(self, item: OrderItem):
        self.__order_list.append(item)

    def add_booking(self, booking: Booking):
        if self.booking: raise HTTPException(409, "Booking Already Exists")
        self.__booking = booking

    def add_delivery(self, delivery: Delivery):
        if self.delivery: raise HTTPException(409, "Delivery Already Exists")
        self.__delivery = delivery

    def pre_calculate_totals(self, coupon_code: Optional[str] = None):
        coupon = None
        if coupon_code:
            if isinstance(self.customer, Member):
                coupon = self.customer.get_coupon_by_code(coupon_code)
            else:
                raise HTTPException(409, "Only members can use coupons")
        
        subtotal = sum(item.price for item in self.order_item)
        deposit = 0.0

        if self.booking:
            subtotal += self.booking.full_price
            deposit = self.booking.deposit

        if self.delivery:
            subtotal += self.delivery.fee

        coupon_discount = 0.0
        if coupon:
             if coupon.status != CouponStatus.AVAILABLE:
                raise HTTPException(409, "Coupon Not Available")
             coupon_discount = coupon.apply_coupon(subtotal)
        
        teir_discount = 0.0
        if isinstance(self.customer, Member):
            teir_discount = self.customer.get_member_discount(subtotal)

        discount = min(teir_discount + coupon_discount, subtotal)

        final_price = subtotal - discount - deposit
        if final_price < 0: final_price = 0.0
        
        return {
            "Member": {
                "Customer ID": self.customer.id,
                "Name": self.customer.name
            },
            "Order Id": self.id,
            "Food": [item.get_details() for item in self.order_item],
            "Booking": self.booking.get_details() if self.booking else "None",
            "Delivery": self.delivery.get_details() if self.delivery else "None",
            "Total Price Before Discount": subtotal,
            "Coupon Code": coupon.code if coupon else "None",
            "Discounted": discount,
            "Final Price": final_price
        }

    def calculate_totals(self, coupon_code: Optional[str] = None):
        info = self.pre_calculate_totals(coupon_code)
        self.__subtotal = info.get("Total Price Before Discount")
        self.__discount = info.get("Discounted")
        self.__final_price = info.get("Final Price")
        if coupon_code and isinstance(self.customer, Member):
            self.__coupon_used = self.customer.get_coupon_by_code(coupon_code)
        return info
    
    def execute_payment(self, method: PaymentMethod, payment_details: Dict[str, Any] = {}, coupon_code: Optional[str] = None) -> 'Receipt':
        from main_system.log.receipt import Receipt 
        from actor.customer import Member
        coupon = None
        if coupon_code:
            if isinstance(self.customer, Member):
                coupon = self.customer.get_coupon_by_code(coupon_code)
            else:
                raise HTTPException(409, "Only members can use coupons")
            
        info = self.calculate_totals(coupon_code)
        total_payable = info["Final Price"]

        if total_payable > 0:
            success, note = method.pay(total_payable, **payment_details)
        else:
            success = True
            note = "Payment Done"

        if success:
            self.status = OrderStatus.PAID

            if self.booking:
                self.booking.mark_checked_in()
                self.booking.room.mark_room_in_use()
            
            if self.delivery:
                self.delivery.mark_as_paid()

            if coupon: coupon.mark_as_used()

            receipt = Receipt(self, method)
            if isinstance(self.customer, Member):
                self.customer.add_receipt(receipt)
            return receipt
        else:
            raise HTTPException(400, note)

    @property
    def subtotal(self): return self.__subtotal
    @property
    def discount(self): return self.__discount
    @property
    def booking(self): return self.__booking
    @property
    def delivery(self): return self.__delivery
    @property
    def order_type(self): 
        if self.booking: return OrderType.EVENT
        elif self.delivery: return OrderType.DELIVERY
        return OrderType.GENERAL
    @property
    def id(self): return self.__id
    @property
    def total_payable_amount(self): return self.__final_price
    @property
    def coupon_used(self): return self.__coupon_used
    @property
    def order_item(self): return self.__order_list
    @property
    def customer(self): return self.__customer
    @property
    def status(self): return self.__status
    @status.setter
    def status(self, val: OrderStatus): self.__status = val