from main_system.menu.menu_item import MenuItem, Ingredient
from main_system.order.order_extention.booking import Booking
from main_system.order.order_extention.delivery import Delivery
from actor.customer import Customer, Coupon, Member, CouponStatus
from main_system.external_platform.payment_method import PaymentMethod
from main_system.enum import OrderStatus, OrderType, OrderItemStatus
from fastapi import HTTPException
from pydantic import BaseModel
from datetime import datetime
from shared.utils.simulate import SimulationClock
import copy
from typing import TYPE_CHECKING, Optional, List, Dict, Any
import uuid

if TYPE_CHECKING:
    from main_system.log.receipt import Receipt
    from main_system.restaurant import restaurant
    

class OrderItem:
    class OrderItemDTO(BaseModel):
        order_id: str
        menu: str
        quantity: int

    @staticmethod
    def is_valid_quantity(quantity: int):
        return quantity > 0
    
    def __init__(self, id: int, menu: MenuItem, quantity: int):
        if not OrderItem.is_valid_quantity(quantity):
            raise ValueError("INVALID: Order Item Quantity")
        self.__id = id
        self.__menu_item = menu
        self.__quantity = quantity
        self.__status = OrderItemStatus.PENDING

    @property
    def id(self): return self.__id
    @property
    def menu_item(self): return self.__menu_item
    @property
    def quantity(self): return self.__quantity
    @property
    def price(self): return self.__menu_item.price * self.__quantity
    @property
    def status(self): return self.__status
    @status.setter
    def status(self, status: OrderItemStatus): self.__status = status
    
    def order_item_reserve(self):
        try:
            for ingredient in self.__menu_item.all_ingredient:
                success = restaurant.stock_reserve(ingredient.item.name, ingredient.quantity * self.__quantity)
                if not success:
                    self.order_item_reverse(ingredient)
                    self.update_status(OrderItemStatus.OUT_OF_STOCK)
                    return
            else:
                self.update_status(OrderItemStatus.RESERVED)
        except ValueError as e:
            raise ValueError(str(e))
    def order_item_reverse(self, ingredient: Ingredient):
        for reserved_ingredient in self.__menu_item.all_ingredient:
            if reserved_ingredient.item.name == ingredient.item.name:
                return
            restaurant.stock_reverse(reserved_ingredient.item.name, reserved_ingredient.quantity * self.__quantity)

    def order_item_to_dict(self):
        return {
            "id": self.__id,
            "menu": self.__menu_item.to_dict_order(restaurant),
            "quantity": self.__quantity,
            "status": self.__status
        }
    
    def get_details(self) -> Dict[str, Any]:
        return {
            "name": self.menu_item.name,
            "quantity": self.quantity,
            "price": self.menu_item.price
        }
        
    def process_cooking(self):
        if self.__status != OrderItemStatus.RESERVED:
             return False
        
        self.status(OrderItemStatus.COOKING)
        ingredients = self.__menu_item.all_ingredient()
        
        for ingredient in ingredients:
            restaurant.consume_reserved_ingredient(ingredient.item.name, ingredient.quantity * self.__quantity)
            
        self.status(OrderItemStatus.READY)
        return True

    def cancel_reservation(self):
        if self.__status == OrderItemStatus.RESERVED:
            ingredients = self.__menu_item.all_ingredient()
            for ingredient in ingredients:
                restaurant.reverse_reserve_ingredient(ingredient.item.name, ingredient.quantity * self.__quantity)
            self.status(OrderItemStatus.CANCEL)
    
class Order:
    def __init__(self, type: OrderType, customer: Customer):
        self.__id = f"TXN-{uuid.uuid4().hex[:12].upper()}"
        self.__type = type
        self.__customer: Customer = customer
        self.__order_item_list: List[OrderItem] = []
        self.__order_item_id_count = 0
        self.__status = OrderStatus.PENDING
        self.__status_start = SimulationClock.get_time()
        self.__coupon_used: Optional[Coupon] = None
        self.__booking: Optional[Booking] = None
        self.__delivery: Optional[Delivery] = None
        self.__subtotal = 0.0
        self.__discount = 0.0
        self.__final_price = 0.0
    class OrderDTO(BaseModel):
        order_id: str
        order_type: str
        order_status: str
        customer: str
        food_list: list
        total_price: float

    def add_order_item(self, menu: MenuItem, quantity: int):
        try:
            new_menu = copy.deepcopy(menu)
            current_order_item = OrderItem(self.__order_item_id_count, new_menu, quantity)
            self.__order_item_id_count += 1
        except ValueError as e:
            raise ValueError(str(e))
        self.__order_item_list.append(current_order_item)
        current_order_item.status = OrderItemStatus.ADDED
        self.update_price()

    def add_booking(self, booking: Booking):
        if self.booking: raise HTTPException(409, "Booking Already Exists")
        self.__booking = booking

    def add_delivery(self, delivery: Delivery):
        if self.delivery: raise HTTPException(409, "Delivery Already Exists")
        self.__delivery = delivery

    def update_price(self):
        count_price = 0
        for order_item in self.__order_item_list:
            if order_item.status != OrderItemStatus.OUT_OF_STOCK and order_item.status != OrderItemStatus.CANCEL:
                count_price += order_item.price
        self.__subtotal = count_price

    def check_customer(self, customer: Customer):
        if self.__customer != customer:
            raise ValueError("Wrong Customer")
    
    def search_order_item_from_id(self, order_item_id: int):
        for order_item in self.__order_item_list:
            if order_item.id == order_item_id:
                return order_item
        raise ValueError("Order Item NOT FOUND")

    def order_reserve(self):
        for order_item in self.__order_item_list:
            if order_item.status == OrderItemStatus.ADDED:
                order_item.order_item_reserve()
        self.update_status(OrderStatus.RESERVED)
        return self
    
    def order_confirm(self):
        if self.__status == OrderStatus.PENDING:
            raise ValueError("Ordering Food First.")
        if self.__status == OrderStatus.CANCELED:
            raise ValueError("Order already been cancelled")
        if self.__status != OrderStatus.RESERVED:
            raise ValueError("Confirmed Already")
        for order_item_index in range(len(self.__order_item_list) - 1, -1, -1):
            order_item = self.__order_item_list[order_item_index]
            if order_item.status == OrderItemStatus.OUT_OF_STOCK or order_item.status == OrderItemStatus.CANCEL:
                del self.__order_item_list[order_item_index]
        self.status(OrderStatus.CONFIRMED)
        return self
    
    def order_item_dict_list(self) -> list:
        dict_list = []
        for e in self.__order_item_list:
            dict_list.append(e.order_item_to_dict(restaurant))
        return dict_list
    
    def order_to_dict(self) -> dict:
        return {
            "order_id": self.__id,
            "order_type": self.__type,
            "order_status": self.__status,
            "customer": self.__customer.name,
            "order_item_list": self.order_item_dict_list(restaurant),
            "total_price": self.__sub_total_price
        }
        
    def cook_order(self):
        if self.__status not in [OrderStatus.RESERVED, OrderStatus.PAIDED]:
            return False
            
        self.status(OrderStatus.COOKING)
        all_done = True
        for item in self.__order_list:
            if item.status == OrderItemStatus.RESERVED:
                if not item.process_cooking(restaurant):
                    all_done = False
                
        if all_done:
            self.status(OrderStatus.READY)
            return True
        return False

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
            self.status = OrderStatus.PAIDED

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
    def status(self, val: OrderStatus): 
        self.__status = val
        self.__status_start = datetime.now()