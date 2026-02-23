import uuid
import uvicorn
from pydantic import BaseModel
from typing import Optional, List, Union
from fastapi import FastAPI, HTTPException
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from enum import Enum
  
app = FastAPI()

class Status(Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    
class OrderType(Enum):
    GENERAL = "General"
    DELIVERY = "Delivery"
    EVENT = "Event"
    
class OrderStatus(Enum):
    PENDING = "Pending"
    PLACED = "Placed"
    PAID = "Paid"
    COOKING = "Cooking"
    READY_TO_PICKUP = "Ready"      
    COMPLETED = "Completed"
    CANCELED = "Canceled"
    FAILED_RESERVATION = "Failed Reservation"

class FoodStatus(Enum):
    INITIALIZED = "Initialized"
    OUT_OF_STOCK = "Out of Stock"
    RESERVED = "Reserved"
    COOKING = "Cooking"
    FINISHED = "Finished"
    CANCELED = "Canceled"
    
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
    def __init__(self, item : Item, quantity : int):
        self.__item = item
        self.__quantity = quantity
        
    @property   
    def item(self):
        return self.__item
    
    @property   
    def quantity(self):
        return self.__quantity

class Stock:
    def __init__(self):
        self.__real_stock = []
        self.__reserved_stock = []
        
    def check_real_stock(self, item:Item):
        count_stock = 0
        for find in self.__real_stock:
            if find == item:
                count_stock += 1
        return count_stock
    
    def check_reserved_stock(self, item:Item):
        count_stock = 0
        for find in self.__reserved_stock:
            if find == item:
                count_stock += 1
        return count_stock
    
    def check_real_by_name(self, item_name: str):
        count_stock = 0
        for find in self.__real_stock:
            if find.name == item_name:
                count_stock += 1
        return count_stock
    
    def check_reserved_by_name(self, item_name: str):
        count_stock = 0
        for find in self.__reserved_stock:
            if find.name == item_name:
                count_stock += 1
        return count_stock
        
    def add_stock(self, item: Item, quantity: int):
        for i in range(quantity):
            self.__real_stock.append(item)
            
    def reserve(self, item: Item, quantity: int):
        if self.check_real_by_name(item.name) < quantity:
            return False
        
        count = quantity
        for i in range(len(self.__real_stock) - 1, -1, -1):
            if self.__real_stock[i].name == item.name:
                self.__reserved_stock.append(self.__real_stock[i])
                del self.__real_stock[i]
                count -= 1
            if count == 0:
                return True
        return False
    
    def consume_reserved(self, item: Item, quantity: int):
        if self.check_reserved_by_name(item.name) < quantity:
            return False

        count = quantity
        for i in range(len(self.__reserved_stock) - 1, -1, -1):
            if self.__reserved_stock[i].name == item.name:
                del self.__reserved_stock[i] # ลบทิ้ง (ใช้ปรุงอาหารไปแล้ว)
                count -= 1
            if count == 0:
                return True
        return False
    
    def cancel_reserved(self, item: Item, quantity: int):
        if self.check_reserved_by_name(item.name) < quantity:
            return False

        count = quantity
        for i in range(len(self.__reserved_stock) - 1, -1, -1):
            if self.__reserved_stock[i].name == item.name:
                self.__real_stock.append(self.__reserved_stock[i])
                del self.__reserved_stock[i]
                count -= 1
            if count == 0:
                return True
        return False
    
    def get_status(self):
        summary = {}
        all_items = set([i.name for i in self.__real_stock] + [i.name for i in self.__reserved_stock])
        for name in all_items:
            summary[name] = {
                "Real": self.check_real_by_name(name),
                "Reserved": self.check_reserved_by_name(name)
            }
        return summary
    
class Particular(ABC):
    def __init__(self, name: str, price: float):
        self.__name = name
        self.__price = price

    @property
    def name(self):
        return self.__name
    
    @property
    def price(self):
        return self.__price
    
    @abstractmethod
    def all_ingredient(self):
        pass
    
class ChickenSet(Particular):
    def __init__(self, name: str, recipe: list, price: float):
        super().__init__(name, price)
        self._recipe = recipe

    def all_ingredient(self):
        return self._recipe
    
class Burger(Particular):
    def __init__(self, name: str, recipe: list, price: float, cooking_time: datetime = None, add_on: Union[list, None] = None):
        add_on_price = self.__calculate_add_on_price(add_on)
        super().__init__(name, price + add_on_price) 
        self._recipe = recipe
        self.__add_on = add_on if add_on else []
        self.__cooking_time = cooking_time

    def __calculate_add_on_price(self, add_on: list):
        add_on_price = 0
        if add_on:
            for ingredient in add_on:
                add_on_price += ingredient.quantity * ingredient.item.price
        return add_on_price
        
    def all_ingredient(self):
        return self._recipe + self.__add_on
    
class Food:
    def __init__(self, particular: Particular, quantity: int):
        self.__particular = particular
        self.__quantity = quantity
        self.__status = FoodStatus.INITIALIZED
        
    @property
    def status(self):
        return self.__status
    
    def update_status(self, status: str):
        self.__status = status

    def reserve(self, stock: Stock):
        ingredients = self.__particular.all_ingredient()
    
        for i in ingredients:
            if stock.check_real_by_name(i.item.name) < (i.quantity * self.__quantity):
                self.update_status(FoodStatus.OUT_OF_STOCK)
                return False
        

        for i in ingredients:
            stock.reserve(i.item, i.quantity * self.__quantity)
        
        self.update_status(FoodStatus.RESERVED)
        return True

    def process_cooking(self, stock: Stock):
        if self.__status != FoodStatus.RESERVED:
             return False
        self.update_status(FoodStatus.COOKING)
        ingredients = self.__particular.all_ingredient()
  
        for i in ingredients:
            qty_needed = i.quantity * self.__quantity
            if stock.check_reserved_by_name(i.item.name) < qty_needed:
                return False

        for i in ingredients:
            stock.consume_reserved(i.item, i.quantity * self.__quantity)
            
        self.update_status(FoodStatus.FINISHED)
        return True
    
    def cancel_reservation(self, stock: Stock):
        if self.__status != FoodStatus.RESERVED:
             return False
        
        ingredients = self.__particular.all_ingredient()
        for i in ingredients:
            stock.cancel_reserved(i.item, i.quantity * self.__quantity)
        
        self.update_status(FoodStatus.CANCELED)
        return True
    
class Order:
    def __init__(self, order_id: str):
        self.__id = order_id
        self.__food_list = []
        self.__status = OrderStatus.PENDING

    @property
    def id(self):
        return self.__id
    
    @property
    def status(self):
        return self.__status

    def add_food(self, food: Food):
        self.__food_list.append(food)

    def confirm_and_reserve(self, stock: Stock):
        reserved_foods = []
        for food in self.__food_list:
            if food.reserve(stock):
                reserved_foods.append(food)
            else:
                for error_food in reserved_foods:
                    error_food.cancel_reservation(stock)
                
                self.__status = OrderStatus.FAILED_RESERVATION
                return False        
        self.__status = OrderStatus.PLACED
        return True

    def start_cooking(self, stock: Stock):
        if self.__status not in [OrderStatus.PLACED, OrderStatus.PAID]:
            return False
        self.__status = OrderStatus.COOKING
        all_done = True
        for food in self.__food_list:
            result = food.process_cooking(stock)
            if not result:
                all_done = False
        
        if all_done:
            self.__status = OrderStatus.READY_TO_PICKUP
            return True
        return False
    
    def cancel_order(self, stock: Stock):
        if self.__status not in [OrderStatus.PLACED, OrderStatus.PAID]:
            return False
        
        for food in self.__food_list:
            if food.status == FoodStatus.RESERVED:
                food.cancel_reservation(stock)  
        
        self.__status = OrderStatus.CANCLED
        return True

class Restaurant:
    def __init__(self, stock: Stock):
        self.__order_list = []
        self.__stock = stock

    def add_order(self, order: Order):
        self.__order_list.append(order)

    def _get_order_id(self, order_id: str):
        for order in self.__order_list:
            if order.id == order_id:
                return order
        return None

    def cooking_order(self, order_id: str):
        target_order = self._get_order_id(order_id)
        if target_order is None:
            return {"status": Status.FAILED, "message": "Order Not Found"}
        success = target_order.start_cooking(self.__stock)
        if success:
            return {"status": Status.SUCCESS, "message": "Cooking Process Complete"}
        else:
            return {"status": Status.FAILED, "message": f"Cooking Failed (Order status is {target_order.status.value})"}
 
class KitchenStaff:
    def __init__(self, name:str,work:Restaurant):
        self.__name = name
        self.__work = work
        
    @property   
    def name(self):
        return self.__name
    
    @property
    def work(self):
        return self.__work

    def cooking_order(self, order_id:str):
        return self.__work.cooking_order(order_id)


# Mock Order
stock = Stock()
restaurant = Restaurant(stock)
chef = KitchenStaff("Chef Chompoo", restaurant)

chicken = Item("Chicken", 30)
bread   = Item("Bread", 10)
cheese  = Item("Cheese", 20)

stock.add_stock(chicken, 50)
stock.add_stock(bread, 20)
stock.add_stock(cheese, 20)

menu_chicken = ChickenSet("Fried Chicken", [Ingredient(chicken, 1)], 50)

menu_burger = Burger("Cheeseburger", 
    recipe=[Ingredient(bread, 1), Ingredient(chicken, 1)], 
    price=120,
    cooking_time=datetime.now(),
    add_on=[Ingredient(cheese, 1)]
)

menu_party = ChickenSet("Party Set", [Ingredient(chicken, 30)], 1000)

order1 = Order("ORD-101")
order1.add_food(Food(menu_chicken, 2))
order1.confirm_and_reserve(stock)
restaurant.add_order(order1)

order2 = Order("ORD-102")
order2.add_food(Food(menu_burger, 2))
order2.confirm_and_reserve(stock)
restaurant.add_order(order2)

order3 = Order("ORD-103")
order3.add_food(Food(menu_burger, 1))
restaurant.add_order(order3)

order4 = Order("ORD-104")
order4.add_food(Food(menu_party, 5))
order4.confirm_and_reserve(stock)
restaurant.add_order(order4)

@app.post("/kitchen/cook")
async def kitchen_cook(order_id: str):
    result = chef.cooking_order(order_id)
    current_stock = stock.get_status()
    if result["status"] == Status.FAILED:
        raise HTTPException(status_code=400, detail={
            "message": result["message"],
            "Stock": current_stock
        })
        
    return {
        "status": result["status"].value,
        "message": result["message"],
        "Stock": current_stock
    }
    
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)