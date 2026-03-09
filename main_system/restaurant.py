from __future__ import annotations
from main_system.authentication import AuthManager
from main_system.ingredient import Item, Ingredient
from main_system.external_platform.delivery_provider import DeliveryProvider, Delivery
from main_system.external_platform.payment_method import PaymentMethod
from main_system.utils.simulate import SimulationClock
from main_system.coupon import Coupon, FixedAmountCoupon, PercentCoupon
from main_system.utils.enum import BookingStatus, UserRole
from main_system.booking import Room, TimeSlot, Booking
from typing import Optional, List, Dict, Any

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from main_system.utils.enum import MemberTier, MenuItemStatus, ItemStatus, IngredientType, OrderStatus, OrderType, OrderItemStatus, DeliveryStatus
from pydantic import BaseModel
import uuid
import random
import copy
import asyncio

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
    @property
    def username(self): return self.__username
    
    def check_username(self, username: str) -> bool:
        return self.__username == username
    def check_identity(self, username: str, password: str) -> bool:
        return self.__username == username and self.__password == password
    
    def __eq__(self, other):
        return (type(other) is type(self)) and self.__name == other.name and self.__id == other.id and self.__phone_number == other.phone_number
class Staff(User):
    def __init__(self, id: str, name: str, phone_number: str, username: str="", password: str="", is_admin: Optional[bool] = False):
        super().__init__(id, name, phone_number, username, password)
        self.__is_admin = is_admin
    
    @property
    def is_admin(self) -> bool: return self.__is_admin

class Customer(User):
    pass
class Guest(Customer):
    __Guest_count = 0
    def __init__(self, id = None):
        if id == None:
            self.__id = f"GUEST-{Guest.__Guest_count:0{3}d}"
            Guest.__Guest_count += 1
        else: 
            self.__id = id

    @property
    def name(self): return f"GUEST"
    @property
    def id(self): return self.__id

    def __eq__(self, other):
        return (type(other) is type(self)) and self.__id == other.id

class Member(Customer):
    def __init__(self, id: str, name: str, tier: MemberTier, username: str, password: str, phone: str = ""):
        super().__init__(id, name, phone, username, password)
        self.__coupon_list: List[Coupon] = [] 
        self.__receipt_list: List[Receipt] = []
        self.__tier: MemberTier = tier
        self.__points: int = 0

    def add_receipt(self, receipt: Receipt): self.__receipt_list.append(receipt)
    def add_coupon(self, coupon: Coupon): self.__coupon_list.append(coupon)
    def add_points(self, points: int): 
        if points <= 0:
            raise ValueError("INVALID: Points")
        self.__points += points

    def check_and_issue_member_teir(self):
        if self.__points >= 1500:
            self.__tier = MemberTier.GOLD
            self.__points = 0
            return self.__tier
        elif self.__points >= 800:
            self.__tier = MemberTier.SILVER
            self.__points = 0
            return self.__tier
        elif self.__points >= 300:
            self.__tier = MemberTier.BRONZE
            self.__points = 0
            return self.__tier
        return None
    
    def get_coupon_by_code(self, code: str):
        for coupon in self.__coupon_list:
            if coupon.code == code: return coupon
        raise LookupError("Coupon Not Found")

    def get_member_discount(self, base_price: float):
        match self.tier:
            case MemberTier.GENERAL: return 0.0
            case MemberTier.BRONZE: return base_price * 0.05
            case MemberTier.SILVER: return base_price * 0.10
            case MemberTier.GOLD: return base_price * 0.15
        return 0.0

    @property
    def points(self) -> int: return self.__points
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
            if restaurant.count_stock_item(ingredient.item.name, ItemStatus.AVAILABLE) < ingredient.quantity:
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
            menu = restaurant.search_menu_item_from_name(self.name)
            self.update_price(menu)
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
    __OrderId_count = 0

    def __init__(self, customer: Customer):
        self.__id = f"ORD-{Order.__OrderId_count:0{3}d}"
        Order.__OrderId_count += 1
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

    def add_order_item(self, menu_name: str, quantity: int):
        if not (self.__status == OrderStatus.PENDING or self.__status == OrderStatus.RESERVED):
            raise ValueError(f"Can not add order item. ({self.__status})")
        try:
            menu = restaurant.search_menu_item_from_name(menu_name)
            new_menu = copy.deepcopy(menu)
            current_order_item = OrderItem(self.__order_item_id_count, new_menu, quantity)
            self.__order_item_id_count += 1
        except ValueError as e:
            raise ValueError(str(e))
        self.__order_item_list.append(current_order_item)
        current_order_item.status = OrderItemStatus.ADDED
        self.update_price()
    
    def is_valid_order_item_id(self, order_item_id: int):
        if order_item_id >= self.__order_item_id_count or order_item_id < 0:
            return False
        return True
    
    def remove_order_item(self, order_item_id: int):
        if not (self.__status == OrderStatus.PENDING or self.__status == OrderStatus.RESERVED):
            raise ValueError(f"Can not remove order item. ({self.__status})")
        if not self.is_valid_order_item_id(order_item_id):
            raise ValueError("Order Item NOT FOUND")
        for e in range(len(self.__order_item_list)):
            if self.__order_item_list[e].id == order_item_id:
                self.__order_item_list.pop(e)
                return
        raise ValueError("Order Item NOT FOUND")

    
    def search_order_item_from_id(self, order_item_id: int):
        if self.is_valid_order_item_id(order_item_id):
            for order_item in self.__order_item_list:
                if order_item.id == order_item_id:
                    return order_item
        raise ValueError("Order Item NOT FOUND")

    def custom(self,order_item_id: int, item_name: str, quantity: int):
        if not (self.__status == OrderStatus.PENDING or self.__status == OrderStatus.RESERVED):
            raise ValueError(f"Can not custom order item. ({self.__status})")
        try:
            order_item = self.search_order_item_from_id(order_item_id)
            order_item.custom_menu(item_name, quantity)
            self.update_price()
        except ValueError as e:
            raise ValueError(str(e))
        except TypeError as e:
            raise TypeError(str(e))

    def add_booking(self, booking: 'Booking'):
        if self.booking: raise ValueError("Booking Already Exists")
        self.__booking = booking

    def add_delivery(self, delivery: Delivery):
        if self.delivery: raise ValueError("Delivery Already Exists")
        self.__delivery = delivery

    def update_price(self):
        count_price = 0
        for order_item in self.__order_item_list:
            if order_item.status != OrderItemStatus.OUT_OF_STOCK and order_item.status != OrderItemStatus.CANCELED:
                count_price += order_item.price
        self.__subtotal = count_price
        return count_price

    def check_customer(self, customer: Customer):
        if self.__customer != customer:
            raise ValueError("Wrong Customer")
        return True
    
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
        self.update_price()
        return self
    
    def order_confirm(self):
        if self.__status == OrderStatus.PENDING:
            raise ValueError("Reserve Food First.")
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
            "order_type": self.order_type,
            "order_status": self.__status,
            "customer": self.__customer.name,
            "order_item_list": self.order_item_dict_list(),
            "total_price": self.__subtotal
        }
        
    def cook(self):
        if self.__status not in [OrderStatus.RESERVED, OrderStatus.PAID]:
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

    def serve(self) -> Order:
        if self.__status != OrderStatus.READY:
            raise ValueError("Status is not READY") 
        self.status = OrderStatus.SERVED
        for item in self.__order_item_list:
            item.status = OrderItemStatus.SERVED
        return self
            
            

    def pre_calculate_totals(self, coupon_code: Optional[str] = None):
        coupon = None
        if coupon_code:
            if isinstance(self.__customer, Member):
                coupon = self.__customer.get_coupon_by_code(coupon_code)
            else:
                raise ValueError("Only members can use coupons")
        
        subtotal = sum(item.price for item in self.__order_item_list)
        deposit = 0.0

        booking_full_price = 0.0
        if self.__booking:
            booking_full_price = self.__booking.full_price
            deposit = self.__booking.deposit

        if self.__delivery:
            subtotal += self.__delivery.fee

        coupon_discount = 0.0
        if coupon:
             if not coupon.is_available():
                raise ValueError("Coupon Not Available")
             coupon_discount = coupon.apply_coupon(subtotal)
        
        teir_discount = 0.0
        if isinstance(self.__customer, Member):
            teir_discount = self.__customer.get_member_discount(subtotal)
        
        subtotal += booking_full_price

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
            "Coupon Remaining Usage": (coupon.max_usage - coupon.used_count) if coupon else "None",
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
                raise ValueError("Only members can use coupons")
            
        info = self.calculate_totals(coupon_code)
        total_payable = info["Final Price"]

        if total_payable > 0:
            success, note = method.pay(total_payable, **payment_details)
        else:
            success = True
            note = "Payment Done"

        if success:
            self.status = OrderStatus.PAID

            if self.__booking:
                self.__booking.mark_as_paid()
            
            if self.__delivery:
                restaurant.update_delivery_status(self.id, DeliveryStatus.PAID, _internal=True)
                restaurant.update_delivery_status(self.id, DeliveryStatus.DRIVER_ASSIGNED, _internal=True)

            if coupon: coupon.consume()

            receipt = Receipt(self, method)
            if isinstance(self.__customer, Member):
                deposit = self.__booking.deposit if self.__booking else 0.0
                self.__customer.add_points(round((total_payable + deposit)/10))
                self.__customer.add_receipt(receipt)
            return receipt
        else:
            raise ValueError(note)
        
    def void_order(self):
        if self.__status == OrderStatus.PENDING or self.__status == OrderStatus.RESERVED or self.__status == OrderStatus. CONFIRMED:
            for order_item in self.__order_item_list:
                if order_item.status == OrderItemStatus.RESERVED:
                    order_item.cancel_reservation()
                    order_item.status = OrderItemStatus.CANCELED
            self.status = OrderStatus.CANCELED
            return
        raise ValueError("Can not void order.")

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
        coupon_remaining = (order.coupon_used.max_usage - order.coupon_used.used_count) if order.coupon_used else "None"
        deposit_deducted = order.booking.deposit if order.booking else 0.0
        
        return {
            "receipt_no": self.id,
            "date": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "merchant": "Knight Chicken Fast Food Co.",
            
            "customer_info": {
                "name": order.customer.name,
                "tier": order.customer.tier if isinstance(order.customer, Member) else "None",
                "points": order.customer.points if isinstance(order.customer, Member) else 0
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
                "coupon_remaining_usage": coupon_remaining,
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
        raise LookupError("Delivery Provider Not Found")
    
    def add_room(self, room: Room): self.__room_list.append(room)
    def get_room(self, room_id: str) -> Room:
        for r in self.__room_list:
            if r.id == room_id: return r
        raise LookupError("Room Not Found")
    
    def add_booking(self, booking: Booking): self.__booking_list.append(booking)
    def get_booking(self, booking_id: str) -> Booking:
        for b in self.__booking_list:
            if b.id == booking_id: return b
        raise LookupError("Booking Not Found")

    def add_order(self, order: Order): self.__order_list.append(order)
    def get_order(self, order_id: str) -> Order:
        for o in self.__order_list:
            if o.id == order_id: return o
        raise LookupError("Order Not Found")

    def add_payment_method(self, method: PaymentMethod): self.__payment_method.append(method)
    def get_payment_method(self, method_name: str) -> PaymentMethod:
        for s in self.__payment_method:
            if s.name.lower() == method_name.lower(): return s
        raise ValueError("Invalid Payment Method")

    def add_receipts(self, receipt: Receipt): 
        self.__receipt_list.append(receipt)

    def get_receipts_by_order_id(self, order_id: str) -> Receipt:
        for r in self.__receipt_list:
            if r.order.id == order_id: return r
        raise LookupError("Receipt Not Found")

    def add_member(self, member: Member): self.__member_list.append(member)
    def get_member_by_id(self, id: str) -> Member:
        for m in self.__member_list:
            if m.id == id: return m
        raise LookupError("Member Not Found")
    
    def add_coupon(self, coupon: 'Coupon'): self.__coupon_list.append(coupon)
    def get_coupon(self, code: str) -> 'Coupon': 
        for c in self.__coupon_list: 
            if c.code == code: return c
        raise LookupError("Coupon Not Found")

    def add_staff(self, staff: 'Staff'): self.__staff_list.append(staff)    
    def get_staff(self, id: str) -> 'Staff':
        for s in self.__staff_list:
            if s.id == id: return s
        raise LookupError("Staff Not Found")

    def get_user_by_id(self, id: str) -> User:
        for m in self.__member_list:
            if m.id == id: return m
        for s in self.__staff_list:
            if s.id == id: return s
        return None

    def verify_token_and_role(self, token: str, allowed_roles: List[str]) -> User:
        session = self.__auth_manager.get_session(token)
        if not session:
            raise PermissionError("Invalid or expired token")

        user = self.get_user_by_id(session.user_id)
        if isinstance(user, Staff):
            if user.is_admin:
                user_role = UserRole.ADMIN
            else:
                user_role = UserRole.STAFF
        elif isinstance(user, Member):
            user_role = UserRole.MEMBER
        else:
            user_role = UserRole.GUEST
            return Guest(session.user_id)
        
        if user_role not in allowed_roles:
            raise PermissionError(f"Access Forbidden: Requires one of {allowed_roles}")

        return user    
    
    def check_order_customer(self, order_id: str, token: str, allowed_roles: List[str]) -> Order:
        try:
            current_customer = restaurant.verify_token_and_role(token=token, allowed_roles=allowed_roles)
            current_order = restaurant.search_order_from_id(order_id)
            current_order.check_customer(current_customer)
            return current_order
        except Exception as e:
            raise ValueError(str(e))
    
    def create_general_order(self, customer: Customer):
        order = Order(customer)
        restaurant.add_order(order)
        return {
            "Order ID": order.id,
            "Customer": customer.name
        }

    def add_menu(self, menu: MenuItem): self.__menu.append(menu)
    
    @property
    def count_order(self): return len(self.__order_list)

    @property
    def check_queue(self):
        count_queue = 0
        for order in self.__order_list:
            if order.status == OrderStatus.PAID or order.status == OrderStatus.COOKING:
                count_queue += 1
        return count_queue
        
    def add_stock(self, item: Item, quantity: int):
        for e in range(quantity):
            self.__stock.append(copy.deepcopy(item))

    def get_queue(self, queue_order: int):
        count_queue = 0
        for order in self.__order_list:
            if order.status == OrderStatus.PAID or order.status == OrderStatus.COOKING:
                count_queue += 1
            if count_queue == queue_order:
                return order
        return False
    
    def count_stock_item(self, item_name: str, status: ItemStatus):
        count_stock = 0
        for find in self.__stock:
            if find.name == item_name and find.status == status:
                count_stock += 1
        return count_stock
    
    def check_stock_item(self, item_name: str):
        item_available = self.count_stock_item(item_name, ItemStatus.AVAILABLE)
        item_reserved = self.count_stock_item(item_name, ItemStatus.RESERVED)
        return {
            "Item": item_name,
            "Available": item_available,
            "Reserved": item_reserved
        }
    
    def all_stock(self):
        item_name_list = []
        for item in self.__stock:
            for name in item_name_list:
                if item.name == name:
                    break
            else:
                item_name_list.append(item.name)
        item_list = []
        for name in item_name_list:
            item_list.append(self.check_stock_item(name))
        return{
            "Stock" : item_list
        }
    
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

    def reserve(self, order: Order):
        if restaurant.check_queue >= 50:
            raise RuntimeError("Queue Overload")
        if order.status == OrderStatus.PENDING or order.status == OrderStatus.RESERVED:
            return order.order_reserve().order_to_dict()
        else:
            raise ValueError(f"{order.status}")
    
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
        if self.count_stock_item(item_name, ItemStatus.RESERVED) < quantity:
            raise ValueError("reverse thing you should not")
        count = 0
        for item_index in range(len(self.__stock) - 1, -1, -1):
            if count == quantity:
                return True
            item = self.__stock[item_index]
            if item.name == item_name and item.status == ItemStatus.RESERVED:
                item.status = ItemStatus.AVAILABLE
                count += 1
    
    def add_item_in_order(self, order: Order, menu: str, quantity: int):
        try:
            order.add_order_item(menu, quantity)
            return order.order_to_dict()
        except Exception as e:
            raise ValueError(str(e))
    def remove_item_in_order(self, order: Order, order_item_id: str):
        try:
            order.remove_order_item(order_item_id)
            return order.order_to_dict()
        except Exception as e:
            raise ValueError(str(e))
    def custom_item_in_order(self, order: Order, order_item_id: int, item_name: str, quantity: int):
        try:
            order.custom(order_item_id, item_name, quantity)
            return order.order_to_dict()
        except Exception as e:
            raise ValueError(str(e))
        
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

    def get_kitchen_queue(self):     
        queue_list = []
        for order in self.__order_list:
            if order.status == OrderStatus.PAID:
                queue_list.append(
                {"order_id": order.id,
                 "order_type": order.order_type.value,
                 "status":order.status.value,
                 "items":[
                     {"name": item.menu_item.name,
                      "quantity": item.quantity,
                      "status":item.status.value
                     }
                     for item in order.order_item
                 ]}
            )
        return {
            "total_queue": len(queue_list),
            "order":queue_list
        }
    def display_kitchen_queue(self):
        queue = restaurant.get_kitchen_queue()
        if queue["total_queue"]==0:
            return {"message": "No order in queue ","queue": queue}
        return {"message": "Current queue ","queue": queue}
        
    def confirm(self, order:Order):
        try:
            confirmed_order = order.order_confirm()
            return confirmed_order.order_to_dict()
        except ValueError as e:
            raise ValueError(str(e))
    
    def void_order_from_id(self, order_id: str):
        order = restaurant.search_order_from_id(order_id)
        order.void_order()
    def serve_order(self, order_id: str):
        try:
            order = restaurant.search_order_from_id(order_id)
            return order.serve().order_to_dict()
        except ValueError as e:
            raise ValueError(str(e))
    
    def cook_order(self, order_id: str):
        order = restaurant.search_order_from_id(order_id)
        success = order.cook()
        if success:
            if order.delivery:
                asyncio.create_task(restaurant.simulate_delivery(order_id))
            return {"message": "Cooking finished. Order is READY.", "status": order.status.value}
        else:
            raise ValueError(f"Cannot cook order. Current status: {order.status.value}")
        
    def create_delivery_order(self, customer: 'User', provider_name: str, distance: float):
        provider = self.get_delivery_provider(provider_name)
        
        order = Order(customer)
        
        delivery_id = f"DEL-{random.randint(1000, 9999)}"
        delivery = Delivery(delivery_id, provider, distance)
        order.add_delivery(delivery)
        
        self.add_order(order)
        return {
            "order_id": order.id,
            "customer_name": customer.name,
            "delivery_id": delivery.id,
            "provider": provider.platform_name,
            "distance": distance
        }

    def update_delivery_status(self, order_id: str, new_status: DeliveryStatus, _internal: bool = False):
        order = self.get_order(order_id)
        if not order.delivery:
            raise ValueError("Order is not a delivery order")
        
        if not _internal and new_status != DeliveryStatus.CANCELED:
            raise ValueError(f"Manual update to {new_status.value} is not allowed. Only 'Canceled' can be set manually.")

        if new_status == DeliveryStatus.DRIVER_ASSIGNED:
            order.delivery.request_rider()
        elif new_status == DeliveryStatus.IN_TRANSIT:
            order.delivery.mark_in_transit()
        elif new_status == DeliveryStatus.DELIVERED:
            order.delivery.mark_delivered()
            order.status = OrderStatus.SERVED
        elif new_status == DeliveryStatus.CANCELED:
            order.delivery.mark_canceled()
            order.status = OrderStatus.CANCELED
        elif new_status == DeliveryStatus.PAID:
            order.delivery.mark_as_paid()
        
        return {
            "message": f"Delivery status updated to {new_status.value}",
            "order_id": order.id,
            "delivery_details": order.delivery.get_details()
        }
    
    
    def check_and_issue_reward(self, order: 'Order'):
        if not isinstance(order.customer, Member):
            return None

        member = order.customer
        spending = order.subtotal
        if not spending: return None
    
        reward_coupon = None

        if spending >= 5000:
            code = f"RW20-{uuid.uuid4().hex[:6].upper()}"
            reward_coupon = FixedAmountCoupon(f"CPN-{code}", code, 1000.0, 300.0, max_usage=2)
        elif spending >= 3000:
            code = f"RW20-{uuid.uuid4().hex[:6].upper()}"
            reward_coupon = PercentCoupon(f"CPN-{code}", code, 1000.0, 20.0, max_usage=1)
        elif spending >= 1000:
            code = f"RWF100-{uuid.uuid4().hex[:6].upper()}"
            reward_coupon = FixedAmountCoupon(f"CPN-{code}", code, 500.0, 100.0, max_usage=1)

        if reward_coupon:
            member.add_coupon(reward_coupon)
            return reward_coupon
            
        return None

    def get_payment_method(self, method_name: str) -> 'PaymentMethod':
        for s in self.__payment_method:
            if s.name.lower() == method_name.lower(): return s
        raise ValueError("Unknown Payment Method")
    
    def booking_room(self, member_id: str, room_id: str, hours: int, pay_method: str, start_time: datetime, payment_details: Dict[str, Any] = {}):
        member = self.get_member_by_id(member_id)
        room = self.get_room(room_id)
        if not self.is_slot_avaliable(room, start_time, hours):
            raise ValueError("Time slot already occupied")
        if start_time < SimulationClock.get_time():
            raise ValueError("Invalid start time")

        time_slot = TimeSlot(start_time, hours)
        full_price = room.price_per_hour * time_slot.hours - member.get_member_discount(room.price_per_hour * time_slot.hours)
        self.process_pay_deposit(full_price * 0.5, pay_method, payment_details)

        booking_id = f"BK-{self.__booking_counter:03d}"
        self.__booking_counter += 1
        booking = Booking(booking_id, member, room, time_slot)
        booking.mark_as_deposit_paid()
        self.add_booking(booking)

        return {
                "booking_no": booking.id,
                "date": SimulationClock.get_time().strftime("%Y-%m-%d %H:%M:%S"),
                "merchant": "Knight Chicken Fast Food Co.",
                "customer_info": {"name": booking.member.name, "tier": booking.member.tier},
                "booking_details": booking.get_details(),
                "financial_summary": {"subtotal": booking.full_price, "deposit paid": booking.deposit, "amount_due": booking.amount_due},
                "payment_record": {"method": pay_method, "status": "deposit Paid"}
                }

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

    def check_in_booking(self, order_id: str, booking_id: str, coupon_code: str, pay_method: str, payment_details: Dict[str, Any] = {}):
        booking = self.get_booking(booking_id)
        if booking.status == BookingStatus.CANCELLED:
            raise ValueError("Booking is cancelled")
        if booking.status == BookingStatus.CHECKED_IN:
            raise ValueError("Booking already checked in")
        if booking.status != BookingStatus.DEPOSIT_PAID or booking.time_slot.start_time > SimulationClock.get_time():
            raise ValueError("Booking is not ready for check-in ")
        order = self.get_order(order_id)
        if not order or order.customer != booking.member:
            raise LookupError("Order not found or member does not match booking")
        order.add_booking(booking)

        receipt_data = self.process_order_payment(order_id=order.id, coupon_code=coupon_code, method_name=pay_method, payment_details=payment_details)

        booking.mark_checked_in()
        return {"message": f"Booking {booking_id} checked in successfully",
                "room_id": booking.room.id,
                "member_name": booking.member.name,
                "check_in_time": SimulationClock.get_time().strftime("%Y-%m-%d %H:%M:%S"),
                "receipt_data": receipt_data,
                "full_amount_paid": order.total_payable_amount
                }

    def check_out_booking(self, booking_id: str):
        booking = self.get_booking(booking_id)
        if booking.status != BookingStatus.CHECKED_IN:
            raise ValueError("Booking is not currently checked in")
        
        booking.mark_completed()
        return {"message": f"Booking {booking_id} checked out successfully",
                "room_id": booking.room.id,
                "member_name": booking.member.name,
                "check_out_time": SimulationClock.get_time().strftime("%Y-%m-%d %H:%M:%S")}

    def cancel_booking(self, booking_id):
        booking = self.get_booking(booking_id)
        if booking.status == BookingStatus.CHECKED_IN or booking.status == BookingStatus.CANCELLED or booking.status == BookingStatus.COMPLETED:
            raise ValueError("Booking can't canceled")
        booking.mark_cancelled()
        return {"message": f"Booking {booking_id} cancelled successfully",
                "room_id": booking.room.id,
                "member_name": booking.member.name,
                "cancel_time": SimulationClock.get_time().strftime("%Y-%m-%d %H:%M:%S")}

    def login(self, username, password):
        member = next((m for m in self.__member_list if m.check_identity(username, password)), None)
        staff = next((s for s in self.__staff_list if s.check_identity(username, password)), None)
        if member:
            return self.__auth_manager.create_session(member.id)
        
        if staff:
            return self.__auth_manager.create_session(staff.id)
        
        raise PermissionError("Invalid username or password")
    
    def add_guest_session(self):
        new_guest = Guest()
        return self.__auth_manager.create_session(new_guest.id)

    def logout(self, token: str):
        session = self.__auth_manager.get_session(token)
        if session:
            session.invalidate()
            return True
        return False
    
    def register_member(self, username: str, password: str, name: str, phone: str = "0000000000") -> 'Member':
        if any(m.check_username(username) for m in self.__member_list) or any(s.check_username(username) for s in self.__staff_list):
            raise ValueError("Username already exists")
        
        new_id = f"M-{self.__member_counter:03d}"
        new_member = Member(new_id, name, MemberTier.BRONZE, username, password, phone)
        
        self.__member_list.append(new_member)
        self.__member_counter += 1
        return new_member

    def register_staff(self, username: str, password: str, name: str, phone: str = "0000000000") -> 'Staff':
        if any(s.check_username(username) for s in self.__staff_list) or any(m.check_username(username) for m in self.__member_list):
            raise ValueError("Username already exists")

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
    
    def preview_booking_details(self, booking_id: str):
        booking = self.get_booking(booking_id)
        return booking.get_details()
    
    def process_pay_deposit(self, deposit: float,  method_name: str, payment_details: Dict[str, Any]):
        method = self.get_payment_method(method_name)
        success, note = method.pay(deposit, **payment_details)
        if not success: raise ValueError(note)
        return success
    
    def process_order_payment(self, order_id: str, coupon_code: Optional[str], method_name: str, payment_details: Dict[str, Any]):
        method = self.get_payment_method(method_name)
        order = self.get_order(order_id)
        
            
        if order.status == OrderStatus.PAID: 
            raise ValueError("Order Already Paid")
            
        receipt = order.execute_payment(method, payment_details, coupon_code)
        self.add_receipts(receipt)

        teir_reward = None
        if isinstance(order.customer, Member):
            teir_reward = order.customer.check_and_issue_member_teir()
        
        reward_coupon = self.check_and_issue_reward(order)
        
        receipt_data = receipt.generate()
        if teir_reward:
            receipt_data["teir_issued"] = f"Congratulations! You received a new teir: {teir_reward}"
        if reward_coupon:
            receipt_data["reward_issued"] = f"Congratulations! You received a new coupon: {reward_coupon.code} , Can Use for : {reward_coupon.max_usage} Times"
            
        return receipt_data
    
    def preview_order_bill(self, order_id: str, coupon_code: Optional[str]):
        order = self.get_order(order_id)
        if order.status == OrderStatus.PAID: raise ValueError("Order Already Paid")
        return order.pre_calculate_totals(coupon_code)

    async def simulate_delivery(self, order_id: str):
        try:
            await asyncio.sleep(5)
            self.update_delivery_status(order_id, DeliveryStatus.IN_TRANSIT, _internal=True)
            
            await asyncio.sleep(5)
            self.update_delivery_status(order_id, DeliveryStatus.DELIVERED, _internal=True)
            
        except Exception as e:
            print(f"Failed to auto-transition delivery {order_id}: {e}")
    
restaurant = Restaurant()