import uuid
import uvicorn
from typing import Union
from fastapi import FastAPI, HTTPException
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pydantic import BaseModel
from enum import Enum
import copy

class User(ABC):
    @staticmethod
    def is_valid_phone_number(phone_number: str):
        return len(phone_number) == 10 and phone_number.isdigit()
    
    def __init__(self, id: str, name: str, phone_number: str):
        if not User.is_valid_phone_number(phone_number):
            raise ValueError("INVALID: Phone number")
        self.__id = id
        self.__name = name
        self.__phone_number = phone_number
    
    @property
    def id(self):
        return self.__id
    @property
    def name(self):
        return self.__name
    @property
    def phone_number(self):
        return self.__phone_number
    
    def __eq__(self, other):
        return (type(other) is type(self)) and self.__name == other.name and self.__id == other.id and self.__phone_number == other.phone_number
    
    
class Staff(User):
    pass

class Customer(User):
    pass

class Guest(Customer):
    class GuestDTO(BaseModel):
        id: str
        name: str
        phone_number: str

class Item:
    class ItemStatus(Enum):
        AVAILABLE = "Available"
        RESERVED = "Reserved"

    @staticmethod
    def is_valid_price(price: float):
        return price > 0
    
    def __init__(self, name: str, price: float):
        if not Item.is_valid_price(price):
            raise ValueError("INVALID: Price")
        self.__name = name
        self.__price = price
        self.__status = Item.ItemStatus.AVAILABLE

    class ItemDTO(BaseModel):
        name: str
        price: float

    @property
    def name(self):
        return self.__name
    
    @property
    def price(self):
        return self.__price
    
    @property
    def status(self):
        return self.__status
    
    def update_status(self, status: ItemStatus):
        self.__status = status
    
    def __eq__(self, other):
        return (type(other) is type(self)) and self.__name == other.name and self.__price == other.price
    
class Ingredient:
    class IngredientType(Enum):
        STRICT = "Strict"
        CUSTOMIZABLE = "Customizable"

    @staticmethod
    def is_valid_quantity(quantity: int):
        return quantity >= 0

    def __init__(self, item: Item, quantity: int, type: IngredientType):
        if not Ingredient.is_valid_quantity(quantity):
            raise ValueError("INVALID: Quantity")
        self.__item = item
        self.__quantity = quantity
        self.__type = type

    @property
    def item(self):
        return self.__item
    @property
    def quantity(self):
        return self.__quantity
    @property
    def type(self):
        return self.__type
    
    def modify(self, quantity: int):
        if not self.is_valid_quantity(quantity):
            raise ValueError("INVALID: Quantity")
        self.__quantity = quantity

    @property
    def custom_add(self):
        if self.__type == self.IngredientType.CUSTOMIZABLE:
            self.__quantity += 1
        else:
            raise TypeError("CAN NOT Custom this Item.")

    @property   
    def custom_sub(self):
        if self.__type == self.IngredientType.CUSTOMIZABLE:
            if not self.is_valid_quantity(self.__quantity - 1):
                raise ValueError("INVALID: Quantity")
            else:
                self.__quantity -= 1
        else:
            raise TypeError("CAN NOT Custom this Item.")
        
    @property
    def ingredient_to_dict(self):
        return {
            "name": self.__item.name,
            "quantity": self.__quantity
        }
        
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
        self.__status = MenuItem.MenuItemStatus.OUT_OF_STOCK
    
    class MenuItemStatus(Enum):
        AVAILABLE = "Available"
        OUT_OF_STOCK = "Out of Stock"
        DELETED = "Deleted"

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

    def update_status(self, status: MenuItemStatus):
        self.__status = status

    def to_dict_order(self, restaurant: 'Restaurant'):
        original_menu = restaurant.search_menu_item_from_name(self.name)
        self.update_price(original_menu)
        return {
            "name": self.__name,
            "price": self.__price
        }

    def to_dict_menu(self, restaurant: 'Restaurant'):
        self.__status = MenuItem.MenuItemStatus.AVAILABLE
        custom: list[Ingredient] = []
        for ingredient in self.all_ingredient:
            if restaurant.check_stock(ingredient.item.name, Item.ItemStatus.AVAILABLE) < ingredient.quantity:
                self.__status = MenuItem.MenuItemStatus.OUT_OF_STOCK
                break
            if ingredient.type == Ingredient.IngredientType.CUSTOMIZABLE:
                custom.append(ingredient.ingredient_to_dict)
        if custom:
            return {
                "name": self.__name,
                "customizable": custom,
                "price": self.__price,
                "status": self.__status
            }
        else:
            return {
                "name": self.__name,
                "price": self.__price,
                "status": self.__status
            }
        
class SingleMenuItem(MenuItem):
    def __init__(self, name: str, price: float, cooking_time: datetime, recipe: list):
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
    
    def calculate_price(self, original_menu: MenuItem):
        add_price = 0
        for ingredient in self.all_ingredient:
            if ingredient.type == Ingredient.IngredientType.CUSTOMIZABLE:
                original_ingredient_quantity = original_menu.find_ingredient_in_recipe(ingredient.item).quantity
                ingredient_add = ingredient.quantity - original_ingredient_quantity
                if ingredient_add > 0:
                    add_price += ingredient_add * ingredient.item.price
        return add_price + original_menu.price

    @property
    def all_ingredient(self):
        return self.__recipe
    
    def custom_add(self, item: Item):
        try:
            ingredient = self.__find_ingredient_in_recipe(item)
            ingredient.custom_add
        except ValueError as e:
            raise ValueError(str(e))
        except TypeError as e:
            raise TypeError(str(e))
        
    def custom_sub(self, item: Item):
        try:
            ingredient = self.__find_ingredient_in_recipe(item)
            ingredient.custom_sub
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
        ingredients: list[Ingredient] = []
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

    class OrderItemStatus(Enum):
        NONE = "None"
        ADDED = "Added to Order"
        AVAILABLE = "Available"
        OUT_OF_STOCK = "Out of Stock"
        COOKING = "Cooking"
        FINISHED = "Finished"
        CANCEL = "Cancel"

    @staticmethod
    def is_valid_quantity(quantity: int):
        return quantity > 0
    
    def __init__(self, id: int, menu: MenuItem, quantity: int):
        if not OrderItem.is_valid_quantity(quantity):
            raise ValueError("INVALID: Order Item Quantity")
        self.__id = id
        self.__menu_item = menu
        self.__quantity = quantity
        self.__status = self.OrderItemStatus.NONE

    @property
    def id(self):
        return self.__id
    @property
    def price(self):
        return self.__quantity * self.__menu_item.price
    @property
    def status(self):
        return self.__status
    
    def update_status(self, status: OrderItemStatus):
        self.__status = status
        
    def order_item_reserve(self, restaurant: 'Restaurant'):
        try:
            for ingredient in self.__menu_item.all_ingredient:
                success = restaurant.stock_reserve(ingredient.item.name, ingredient.quantity * self.__quantity)
                if not success:
                    self.order_item_reverse(restaurant, ingredient)
                    self.update_status(OrderItem.OrderItemStatus.OUT_OF_STOCK)
                    return
            else:
                self.update_status(OrderItem.OrderItemStatus.AVAILABLE)
        except ValueError as e:
            raise ValueError(str(e))
    def order_item_reverse(self, restaurant: 'Restaurant', ingredient: Ingredient):
        for reserved_ingredient in self.__menu_item.all_ingredient:
            if reserved_ingredient.item.name == ingredient.item.name:
                return
            restaurant.stock_reverse(reserved_ingredient.item.name, reserved_ingredient.quantity * self.__quantity)

    def order_item_to_dict(self, restaurant: 'Restaurant'):
        return {
            "id": self.__id,
            "menu": self.__menu_item.to_dict_order(restaurant),
            "quantity": self.__quantity,
            "status": self.__status
        }
    
class Order:
    class OrderType(Enum):
        GENERAL = "General"
        EVENT = "Event"
        DELIVERY = "Delivery"
    class OrderStatus(Enum):
        NONE = "None"
        RESERVED = "Reserved"
        CONFIRMED = "Confirmed"
        PAIDED = "Paided"
        COOKING = "Cooking"
        FINISHED = "Finished"
        SERVED = "Served"
        CANCELLED = "Cancelled"

    class OrderDTO(BaseModel):
        order_id: str
        order_type: str
        order_status: str
        customer: str
        food_list: list
        total_price: float

    def __init__(self, id: str, type: OrderType, customer: Customer):
        self.__id = id
        self.__type = type
        self.__customer = customer
        self.__order_item_list: list[OrderItem] = []
        self.__order_item_id_count = 0
        self.__sub_total_price = 0
        self.__final_price = 0
        self.__status_start = datetime.now()
        self.__status = self.OrderStatus.NONE
        self.__booking = None
        self.__delivery = None

    @property
    def status(self):
        return self.__status
    @property
    def id(self):
        return self.__id
    @property
    def update_price(self):
        count_price = 0
        for order_item in self.__order_item_list:
            if order_item.status != OrderItem.OrderItemStatus.OUT_OF_STOCK and order_item.status != OrderItem.OrderItemStatus.CANCEL:
                count_price += order_item.price
        self.__sub_total_price = count_price
    
    def update_status(self, order_status: OrderStatus):
        self.__status = order_status
        self.__status_start = datetime.now()

    def check_customer(self, customer: Customer):
        if self.__customer != customer:
            raise ValueError("Wrong Customer")
    
    def add_order_item(self, menu: MenuItem, quantity: int):
        try:
            new_menu = copy.deepcopy(menu)
            current_order_item = OrderItem(self.__order_item_id_count, new_menu, quantity)
            self.__order_item_id_count += 1
        except ValueError as e:
            raise ValueError(str(e))
        self.__order_item_list.append(current_order_item)
        current_order_item.update_status(OrderItem.OrderItemStatus.ADDED)
        self.update_price

    def search_order_item_from_id(self, order_item_id: int):
        for order_item in self.__order_item_list:
            if order_item.id == order_item_id:
                return order_item
        raise ValueError("Order Item NOT FOUND")

    def order_reserve(self, restaurant: 'Restaurant'): # (ควรแก้ชื่อเป็น reserve_stock)
        for order_item in self.__order_item_list:
            if order_item.status == OrderItem.OrderItemStatus.ADDED:
                order_item.order_item_reserve(restaurant)
        self.update_status(Order.OrderStatus.RESERVED)
        return self
    
    def order_confirm(self): # (ควรแก้เป็น finalize_order)
        if self.__status == Order.OrderStatus.NONE:
            raise ValueError("Ordering Food First.")
        if self.__status == Order.OrderStatus.CANCELLED:
            raise ValueError("Order already been cancelled")
        if self.__status != Order.OrderStatus.RESERVED:
            raise ValueError("Confirmed Already")
        for order_item_index in range(len(self.__order_item_list) - 1, -1, -1):
            order_item = self.__order_item_list[order_item_index]
            if order_item.status == OrderItem.OrderItemStatus.OUT_OF_STOCK or order_item.status == OrderItem.OrderItemStatus.CANCEL:
                del self.__order_item_list[order_item_index]
        self.update_status(Order.OrderStatus.CONFIRMED)
        return self
    
    def order_item_dict_list(self, restaurant: 'Restaurant') -> list:
        dict_list = []
        for e in self.__order_item_list:
            dict_list.append(e.order_item_to_dict(restaurant))
        return dict_list
    
    def order_to_dict(self, restaurant: 'Restaurant') -> dict:
        return {
            "order_id": self.__id,
            "order_type": self.__type,
            "order_status": self.__status,
            "customer": self.__customer.name,
            "order_item_list": self.order_item_dict_list(restaurant),
            "total_price": self.__sub_total_price
        }
    

class Restaurant:
    def __init__(self):
        self.__member_list = []
        self.__order_list = []
        self.__stock = []
        self.__coupon_list = []
        self.__receipt_log = []
        self.__room_list = []
        self.__staff_list = []
        self.__menu = []
        self.__payment_gateway = None
        self.__booking_list = []

    def add_order(self, order: Order):
        self.__order_list.append(order)

    def add_menu(self, menu: MenuItem):
        self.__menu.append(menu)

    @property
    def count_order(self):
        return len(self.__order_list)

    @property
    def check_queue(self):
        count_queue = 0
        for order in self.__order_list:
            if order.status == Order.OrderStatus.PAIDED or order.status == Order.OrderStatus.COOKING:
                count_queue += 1
        return count_queue
    
    def add_stock(self, item: Item, quantity: int):
        for e in range(quantity):
            self.__stock.append(copy.deepcopy(item))

    def get_queue(self, queue_order: int):
        count_queue = 0
        for order in self.__order_list:
            if order.status == Order.OrderStatus.PAIDED or order.status == Order.OrderStatus.COOKING:
                count_queue += 1
            if count_queue == queue_order:
                return order
        return False
    
    def check_stock(self, item_name: str, status: Item.ItemStatus):
        count_stock = 0
        for find in self.__stock:
            if find.name == item_name and find.status == status:
                count_stock += 1
        return count_stock
    
    def get_menu(self):
        menu = []
        for each_menu in self.__menu:
            menu.append(each_menu.to_dict_menu(self))
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
    
    def reserve(self, order: Order): # (ควรแก้เป็น reserve_stock)
        return order.order_reserve(self)
    
    def stock_reserve(self, item_name: str, quantity: int):
        if quantity <= 0:
            raise ValueError("INVALID: Quantity")
        count = 0
        for item in self.__stock:
            if item.name == item_name and item.status == Item.ItemStatus.AVAILABLE:
                item.update_status(Item.ItemStatus.RESERVED)
                count += 1
            if count == quantity:
                return True
        self.stock_reverse(item_name, count)
        return False
        
    def stock_reverse(self, item_name: str, quantity: int):
        if quantity < 0:
            raise ValueError("INVALID: Quantity")
        if self.check_stock(item_name, Item.ItemStatus.RESERVED) < quantity:
            raise ValueError("reverse thing you should not")
        count = 0
        for item_index in range(len(self.__stock) - 1, -1, -1):
            if count == quantity:
                return True
            item = self.__stock[item_index]
            if item.name == item_name and item.status == Item.ItemStatus.RESERVED:
                item.update_status(Item.ItemStatus.AVAILABLE)
                count += 1

    def confirm(self, order:Order): # (ควรแก้เป็น finalize_order)
        try:
            confirmed_order = order.order_confirm()
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return confirmed_order


guest1 = Guest("123", "Anna", "0100000000")
restaurant = Restaurant()
# Mock Order
chicken = Item("Chicken", 30)
bread = Item("Bread", 5)
cheese = Item("Cheese", 20)
restaurant.add_stock(chicken, 20)
restaurant.add_stock(bread, 10)
restaurant.add_stock(cheese, 10)


chicken_recipe = []
chicken_recipe.append(Ingredient(chicken, 1, Ingredient.IngredientType.STRICT))
fried_chicken= SingleMenuItem("Fried Chicken", 20, timedelta(minutes=10), chicken_recipe)
restaurant.add_menu(fried_chicken)

burger_recipe = []
burger_recipe.append(Ingredient(bread, 1, Ingredient.IngredientType.STRICT))
burger_recipe.append(Ingredient(chicken, 1, Ingredient.IngredientType.STRICT))
burger_recipe.append(Ingredient(cheese, 1, Ingredient.IngredientType.CUSTOMIZABLE))
burger = SingleMenuItem("Hamburger", 60, timedelta(minutes=15), burger_recipe)
restaurant.add_menu(burger)


party_chicken_recipe = []
party_chicken_recipe.append(Food(fried_chicken, 60))
party_chicken= SetMenuItem("Party Set", 1000, party_chicken_recipe)
restaurant.add_menu(party_chicken)

# party_chicken.all_ingredient
# print(restaurant.get_menu())


app = FastAPI()

@app.get("/menu", response_model=dict, tags=["Menu"])
async def get_menu():
    return restaurant.get_menu()
    
@app.post("/order/general/guest/start", response_model=str, tags=["Ordering"])
async def start_order(guest: Guest.GuestDTO):
    try:
        current_customer = Guest(guest.id, guest.name, guest.phone_number)
        order = Order(str(uuid.uuid4()), Order.OrderType.GENERAL, current_customer)
        restaurant.add_order(order)
        return order.id
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/order/orderitem/add", response_model=Union[Order.OrderDTO, dict], tags=["Ordering"])
async def add_order(orderitem: OrderItem.OrderItemDTO):
    try:
        current_order = restaurant.search_order_from_id(orderitem.order_id)
        menu = restaurant.search_menu_item_from_name(orderitem.menu)
        current_order.add_order_item(menu, orderitem.quantity)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=(str(e)))
    return current_order.order_to_dict(restaurant)

@app.put("/order/ordering/guest", response_model=Union[Order.OrderDTO, dict], tags=["Ordering"]) # (ควรแก้เป็น /reserve_stock)
async def ordering(order_id: str, guest: Guest.GuestDTO): # (ควรแก้เป็น reserve_order_stock)
    if restaurant.check_queue >= 50:
        raise HTTPException(status_code=418, detail="Queue Overload")
    try:
        current_customer = Guest(guest.id, guest.name, guest.phone_number)
        order = restaurant.search_order_from_id(order_id)
        order.check_customer(current_customer)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    reserved_order = restaurant.reserve(order) # (ควรแก้เป็น reserve_stock)
    reserved_order.update_price
    return reserved_order.order_to_dict(restaurant)

@app.put("/order/confirm/guest", response_model=Union[Order.OrderDTO, dict], tags=["Ordering"]) # (ควรแก้เป็น /finalize)
async def confirm_order(order_id: str, guest: Guest.GuestDTO): # (ควรแก้เป็น finalize_order)
    try:
        current_customer = Guest(guest.id, guest.name, guest.phone_number)
        order = restaurant.search_order_from_id(order_id)
        order.check_customer(current_customer)
        confirmed_order = restaurant.confirm(order) # (ควรแก้เป็น finalize_order)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return confirmed_order.order_to_dict(restaurant)

@app.get("/stock/check/{item_name}", tags=["Stock"])
async def get_stock(item_name: str):
    item_available = restaurant.check_stock(item_name, Item.ItemStatus.AVAILABLE)
    item_reserved = restaurant.check_stock(item_name, Item.ItemStatus.RESERVED)
    return {
        "Available": item_available,
        "Reserved": item_reserved
    }

@app.get("/restaurant/queue/check", tags=["Queue"])
async def check_queue():
    return { "Queue": restaurant.check_queue}

@app.get("/restaurant/queue/get/{queue_order}", response_model=Union[Order.OrderDTO, dict], tags=["Queue"])
async def get_queue(queue_order: int):
    if queue_order > 50 or queue_order < 1:
        raise HTTPException(status_code=400, detail="Queue not Found")
    order = restaurant.get_queue()
    if order == False:
        raise HTTPException(status_code=400, detail="Queue not Found")
    return order.order_to_dict(restaurant)

if __name__ == "__main__":
    uvicorn.run("main:app",host="127.0.0.1",port=8000,reload=True)
