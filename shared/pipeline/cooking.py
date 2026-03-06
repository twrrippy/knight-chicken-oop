import uuid
import uvicorn
from pydantic import BaseModel
from typing import Optional, List, Union
from fastapi import FastAPI, HTTPException
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from enum import Enum
  
app = FastAPI()    
class OrderType(Enum):
    GENERAL = "General"
    DELIVERY = "Delivery"
    EVENT = "Event"
    
class OrderStatus(Enum):
    PENDING = "Pending"
    RESERVED = "Reserved"
    CONFIRMED = "Confirmed"
    PAIDED = "Paided"
    COOKING = "Cooking"
    READY = "Ready"      
    SERVED = "Served"
    CANCELED = "Canceled"
    
class OrderItemStatus(Enum):
    PENDING = "Pending"
    ADDED = "Added to Order"
    RESERVED = "Reserved"
    OUT_OF_STOCK = "Out of Stock"
    COOKING = "Cooking"
    READY = "Ready"
    CANCEL = "Cancel"

class MenuItemStatus(Enum):
    AVAILABLE = "Available"
    UNAVAILABLE = "Unavailable"
class ItemStatus(Enum):
    AVAILABLE = "Available"
    RESERVED = "Reserved"
class IngredientType(Enum):
    STRICT = "Strict"
    CUSTOMIZABLE = "Customizable"
    
class User(ABC):
    def __init__(self, id: str, name: str, phone_number: str):
        self._id = id
        self._name = name
        self._phone_number = phone_number

    @property
    def name(self):
        return self._name

class Customer(User):
        pass

class Guest(Customer):
    class GuestDTO(BaseModel):
        id: str
        name: str
        phone_number: str
class Staff(User):
    pass

class Item():
    def __init__(self, name : str, price : float):
        self.__name = name
        self.__price = price
            
    @property
    def name(self):
        return self.__name
    
    @property
    def price(self):
        return self.__price
    
class Ingredient:
    def __init__(self, item : Item, quantity : int,  type: IngredientType): 
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
    
    @property
    def custom_add(self):
        if self.__type == IngredientType.CUSTOMIZABLE:
            self.__quantity += 1
        else:
            raise TypeError("CAN NOT Custom this Item.")

    @property   
    def custom_sub(self):
        if self.__type == IngredientType.CUSTOMIZABLE:
            if not self.is_valid_quantity(self.__quantity - 1):
                raise ValueError("INVALID: Quantity")
            else:
                self.__quantity -= 1
        else:
            raise TypeError("CAN NOT Custom this Item.")
        
class MenuItem(ABC):
    def __init__(self,name:str, price: float, cooking_time: timedelta ):
        self.__name = name
        self.__price = price
        self.__cooking_time = cooking_time
        self.__menu_item_status = MenuItemStatus.AVAILABLE

    @property    
    def name(self):
        return self.__name
    
    @property
    def price(self):
        return self.__price
    
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

class SetMenuItem(MenuItem):
    def __init__(self, name, price, cooking_time, items: list):
        super().__init__(name, price, cooking_time)
        self.__items = items
        
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
    
class OrderItem:
    class OrderItemDTO(BaseModel):
        order_id: str
        menu_name: str
        quantity: int
    
    def __init__(self, item_id: int, menu_item: MenuItem, quantity: int):
        self.__id = item_id
        self.__menu_item = menu_item
        self.__quantity = quantity
        self.__status = OrderItemStatus.PENDING

    @property
    def id(self):
        return self.__id

    @property
    def status(self):
        return self.__status
    
    @property
    def menu_item(self):
        return self.__menu_item
    
    @property
    def quantity(self):
        return self.__quantity
    
    @property
    def subtotal(self):
        return self.__menu_item.price * self.__quantity

    def update_status(self, status: OrderItemStatus):
        self.__status = status

    def reserve(self, restaurant: 'Restaurant'):
        ingredients = self.__menu_item.get_all_ingredient()
        for ingredient in ingredients:
            if restaurant.find_ingredient_in_stock(ingredient.item.name) < (ingredient.quantity * self.__quantity):
                self.update_status(OrderItemStatus.CANCEL)
                return False
            
        for ingredient in ingredients:
            restaurant.reserve_ingredient(ingredient.item.name, ingredient.quantity * self.__quantity)
            
        self.update_status(OrderItemStatus.RESERVED)
        return True

    def process_cooking(self, restaurant: 'Restaurant'):
        if self.__status != OrderItemStatus.RESERVED:
             return False
        
        self.update_status(OrderItemStatus.COOKING)
        ingredients = self.__menu_item.get_all_ingredient()
        
        for ingredient in ingredients:
            restaurant.consume_reserved_ingredient(ingredient.item.name, ingredient.quantity * self.__quantity)
            
        self.update_status(OrderItemStatus.FINISHED)
        return True

    def cancel_reservation(self, restaurant: 'Restaurant'):
        if self.__status == OrderItemStatus.RESERVED:
            ingredients = self.__menu_item.get_all_ingredient()
            for ingredient in ingredients:
                restaurant.reverse_reserve_ingredient(ingredient.item.name, ingredient.quantity * self.__quantity)
            self.update_status(OrderItemStatus.CANCEL)

class Order:
    
    class OrderDTO(BaseModel):
        order_id: str
        order_type: str
        order_status: str
        customer: str
        food_list: list
        total_price: float
    
    def __init__(self, order_id: str, order_type: OrderType, customer: Customer):
        self.__id = order_id
        self.__type = order_type
        self.__customer = customer
        self.__order_list: List[OrderItem] = []
        self.__status = OrderStatus.NONE
        self.__item_id_counter = 1

    @property
    def id(self):
        return self.__id
    
    @property
    def status(self):
        return self.__status

    @property
    def items(self):
        return self.__order_list

    def update_status(self, status: OrderStatus):
        self.__status = status

    def add_order_item(self, menu_item: MenuItem, quantity: int):
        item = OrderItem(self.__item_id_counter, menu_item, quantity)
        self.__order_list.append(item)
        self.__item_id_counter += 1

    def confirm_and_reserve(self, restaurant: 'Restaurant'):
        reserved_items = []
        for item in self.__order_list:
            if item.status == OrderItemStatus.PENDING:
                if item.reserve(restaurant):
                    reserved_items.append(item)
                else:
                    for reserved_item in reserved_items:
                        reserved_item.cancel_reservation(restaurant)
                    self.update_status(OrderStatus.CANCELED)
                    return False        
        self.update_status(OrderStatus.RESERVED)
        return True

    def cook_order(self, restaurant: 'Restaurant'):
        if self.__status not in [OrderStatus.RESERVED, OrderStatus.PAIDED]:
            return False
            
        self.update_status(OrderStatus.COOKING)
        all_done = True
        for item in self.__order_list:
            if item.status == OrderItemStatus.RESERVED:
                if not item.process_cooking(restaurant):
                    all_done = False
                
        if all_done:
            self.update_status(OrderStatus.READY)
            return True
        return False
 
class Restaurant:
    def __init__(self):
        self.__member_list = []
        self.__order_list: List[Order] = []
        self.__stock: List[Item] = [] 
        self.__reserved_stock: List[Item] = []
        self.__menu: List[MenuItem] = []
        
    def add_menu(self, menu_item: MenuItem):
        self.__menu.append(menu_item)

    def get_menu_by_name  (self, name: str):
        for menu in self.__menu:
            if menu.name == name:
                return menu
        return None

    def get_all_menu(self):
        return [{"name": m.name, "price": m.price} for m in self.__menu]

    def add_order(self, order: Order):
        self.__order_list.append(order)

    def get_order_by_id(self, order_id: str):
        for order in self.__order_list:
            if order.id == order_id:
                return order
        return None

    def add_stock(self, item: Item, quantity: int):
        for _ in range(quantity):
            self.__stock.append(Item(item.name, item.price))

    def find_ingredient_in_stock(self, item_name: str):
        return sum(1 for item in self.__stock if item.name == item_name)

    def find_item_in_reserved(self, item_name: str):
        return sum(1 for reserved_item in self.__reserved_stock if reserved_item.name == item_name)

    def reserve_ingredient(self, item_name: str, quantity: int):
        if self.find_ingredient_in_stock(item_name) < quantity:
            return False
            
        count = 0
        for i in range(len(self.__stock) - 1, -1, -1):
            if self.__stock[i].name == item_name:
                self.__reserved_stock.append(self.__stock.pop(i))
                count += 1
                if count == quantity:
                    break
        return True

    def consume_reserved_ingredient(self, item_name: str, quantity: int):
        if self.find_item_in_reserved(item_name) < quantity:
            return False

        count = 0
        for i in range(len(self.__reserved_stock) - 1, -1, -1):
            if self.__reserved_stock[i].name == item_name:
                self.__reserved_stock.pop(i)
                count += 1
                if count == quantity:
                    break
        return True

    def reverse_reserve_ingredient(self, item_name: str, quantity: int):
        count = 0
        for i in range(len(self.__reserved_stock) - 1, -1, -1):
            if self.__reserved_stock[i].name == item_name:
                self.__stock.append(self.__reserved_stock.pop(i)) 
                count += 1
                if count == quantity:
                    break

guest1 = Guest("123", "Anna", "0100000000")           
restaurant = Restaurant()

# -- Setup Mock Data --
chicken = Item("Chicken", 30)
bread = Item("Bread", 10)
cheese = Item("Cheese", 20)

restaurant.add_stock(chicken, 50)
restaurant.add_stock(bread, 20)
restaurant.add_stock(cheese, 20)

chicken_recipe = [Ingredient(chicken, 1, IngredientType.STRICT)]
fried_chicken = SingleMenuItem("Fried Chicken", 50, timedelta(minutes=10), chicken_recipe)

burger_recipe = [
    Ingredient(bread, 1, IngredientType.STRICT), 
    Ingredient(chicken, 1, IngredientType.STRICT),
    Ingredient(cheese, 1, IngredientType.CUSTOMIZABLE)
]
burger = SingleMenuItem("Cheeseburger", 120, timedelta(minutes=15), burger_recipe)

party_set = SetMenuItem("Party Set", 1000, timedelta(minutes=30), [Food(fried_chicken, 10), Food(burger, 2)])

restaurant.add_menu(fried_chicken)
restaurant.add_menu(burger)
restaurant.add_menu(party_set)

@app.get("/menu")
async def get_menu():
    return {"menu": restaurant.get_all_menu()}

@app.get("/stock")
async def get_stock():
    return {
        "Chicken": {"Real": restaurant.find_ingredient_in_stock("Chicken"), "Reserved": restaurant.find_item_in_reserved("Chicken")},
        "Bread": {"Real": restaurant.find_ingredient_in_stock("Bread"), "Reserved": restaurant.find_item_in_reserved("Bread")},
        "Cheese": {"Real": restaurant.find_ingredient_in_stock("Cheese"), "Reserved": restaurant.find_item_in_reserved("Cheese")}
    }

@app.post("/order/start")
async def start_order(guest: Guest.GuestDTO):
    current_customer = Guest(guest.id, guest.name, guest.phone_number)
    order_id = f"ORD-{uuid.uuid4().hex[:6].upper()}"
    new_order = Order(order_id, OrderType.GENERAL, current_customer)
    restaurant.add_order(new_order)
    return {"order_id": new_order.id, "status": new_order.status.value}

@app.put("/order/add_item")
async def add_order_item(dto: OrderItem.OrderItemDTO):
    order = restaurant.get_order_by_id(dto.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    menu = restaurant.get_menu_by_name(dto.menu_name)
    if not menu:
        raise HTTPException(status_code=404, detail="Menu item not found")
        
    order.add_order_item(menu, dto.quantity)
    return {"message": f"Added {dto.quantity} x {dto.menu_name} to {dto.order_id}"}

@app.post("/order/reserve/{order_id}")
async def reserve_order(order_id: str):
    order = restaurant.get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    success = order.confirm_and_reserve(restaurant)
    if success:
        return {"message": "Order reserved successfully", "status": order.status.value}
    else:
        raise HTTPException(status_code=400, detail="Insufficient stock. Reservation failed.")

@app.post("/kitchen/cook/{order_id}")
async def cook_order(order_id: str):
    order = restaurant.get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    success = order.cook_order(restaurant)
    if success:
        return {"message": "Cooking finished. Order is READY.", "status": order.status.value}
    else:
        raise HTTPException(status_code=400, detail=f"Cannot cook order. Current status: {order.status.value}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)