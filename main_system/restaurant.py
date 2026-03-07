from __future__ import annotations
from main_system.authentication import AuthManager
from main_system.ingredient import Item, Ingredient
from main_system.external_platform.delivery_provider import DeliveryProvider, Delivery
from main_system.external_platform.payment_method import PaymentMethod
from shared.utils.simulate import SimulationClock
from main_system.coupon import Coupon, FixedAmountCoupon, PercentCoupon
from main_system.enum import RoomStatus, RoomType, BookingStatus
from main_system.booking import Room, TimeSlot, Booking
from typing import TYPE_CHECKING, Optional, List, Tuple, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from main_system.enum import Enum, MemberTier, MenuItemStatus, ItemStatus, IngredientType, CouponStatus, OrderStatus, OrderType, OrderItemStatus
from fastmcp import FastMCP
from pydantic import BaseModel
import uuid
import random
import copy

class User(ABC):
    @staticmethod
    def is_valid_phone_number(phone_number: str):
        return len(phone_number) == 10 and phone_number.isdigit()
    
    def __init__(self, id: str, name: str, phone_number: str, username: str, password: str):
        if not User.is_valid_phone_number(phone_number):
            raise ValueError("INVALID: Phone number")
        self.__id = id
        self.__name = name
        self.__phone_number = phone_number
        self.__username = username
        self.__password = password
    
    @property
    def id(self): return self.__id
    @property
    def name(self): return self.__name
    @property
    def phone_number(self): return self.__phone_number
    
    def check_username(self, username: str) -> bool:
        return self.__username == username
    def check_identity(self, username: str, password: str) -> bool:
        return self.__username == username and self.__password == password
    
    # def __eq__(self, other):
    #     return (type(other) is type(self)) and self.__name == other.name and self.__id == other.id and self.__phone_number == other.phone_number
class Staff(User):
    def __init__(self, id: str, name: str, phone_number: str, username: str="", password: str="", is_admin: Optional[bool] = False):
        super().__init__(id, name, phone_number, username, password)
        self.__is_admin = is_admin

    def check_room_availability(self, room, start_time: datetime, hours: int) -> bool:
        return restaurant.is_slot_available(room, start_time, hours)
    
    @property
    def is_admin(self) -> bool: return self.__is_admin

class Customer(User):
    pass
class Guest(Customer):
    Guest_count = 0
    def __init__(self, name = None):
        if name == None:
            self.__name = f"GUEST-{Guest.Guest_count:0{3}d}"
            Guest.Guest_count += 1
        else: 
            self.__name = name

    @property
    def id(self): return f"GUEST"
    @property
    def name(self): return self.__name

    def __eq__(self, other):
        return (type(other) is type(self)) and self.__name == other.name

class Member(Customer):
    def __init__(self, id: str, name: str, tier: MemberTier, username: str, password: str, phone: str = ""):
        super().__init__(id, name, phone, username, password)
        self.__coupon_list: List[Coupon] = [] 
        self.__receipt_list: List[Receipt] = []
        self.__tier: MemberTier = tier
        self.__points: int = 0

    def add_receipt(self, receipt: Receipt): self.__receipt_list.append(receipt)
    def add_coupon(self, coupon: Coupon): self.__coupon_list.append(coupon)
    
    def get_coupon_by_code(self, code: str):
        for coupon in self.__coupon_list:
            if coupon.code == code: return coupon
        raise HTTPException(404, "Coupon Not Found")

    def get_member_discount(self, base_price: float):
        match self.tier:
            case MemberTier.GENERAL: return 0.0
            case MemberTier.BRONZE: return base_price * 0.05
            case MemberTier.SILVER: return base_price * 0.10
            case MemberTier.GOLD: return base_price * 0.15
        return 0.0

    @property
    def tier(self) -> MemberTier: return self.__tier


    


class MenuItem(ABC):
    @staticmethod
    def is_valid_price(price: float):
        return price > 0
    
    @staticmethod
    def is_valid_cooking_time(time: timedelta):
        return time > timedelta(seconds=0)
    
    def __init__(self, name: str, price: float, cooking_time: timedelta):
        if not MenuItem.is_valid_price(price):
            raise ValueError("INVALID: Price")
        if not MenuItem.is_valid_cooking_time(cooking_time):
            raise ValueError("INVALID: Cooking time")
        self.__name = name
        self.__price = price
        self.__cooking_time = cooking_time

    @property
    def name(self):
        return self.__name
    
    @property
    def price(self):
        return self.__price
    
    @property
    def cooking_time(self):
        return self.__cooking_time
    
    @abstractmethod
    def all_ingredient(self):
        pass
    @abstractmethod
    def calculate_price(self, original_menu: 'MenuItem'):
        pass

    def update_price(self, original_menu: 'MenuItem'):
        self.__price = self.calculate_price(original_menu)

    def to_dict_order(self):
        original_menu = restaurant.search_menu_item_from_name(self.name)
        custom = []
        for ingredient in self.all_ingredient:
            if ingredient.type == IngredientType.CUSTOMIZABLE:
                custom.append(ingredient.ingredient_to_dict)
        self.update_price(original_menu)
        custom = []
        for ingredient in self.all_ingredient:
            if ingredient.type == IngredientType.CUSTOMIZABLE:
                custom.append(ingredient.ingredient_to_dict)
        return {
            "name": self.__name,
            "customizable": custom if custom else None,
            "price": self.__price
        }

    def to_dict_menu(self):
        current_status = MenuItemStatus.AVAILABLE
        custom = []
        for ingredient in self.all_ingredient:
            if restaurant.check_stock(ingredient.item.name, ItemStatus.AVAILABLE) < ingredient.quantity:
                current_status = MenuItemStatus.UNAVAILABLE
                break
            if ingredient.type == IngredientType.CUSTOMIZABLE:
                custom.append(ingredient.ingredient_to_dict)
        return {
            "name": self.__name,
            "customizable": custom if custom else None,
            "price": self.__price,
            "status": current_status
        }
        
class SingleMenuItem(MenuItem):
    def __init__(self, name: str, price: float, cooking_time: timedelta, recipe: list):
        try:
            super().__init__(name, price, cooking_time)
        except ValueError as e:
            raise ValueError(str(e))
        for ingredient in recipe:
            if not Ingredient.is_valid_quantity(ingredient.quantity):
                raise ValueError("INVALID: Ingredient QUANTITY in Recipe")
        self.__recipe = recipe
        
    def find_ingredient_in_recipe(self, item: Item):
        for find_ingredient in self.__recipe:
            if find_ingredient.item == item:
                return find_ingredient
        raise ValueError("INVALID: Item")
    
    def find_ingredient_in_recipe_from_name(self, item_name: str):
        for find_ingredient in self.__recipe:
            if find_ingredient.item.name == item_name:
                return find_ingredient
        raise ValueError("INVALID: Item")
    
    def calculate_price(self, original_menu: MenuItem):
        add_price = 0
        for ingredient in self.all_ingredient:
            if ingredient.type == IngredientType.CUSTOMIZABLE:
                original_ingredient_quantity = original_menu.find_ingredient_in_recipe(ingredient.item).quantity
                ingredient_add = ingredient.quantity - original_ingredient_quantity
                if ingredient_add > 0:
                    add_price += ingredient_add * ingredient.item.price
        return add_price + original_menu.price

    @property
    def all_ingredient(self):
        return self.__recipe
    
    def custom_ingredient(self, item_name: str, quantity: int):
        try:
            ingredient = self.find_ingredient_in_recipe_from_name(item_name)
            ingredient.custom(quantity)
        except ValueError as e:
            raise ValueError(str(e))
        except TypeError as e:
            raise TypeError(str(e))
        
class Food:
    def __init__(self, item: SingleMenuItem, quantity: int):
        self.__item = item
        self.__quantity = quantity

    @property
    def item(self):
        return self.__item
    @property
    def quantity(self):
        return self.__quantity
    
    @property
    def get_ingredient_per_unit(self):
        return self.__item.all_ingredient

class SetMenuItem(MenuItem):
    def __init__(self, name, price, items: list):
        total_cooking_time = timedelta(seconds=0)
        for food in items:
            total_cooking_time += food.item.cooking_time
        super().__init__(name, price, total_cooking_time)
        self.__items = items

    def find_ingredient_in_recipe(self, item: Item):
        for find_ingredient in self.all_ingredient:
            if find_ingredient.item == item:
                return find_ingredient
        raise ValueError("INVALID: Item")

    # merge duplicate ingredient
    @property
    def all_ingredient(self):
        ingredients = []
        for food in self.__items:
            add_ingredients = copy.deepcopy(food.get_ingredient_per_unit)
            for unit in add_ingredients:
                for merge in ingredients:
                    if merge.item == unit.item:
                        merge.modify(merge.quantity + (unit.quantity * food.quantity))
                else:
                    unit.modify(unit.quantity * food.quantity)
                    ingredients.append(unit)
        return ingredients
    
    def calculate_price(self, original_menu: MenuItem):
        return original_menu.price

class OrderItem:
    class OrderItemDTO(BaseModel):
        order_id: str
        menu: str
        quantity: int
    
    class OrderItemCustomDTO(BaseModel):
        order_id: str
        order_item_id: int
        item_name: str
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
    
    def custom_menu(self, item_name: str, quantity: int):
        if not isinstance(self.__menu_item, SingleMenuItem):
            raise TypeError("Can not custom. This is not Single Menu Item.")
        try:
            self.__menu_item.custom_ingredient(item_name= item_name, quantity= quantity)
        except ValueError as e:
            raise ValueError(str(e))
        except TypeError as e:
            raise TypeError(str(e))

    def order_item_reserve(self):
        try:
            for ingredient in self.__menu_item.all_ingredient:
                success = restaurant.stock_reserve(ingredient.item.name, ingredient.quantity * self.__quantity)
                if not success:
                    self.order_item_reverse(ingredient)
                    self.status = OrderItemStatus.OUT_OF_STOCK
                    return
            else:
                self.status= OrderItemStatus.RESERVED
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
            "menu": self.__menu_item.to_dict_order(),
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
        
        self.status = OrderItemStatus.COOKING
        ingredients = self.__menu_item.all_ingredient
        
        for ingredient in ingredients:
            restaurant.consume_reserved_ingredient(ingredient.item.name, ingredient.quantity * self.__quantity)
            
        self.status = OrderItemStatus.READY
        return True

    def cancel_reservation(self):
        if self.__status == OrderItemStatus.RESERVED:
            ingredients = self.__menu_item.all_ingredient
            for ingredient in ingredients:
                restaurant.stock_reverse(ingredient.item.name, ingredient.quantity * self.__quantity)
            self.status = OrderItemStatus.CANCELED

class Order:
    OrderId_count = 0

    def __init__(self, type: OrderType, customer: Customer):
        self.__id = f"ORD-{Order.OrderId_count:0{3}d}"
        Order.OrderId_count += 1
        self.__type = type
        self.__customer: Customer = customer
        self.__order_item_list: List[OrderItem] = []
        self.__order_item_id_count = 0
        self.__status = OrderStatus.PENDING
        self.__status_start = SimulationClock.get_time()
        self.__coupon_used: Optional[Coupon] = None
        self.__booking: Optional['Booking'] = None
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
    
    def search_order_item_from_id(self, order_item_id: int):
        for order_item in self.__order_item_list:
            if order_item.id == order_item_id:
                return order_item
        raise ValueError("Order Item NOT FOUND")

    def custom(self,order_item_id: int, item_name: str, quantity: int):
        try:
            order_item = self.search_order_item_from_id(order_item_id)
            order_item.custom_menu(item_name, quantity)
        except ValueError as e:
            raise ValueError(str(e))
        except TypeError as e:
            raise TypeError(str(e))

    def add_booking(self, booking: 'Booking'):
        if self.booking: raise HTTPException(409, "Booking Already Exists")
        self.__booking = booking

    def add_delivery(self, delivery: Delivery):
        if self.delivery: raise HTTPException(409, "Delivery Already Exists")
        self.__delivery = delivery

    def update_price(self):
        count_price = 0
        for order_item in self.__order_item_list:
            if order_item.status != OrderItemStatus.OUT_OF_STOCK and order_item.status != OrderItemStatus.CANCELED:
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
        self.status = OrderStatus.RESERVED
        return self
    
    def order_confirm(self):
        if self.__status == OrderStatus.PENDING:
            raise ValueError("Ordering Food First.")
        if self.__status == OrderStatus.CANCELED:
            raise ValueError("Order already been canceled")
        if self.__status != OrderStatus.RESERVED:
            raise ValueError("Confirmed Already")
        for order_item_index in range(len(self.__order_item_list) - 1, -1, -1):
            order_item = self.__order_item_list[order_item_index]
            if order_item.status == OrderItemStatus.OUT_OF_STOCK or order_item.status == OrderItemStatus.CANCELED:
                del self.__order_item_list[order_item_index]
        self.status = OrderStatus.CONFIRMED
        return self
    
    def order_item_dict_list(self) -> list:
        dict_list = []
        for e in self.__order_item_list:
            dict_list.append(e.order_item_to_dict())
        return dict_list
    
    def order_to_dict(self) -> dict:
        return {
            "order_id": self.__id,
            "order_type": self.__type,
            "order_status": self.__status,
            "customer": self.__customer.name,
            "order_item_list": self.order_item_dict_list(),
            "total_price": self.__subtotal
        }
        
    def cook_order(self):
        if self.__status not in [OrderStatus.RESERVED, OrderStatus.PAIDED]:
            return False
            
        self.status = OrderStatus.COOKING
        all_done = True
        for item in self.__order_item_list:
            if item.status == OrderItemStatus.RESERVED:
                if not item.process_cooking():
                    all_done = False
                
        if all_done:
            self.status = OrderStatus.READY
            return True
        return False

    def pre_calculate_totals(self, coupon_code: Optional[str] = None):
        coupon = None
        if coupon_code:
            if isinstance(self.__customer, Member):
                coupon = self.__customer.get_coupon_by_code(coupon_code)
            else:
                raise HTTPException(409, "Only members can use coupons")
        
        subtotal = sum(item.price for item in self.__order_item_list)
        deposit = 0.0

        if self.__booking:
            subtotal += self.__booking.full_price
            deposit = self.__booking.deposit

        if self.__delivery:
            subtotal += self.__delivery.fee

        coupon_discount = 0.0
        if coupon:
             if coupon.status != CouponStatus.AVAILABLE:
                raise HTTPException(409, "Coupon Not Available")
             coupon_discount = coupon.apply_coupon(subtotal)
        
        teir_discount = 0.0
        if isinstance(self.__customer, Member):
            teir_discount = self.__customer.get_member_discount(subtotal)

        discount = min(teir_discount + coupon_discount, subtotal)

        final_price = subtotal - discount - deposit
        if final_price < 0: final_price = 0.0
        
        return {
            "Member": {
                "Customer ID": self.__customer.id,
                "Name": self.__customer.name,
                "Tier": self.__customer.tier if isinstance(self.__customer, Member) else "None"
            },
            "Order Id": self.__id,
            "Food": [item.get_details() for item in self.__order_item_list],
            "Booking": self.__booking.get_details() if self.__booking else "None",
            "Delivery": self.__delivery.get_details() if self.__delivery else "None",
            "Total Price Before Discount": subtotal,
            "Coupon Code": coupon.code if coupon else "None",
            "Coupon Discount": coupon_discount,
            "Tier Discount": teir_discount,
            "Total Discounted": discount,
            "Final Price": final_price
        }

    def calculate_totals(self, coupon_code: Optional[str] = None):
        info = self.pre_calculate_totals(coupon_code)
        self.__subtotal = info.get("Total Price Before Discount")
        self.__discount = info.get("Total Discounted")
        self.__final_price = info.get("Final Price")
        if coupon_code and isinstance(self.__customer, Member):
            self.__coupon_used = self.__customer.get_coupon_by_code(coupon_code)
        return info
    
    def execute_payment(self, method: PaymentMethod, payment_details: Dict[str, Any] = {}, coupon_code: Optional[str] = None) -> 'Receipt':
        coupon = None
        if coupon_code:
            if isinstance(self.__customer, Member):
                coupon = self.__customer.get_coupon_by_code(coupon_code)
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

            if self.__booking:
                self.__booking.mark_checked_in()
                self.__booking.room.mark_room_in_use()
            
            if self.__delivery:
                self.__delivery.mark_as_paid()

            if coupon: coupon.mark_as_used()

            receipt = Receipt(self, method)
            if isinstance(self.__customer, Member):
                self.__customer.add_receipt(receipt)
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
    def order_item(self): return self.__order_item_list
    @property
    def customer(self): return self.__customer
    @property
    def status(self): return self.__status
    @status.setter
    def status(self, val: OrderStatus): 
        self.__status = val
        self.__status_start = datetime.now()

class Receipt:
    def __init__(self, order: 'Order', method: 'PaymentMethod'):
      self.__id = f"TXN-{uuid.uuid4().hex[:12].upper()}"
      self.__order = order                 
      self.__method = method
      self.__timestamp = SimulationClock.get_time()

    @property
    def id(self): return self.__id
    @property
    def order(self): return self.__order
    @property
    def method(self): return self.__method
    @property
    def timestamp(self): return self.__timestamp

    def generate(self):
        order = self.order
        coupon_code = order.coupon_used.code if order.coupon_used else "None"
        deposit_deducted = order.booking.deposit if order.booking else 0.0
        
        return {
            "receipt_no": self.id,
            "date": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "merchant": "Knight Chicken Fast Food Co.",
            
            "customer_info": {
                "name": order.customer.name,
                "tier": order.customer.tier if isinstance(order.customer, Member) else "None"
            },
            
            "order_summary": {
                "order_id": order.id,
                "order_type": order.order_type
            },
            
            "itemized_bill": {
                "foods": [item.get_details() for item in order.order_item],
                "booking_details": order.booking.get_details() if order.booking else "None",
                "delivery_details": order.delivery.get_details() if order.delivery else "None"
            },
            
            "financial_summary": {
                "subtotal": order.subtotal,
                "coupon_applied": coupon_code,
                "discount_amount": order.discount,
                "deposit_deducted": deposit_deducted,
                "net_amount_due": order.total_payable_amount
            },
            
            "payment_record": {
                "method": self.method.name,
                "status": "SUCCESS"
            }
        }
class Restaurant:
    def __init__(self):
        self.__menu: List[MenuItem] = []
        self.__stock: List[Item] = []
        self.__receipt_list: List[Receipt] = []
        self.__coupon_list: List[Coupon] = []
        self.__member_list: List[Member] = []
        self.__staff_list: List[Staff] = []
        self.__booking_list: List[Booking] = []  
        self.__order_list: List[Order] = []      
        self.__payment_method: List[PaymentMethod] = []
        self.__room_list: List[Room] = []
        self.__delivery_providers: List[DeliveryProvider] = []
        self.__auth_manager = AuthManager()
        self.__member_counter = 0
        self.__staff_counter = 0
        self.__booking_counter = 0

    def add_delivery_provider(self, provider: 'DeliveryProvider'): self.__delivery_providers.append(provider)
    def get_delivery_provider(self, provider_name: str) -> 'DeliveryProvider':
        for p in self.__delivery_providers:
            if p.platform_name.lower() == provider_name.lower(): return p
        raise HTTPException(404, "Delivery Provider Not Found")
    
    def add_room(self, room: Room): self.__room_list.append(room)
    def get_room(self, room_id: str) -> Room:
        for r in self.__room_list:
            if r.id == room_id: return r
        raise HTTPException(404, "Room Not Found")
    
    def add_booking(self, booking: Booking): self.__booking_list.append(booking)
    def get_booking(self, booking_id: str) -> Booking:
        for b in self.__booking_list:
            if b.id == booking_id: return b
        raise HTTPException(404, "Booking Not Found")

    def add_order(self, order: Order): self.__order_list.append(order)
    def get_order(self, order_id: str) -> Order:
        for o in self.__order_list:
            if o.id == order_id: return o
        raise HTTPException(404, "Order Not Found")

    def add_payment_method(self, method: PaymentMethod): self.__payment_method.append(method)
    def get_payment_method(self, method_name: str) -> PaymentMethod:
        for s in self.__payment_method:
            if s.name.lower() == method_name.lower(): return s
        raise HTTPException(400, "Invalid Payment Method")

    def add_receipts(self, receipt: Receipt): 
        self.__receipt_list.append(receipt)
         # print(f"[SYSTEM LOG] {receipt.timestamp} | {receipt.id} | {receipt.status} | {receipt.amount} THB")
    def get_receipts_by_order_id(self, order_id: str) -> Receipt:
        for r in self.__receipt_list:
            if r.order.id == order_id: return r
        raise HTTPException(404, "Receipt Not Found")

    def add_member(self, member: Member): self.__member_list.append(member)
    def get_member_by_id(self, id: str) -> Member:
        for m in self.__member_list:
            if m.id == id: return m
        raise HTTPException(404, "Member Not Found")
    
    def add_coupon(self, coupon: 'Coupon'): self.__coupon_list.append(coupon)
    def get_coupon(self, code: str) -> 'Coupon': 
        for c in self.__coupon_list: 
            if c.code == code: return c
        raise HTTPException(404, "Coupon Not Found")

    def add_staff(self, staff: 'Staff'): self.__staff_list.append(staff)    
    def get_staff(self, id: str) -> 'Staff':
        for s in self.__staff_list:
            if s.id == id: return s
        raise HTTPException(404, "Staff Not Found")

    def get_user_by_id(self, id: str) -> User:
        for m in self.__member_list:
            if m.id == id: return m
        for s in self.__staff_list:
            if s.id == id: return s
        raise HTTPException(404, "User Not Found")

    def verify_token_and_role(self, token: str, allowed_roles: List[str]) -> User:
        session = self.__auth_manager.get_session(token)
        if not session:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        user = self.get_user_by_id(session.user_id)
        if isinstance(user, Staff):
            if user.is_admin:
                user_role = "Admin"
            else:
                user_role = "Staff"
        else:
            user_role = "Member"
        if user_role not in allowed_roles:
            raise HTTPException(status_code=403, detail=f"Access Forbidden: Requires one of {allowed_roles}")

        return user    
    
    def add_menu(self, menu: MenuItem): self.__menu.append(menu)
    
    @property
    def count_order(self): return len(self.__order_list)

    @property
    def check_queue(self):
        count_queue = 0
        for order in self.__order_list:
            if order.status == OrderStatus.PAIDED or order.status == OrderStatus.COOKING:
                count_queue += 1
        return count_queue
    
    def add_stock(self, item: Item, quantity: int):
        for e in range(quantity):
            self.__stock.append(copy.deepcopy(item))

    def get_queue(self, queue_order: int):
        count_queue = 0
        for order in self.__order_list:
            if order.status == OrderStatus.PAIDED or order.status == OrderStatus.COOKING:
                count_queue += 1
            if count_queue == queue_order:
                return order
        return False
    
    def check_stock(self, item_name: str, status: ItemStatus):
        count_stock = 0
        for find in self.__stock:
            if find.name == item_name and find.status == status:
                count_stock += 1
        return count_stock
    
    def get_menu(self):
        menu = []
        for each_menu in self.__menu:
            menu.append(each_menu.to_dict_menu())
        return {"menu": menu}
    
    def search_menu_item_from_name(self, menu_item_name: str):
        for menu_item in self.__menu:
            if menu_item.name == menu_item_name:
                return menu_item
        raise ValueError("Menu NOT FOUND")
    
    def search_order_from_id(self, order_id: str) -> Order:
        for find in self.__order_list:
            if find.id == order_id:
                return find
        raise ValueError("Order NOT FOUND")
    #reserved while ordering
    def reserve(self, order: Order):
        return order.order_reserve()
    
    def stock_reserve(self, item_name: str, quantity: int):
        if quantity < 0:
            raise ValueError("INVALID: Quantity")
        count = 0
        for item in self.__stock:
            if item.name == item_name and item.status == ItemStatus.AVAILABLE:
                item.status = ItemStatus.RESERVED
                count += 1
            if count == quantity:
                return True
        self.stock_reverse(item_name, count)
        return False
        
    def stock_reverse(self, item_name: str, quantity: int):
        if quantity < 0:
            raise ValueError("INVALID: Quantity")
        if self.check_stock(item_name, ItemStatus.RESERVED) < quantity:
            raise ValueError("reverse thing you should not")
        count = 0
        for item_index in range(len(self.__stock) - 1, -1, -1):
            if count == quantity:
                return True
            item = self.__stock[item_index]
            if item.name == item_name and item.status == ItemStatus.RESERVED:
                item.status = ItemStatus.AVAILABLE
                count += 1
    
    def find_ingredient_in_stock(self, item_name: str):
        return sum(1 for item in self.__stock if item.name == item_name and item.status == ItemStatus.AVAILABLE)

    def find_item_in_reserved(self, item_name: str):
        return sum(1 for item in self.__stock if item.name == item_name and item.status == ItemStatus.RESERVED)
    
    def consume_reserved_ingredient(self, item_name: str, quantity: int):
        if self.find_item_in_reserved(item_name) < quantity:
            return False

        count = 0
        for i in range(len(self.__stock) - 1, -1, -1):
            item = self.__stock[i]
            if item.name == item_name and item.status == ItemStatus.RESERVED:
                self.__stock.pop(i)
                count += 1
                if count == quantity:
                    break
        return True

    def stock_reverse(self, item_name: str, quantity: int):
        if quantity < 0:
            raise ValueError("INVALID: Quantity")
        if self.check_stock(item_name, ItemStatus.RESERVED) < quantity:
            raise ValueError("Reverse")
        count = 0
        for item_index in range(len(self.__stock) - 1, -1, -1):
            if count == quantity:
                return True
            item = self.__stock[item_index ]
            if item.name == item_name and item.status == ItemStatus.RESERVED:
                item.status == ItemStatus.AVAILABLE 
                count += 1
        return count == quantity
                    

    def confirm(self, order:Order):
        try:
            confirmed_order = order.order_confirm()
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return confirmed_order
    
    def check_and_issue_reward(self, order: 'Order'):
        if not isinstance(order.customer, Member):
            return None

        member = order.customer
        spending = order.subtotal
        if not spending: return None
    
        reward_coupon = None

        if spending >= 3000:
            code = f"RW20-{uuid.uuid4().hex[:6].upper()}"
            reward_coupon = PercentCoupon(f"CPN-{code}", code, 1000.0, 20.0)
        elif spending >= 1000:
            code = f"RWF100-{uuid.uuid4().hex[:6].upper()}"
            reward_coupon = FixedAmountCoupon(f"CPN-{code}", code, 500.0, 100.0)

        if reward_coupon:
            member.add_coupon(reward_coupon)
            return reward_coupon.code
            
        return None
    
    def check_and_issue_member_teir(self, order: 'Order'):
        if not isinstance(order.customer, Member):
            return None

    def get_payment_method(self, method_name: str) -> 'PaymentMethod':
        for s in self.__payment_method:
            if s.name.lower() == method_name.lower(): return s
        raise HTTPException(status_code=400, detail="Unknown Method")
    
    def booking_room(self,token: str, member_id: str, room_id: str, hours: int, pay_method: str, start_time: datetime, payment_details: Dict[str, Any] = {}):
        staff = self.verify_token_and_role(token, allowed_roles=["Staff", "Admin"])
        if not staff:
            raise HTTPException(status_code=401, detail="Unauthorized token")

        member = self.get_member_by_id(member_id)
        if not member or not isinstance(member, Member):
            raise HTTPException(status_code=404, detail="Member not found")
        
        room = self.get_room(room_id)
        if not room or not isinstance(room, Room):
            raise HTTPException(status_code=404, detail="Room not found")

        if not self.is_slot_avaliable(room, start_time, hours):
            raise HTTPException(status_code=400, detail="Time slot already occupied")
        
        booking_id = f"BK-{self.__booking_counter:03d}"
        self.__booking_counter += 1
        time_slot = TimeSlot(start_time, hours)
        booking = Booking(booking_id, member, room, time_slot)
        
        pay_med = self.get_payment_method(pay_method)
        message = booking.pay_deposit(pay_med, payment_details)
        
        self.add_booking(booking)
        return message

    def is_slot_avaliable(self, room, start, hours):
        end = start + timedelta(hours=hours)
        for b in self.__booking_list:
            if b.room.id == room.id: 
                if b.status not in [BookingStatus.CANCELLED, BookingStatus.COMPLETED]:
                    if start < b.time_slot.end_time and end > b.time_slot.start_time:
                        return False
        return True

    def auto_check_no_show(self):
        now = SimulationClock.get_time()
        for b in self.__booking_list:
            deadline = b.time_slot.start_time + timedelta(minutes=30)
            if b.status == BookingStatus.DEPOSIT_PAID and now > deadline:
                b.mark_cancelled()
                b.room.mark_room_available()

    def check_in_booking(self, token: str, order_id: str, booking_id: str, coupon_code: str, pay_method: str, payment_details: Dict[str, Any] = {}):
        session = self.__auth_manager.get_session(token)
        if not session:
            raise HTTPException(status_code=401, detail="Unauthorized token")
        staff = self.get_staff(session.user_id)
        if not isinstance(staff, Staff):
            raise HTTPException(status_code=401, detail="Only Staff can handle check-in")

        booking = self.get_booking(booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
        if booking.status == BookingStatus.CANCELLED:
            raise HTTPException(status_code=400, detail="Booking is cancelled")
        if booking.status != BookingStatus.DEPOSIT_PAID:
            raise HTTPException(status_code=400, detail="Booking is not ready for check-in ")
        
        order = self.get_order(order_id)
        if not order or order.booking != booking:
            raise HTTPException(status_code=404, detail="Order not found or does not match booking")

        receipt_data = self.process_order_payment(order_id=order.id, coupon_code=coupon_code, method_name=pay_method, payment_details=payment_details)

        booking.mark_checked_in()
        booking.room.mark_room_in_use()
        return {"message": f"Booking {booking_id} checked in successfully",
                "room_id": booking.room.id,
                "member_name": booking.member.name,
                "check_in_time": SimulationClock.get_time().strftime("%Y-%m-%d %H:%M:%S"),
                "receipt_data": receipt_data,
                "full_amount_paid": order.total_payable_amount
                }

    def check_out_booking(self, token: str, booking_id: str):
        # แบบที่ยังไม่เช็คเกินเวลา
        session = self.__auth_manager.get_session(token)
        if not session:
            raise HTTPException(status_code=401, detail="Unauthorized token")
        staff = self.get_staff(session.user_id)
        if not isinstance(staff, Staff):
            raise HTTPException(status_code=401, detail="Only Staff can handle check-out")

        booking = self.get_booking(booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
        if booking.status != BookingStatus.CHECKED_IN:
            raise HTTPException(status_code=400, detail="Booking is not currently checked in")
        
        booking.mark_checked_out()
        return {"message": f"Booking {booking_id} checked out successfully",
                "room_id": booking.room.id,
                "member_name": booking.member.name,
                "check_out_time": SimulationClock.get_time().strftime("%Y-%m-%d %H:%M:%S")}

    def login(self, username, password):
        member = next((m for m in self.__member_list if m.check_identity(username, password)), None)
        staff = next((s for s in self.__staff_list if s.check_identity(username, password)), None)
        if member:
            return self.__auth_manager.create_session(member.id)
        
        if staff:
            return self.__auth_manager.create_session(staff.id)
        
        raise HTTPException(401, "Invalid username or password")

    def logout(self, token: str):
        session = self.__auth_manager.get_session(token)
        if session:
            session.invalidate()
            return True
        return False
    
    # --- Member Registration ---
    def register_member(self, username: str, password: str, name: str, phone: str = "0000000000") -> 'Member':
        # ตรวจสอบว่า Username ซ้ำไหม
        if any(m.check_username(username) for m in self.__member_list) or any(s.check_username(username) for s in self.__staff_list):
            raise HTTPException(400, "Username already exists")
        
        # ระบบสร้าง ID ให้อัตโนมัติ
        new_id = f"M-{self.__member_counter:03d}" # ผลลัพธ์จะเป็น M-001, M-002...
        
        # สร้าง Member (Tier เริ่มต้นเป็น Bronze อัตโนมัติใน __init__)
        new_member = Member(new_id, name, MemberTier.BRONZE, username, password, phone)
        
        self.__member_list.append(new_member)
        self.__member_counter += 1
        return new_member

    # --- Staff Registration ---
    def register_staff(self, username: str, password: str, name: str, phone: str = "0000000000") -> 'Staff':
        if any(s.check_username(username) for s in self.__staff_list) or any(m.check_username(username) for m in self.__member_list):
            raise HTTPException(400, "Username already exists")

        new_id = f"S-{self.__staff_counter:03d}"
        
        new_staff = Staff(new_id, name, phone, username, password)
        
        self.__staff_list.append(new_staff)
        self.__staff_counter += 1
        return new_staff
    
    def get_all_members(self) -> List['Member']: return self.__member_list
    def get_all_staff(self) -> List['Staff']: return self.__staff_list
    def get_all_rooms(self) -> List['Room']: return self.__room_list
    def get_all_receipts(self) -> List['Receipt']: return self.__receipt_list
    def get_all_orders(self) -> List['Order']: return self.__order_list
    def get_all_bookings(self) -> List['Booking']: return self.__booking_list
    def get_all_coupons(self) -> List['Coupon']: return self.__coupon_list
    
    ### --------- API --------- ###
    
    def preview_booking_details(self, booking_id: str):
        booking = self.get_booking(booking_id)
        return booking.get_details()
    
    def process_pay_deposit(self, booking_id: str, method_name: str, payment_details: Dict[str, Any]):
        booking = self.get_booking(booking_id)
        method = self.get_payment_method(method_name)
        if booking.status != BookingStatus.PENDING:
            raise HTTPException(400, "Booking Already Paid")
        
        return booking.pay_deposit(method, payment_details)
    
    def process_order_payment(self, order_id: str, coupon_code: Optional[str], method_name: str, payment_details: Dict[str, Any]):
        method = self.get_payment_method(method_name)
        order = self.get_order(order_id)
        
            
        if order.status == OrderStatus.PAIDED: 
            raise HTTPException(400, "Order Already Paid")
            
        receipt = order.execute_payment(method, payment_details, coupon_code)
        self.add_receipts(receipt)
        
        reward_code = self.check_and_issue_reward(order)
        
        receipt_data = receipt.generate()
        if reward_code:
            receipt_data["reward_issued"] = f"Congratulations! You received a new coupon: {reward_code}"
            
        return receipt_data
    
    def preview_order_bill(self, order_id: str, coupon_code: Optional[str]):
        order = self.get_order(order_id)
        if order.status == OrderStatus.PAIDED: raise HTTPException(400, "Order Already Paid")
        return order.pre_calculate_totals(coupon_code)
    
restaurant = Restaurant()