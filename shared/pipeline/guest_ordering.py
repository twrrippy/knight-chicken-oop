import uuid
import uvicorn
from typing import Union
from fastapi import FastAPI, HTTPException
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pydantic import BaseModel

class User(ABC):
    def __init__(self, id: str, name: str, phone_number: str):
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
        if not (type(other) is type(self)):
            return False
        return self.__name == other.name and self.__id == other.id and self.__phone_number == other.phone_number
    
    def check(self, other):
        return self.__eq__(other)
    
class Staff(User):
    pass

class Customer(User):
    pass

class Guest(Customer):
    class GuestDTO(BaseModel):
        id: str
        name: str
        phone_number: str

class Item():
    def __init__(self, name: str, price: float):
        self.__name = name
        self.__price = price

    class ItemDTO(BaseModel):
        name: str
        price: float

    @property
    def name(self):
        return self.__name
    
    @property
    def price(self):
        return self.__price

class Ingredient():
    def __init__(self, item: Item, quantity: int):
        self.__item = item
        self.__quantity = quantity

    @property
    def item(self):
        return self.__item
    @property
    def quantity(self):
        return self.__quantity

class Particular(ABC):
    def __init__(self,name: str, recipe: list, price: float, cooking_time: datetime):
        self.__name = name
        self._recipe = recipe
        self.__price = price
        self.__cooking_time = cooking_time

    @property
    def name(self):
        return self.__name
    
    @property
    def price(self):
        return self.__price
    
    @abstractmethod
    def all_ingredient(self):
        pass

    @property
    def to_dict(self):
        return {
            "name": self.__name,
            "price": self.__price
        }

class ChickenSet(Particular):

    def all_ingredient(self):
        return self._recipe
    
class Burger(Particular):
    def __init__(self,name: str, recipe: list, add_on: list, price: float, cooking_time: datetime):
        add_on_price = 0
        for ingredient in add_on:
            add_on_price += ingredient.quantity * ingredient.item.price
        super().__init__(name, recipe, price + add_on_price , cooking_time)
        self.__add_on = add_on
        
    def all_ingredient(self):
        return self._recipe + self.__add_on

class Food():
    def __init__(self, particular: Particular, quantity: int):
        self.__particular = particular
        self.__quantity = quantity
        self.__status = None
    
    @property
    def price(self):
        return self.__quantity * self.__particular.price
    @property
    def status(self):
        return self.__status
    
    def update_status(self, food_status: str):
        self.__status = food_status

    def reserve(self, stock):
        all_ingredient_in_particular = self.__particular.all_ingredient()
        for ingredient in all_ingredient_in_particular:
            if not stock.reserve(ingredient.item, ingredient.quantity * self.__quantity):
                self.reverse(stock, all_ingredient_in_particular, ingredient)
                self.update_status("Out of Stock")
                break
        else:
            self.update_status("Available")
        return self
    def reverse(self, stock, all_ingredient_in_particular, ingredient):       
        for deleting_ingredient in all_ingredient_in_particular:
            if deleting_ingredient == ingredient:
                break
            else:
                stock.reverse(deleting_ingredient.item, deleting_ingredient.quantity * self.__quantity)
    
    @property
    def to_dict(self):
        return {
            "particular": self.__particular.to_dict,
            "quantity": self.__quantity,
            "status": self.__status
        }

class Order():
    def __init__(self, id: str, type: str, customer: Customer):
        self.__id = id
        self.__type = type
        self.__customer = customer
        self.__food_list = []
        self.__total_price = 0
        self.__status_start = datetime.now()
        self.__status = None

    class OrderDTO(BaseModel):
        order_id: str
        order_type: str
        customer: str
        food_list: list
        total_price: float
    class FoodDTO(BaseModel):
        order_id: str
        particular: dict
        quantity: int

    @property
    def status(self):
        return self.__status
    @property
    def id(self):
        return self.__id
    
    @property
    def update_price(self):
        count_price = 0
        for food in self.__food_list:
            if food.status != "Out of Stock" and food.status != "Cancle":
                count_price += food.price
        self.__total_price = count_price
    
    def update_status(self, order_status: str):
        self.__status = order_status

    def check_customer(self, customer: Customer):
        return self.__customer.check(customer)
    
    def add_food(self, food: Food):
        self.__food_list.append(food)
        food.update_status("Add to Order")

    def reserve(self, stock):
        for food in self.__food_list:
            food.reserve(stock)
        self.update_status("Reserved")
        return self
    
    @property
    def to_dict(self) -> dict:
        return {
            "order_id": self.__id,
            "order_type": self.__type,
            "customer": self.__customer.name,
            "food_list": self.food_dict_list,
            "total_price": self.__total_price
        }
    
    @property
    def food_dict_list(self) -> list:
        dict_list = []
        for e in self.__food_list:
            dict_list.append(e.to_dict)
        return dict_list
    
class DineInOrder(Order):
    def __init__(self, id: str, customer: Customer):
        super().__init__(id, "DineIn", customer)

class MenuFood():
    def __init__(self, particular: Particular):
        self.__particular = particular
        self.__status = "Available"
    
    def update_status(self, menu_food_status: str):
        self.__status = menu_food_status

class Stock():
    def __init__(self):
        self.__reserved_stock = []
        self.__real_stock = []
    
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
        for e in range(quantity):
            self.__real_stock.append(item)

    def reserve(self, item: Item, quantity: int):
        count = quantity
        for item_index in range(len(self.__real_stock) - 1, -1, -1):
            if self.__real_stock[item_index] == item:
                self.__reserved_stock.append(self.__real_stock[item_index])
                del self.__real_stock[item_index]
                count-=1
            if count == 0:
                return True
        else:
            stock.reverse(item, quantity - count)
            return False
            
    def reverse(self, item: Item, quantity: int):
        if self.check_reserved_stock(item) < quantity:
            raise ValueError("reverse thing you should not")
        count = quantity
        for item_index in range(len(self.__reserved_stock) - 1, -1, -1):
            if count == 0:
                return True
            if self.__reserved_stock[item_index] == item:
                self.__real_stock.append(self.__reserved_stock[item_index])
                del self.__reserved_stock[item_index]
                count -= 1

        

class StockLog():
    def __init__(self, id: str, action :str, ingredient: Ingredient, staff: Union[Staff, None]):
        self.__id = id
        self.__action = action
        self.__ingredient = Ingredient
        if staff == None:
            self.__staff = "System"
        else:
            self.__staff = staff

class Restaurant():
    def __init__(self, stock: Stock):
        self.__member_list = []
        self.__order_list = []
        self.__coupon_list = []
        self.__stock_log = []
        self.__transaction_log = []
        self.__room_list = []
        self.__staff_list = []
        self.__stock = stock
        self.__menu = []
        self.__payment_gateway = None
        self.__delivery_platform = None

    def add_order(self, order: Order):
        self.__order_list.append(order)

    def add_stock_log(self, new_log: StockLog):
        self.__stock_log.append(new_log)

    @property
    def count_order(self):
        return len(self.__order_list)

    @property
    def check_queue(self):
        count_queue = 0
        for order in self.__order_list:
            if order.status == "Paided" or order.status == "Cooking":
                count_queue += 1
            if count_queue >= 50:
                return False
        return True
    
    @property
    def get_menu(self):
        return self.__menu
    
    def search_order_from_id(self, order_id: str, customer: Customer) -> Order:
        for find in self.__order_list:
            if find.id == order_id:
                if find.check_customer(customer):
                    return find
                else:
                    raise ValueError("Wrong Customer")
        raise ValueError("Order not found")

    def reserve(self, order: Order, stock: Stock) -> Order:
        return order.reserve(stock)


# def ordering(order_id: str,customer: Customer):
#     if not restaurant.check_queue:
#         print("oo")
#         return
#     order = restaurant.search_order_from_id(order_id,customer)
#     reserved_order = restaurant.reserve(order, stock)
#     order.update_price
#     print(reserved_order.to_dict)

guest1 = Guest("123", "Anna", "0100000000")
stock = Stock()
restaurant = Restaurant(stock)
# Mock Order
chicken = Item("Chicken", 30)
bread = Item("Bread", 5)
cheese = Item("Cheese", 20)
stock.add_stock(chicken, 20)
stock.add_stock(bread, 10)
stock.add_stock(cheese, 10)


chicken_recipe = []
chicken_recipe.append(Ingredient(chicken, 1))
fried_chicken= ChickenSet("Fried Chicken", chicken_recipe, 20, timedelta(minutes=10))

burger_recipe = []
burger_recipe.append(Ingredient(bread, 1))
burger_recipe.append(Ingredient(chicken, 1))
burger_add_on = []
burger_add_on.append(Ingredient(cheese, 1))
burger = Burger("Hamburger", burger_recipe, burger_add_on, 60, timedelta(minutes=15))

burger2_recipe = []
burger2_recipe.append(Ingredient(bread, 1))
burger2_recipe.append(Ingredient(chicken, 1))
burger2_add_on = []
burger2 = Burger("Hamburger", burger2_recipe, burger2_add_on, 60, timedelta(minutes=15))

party_chicken_recipe = []
party_chicken_recipe.append(Ingredient(bread, 1))
party_chicken_recipe.append(Ingredient(chicken, 30))
party_chicken= ChickenSet("Party Set", party_chicken_recipe, 1000, timedelta(minutes=30))

# Case 101
order1 = DineInOrder("101", guest1)
order1.add_food(Food(fried_chicken, 2))
restaurant.add_order(order1)

# Case 102
order2 = DineInOrder("102", guest1)
order2.add_food(Food(burger, 2))
order2.add_food(Food(burger2, 2))
restaurant.add_order(order2)

# Case 103
order3 = DineInOrder("103", guest1)
order3.add_food(Food(fried_chicken, 2))
order3.add_food(Food(party_chicken, 1))
restaurant.add_order(order3)

# also_guest1 = Guest("123", "Anna", "0100000000")
# ordering("101", also_guest1)
# ordering("102", also_guest1)
# ordering("103", also_guest1)

app = FastAPI()
# @app.get("/menu")
# def get_menu():
    
@app.post("/order/dinein/guest/start")
async def start_order(guest: Guest.GuestDTO):
    current_customer = Guest(guest.id, guest.name, guest.phone_number)
    order = Order(str(uuid.uuid4()), "Dine In", current_customer)
    restaurant.add_order(order)
    return order.id

@app.post("order/food/add", response_model=Union[Order.OrderDTO, dict])
async def add_order(food: Order.FoodDTO): #รับแยก order id กับ food ไปเขียน dto ดีๆซะ
    new_food = Food(food.particular, food.quantity)
    try:
        order = restaurant.search_order_from_id(food.order_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    order.add_food(new_food)
    return order.to_dict

@app.put("/ordering/guest", response_model=Union[Order.OrderDTO, dict])
async def ordering(order_id: str, guest: Guest.GuestDTO):
    if not restaurant.check_queue:
        raise HTTPException(status_code=418, detail="Queue Overload")
    try:
        current_customer = Guest(guest.id, guest.name, guest.phone_number)
        order = restaurant.search_order_from_id(order_id, current_customer)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    reserved_order = restaurant.reserve(order, stock)
    order.update_price
    return reserved_order.to_dict

@app.get("/stock/{item_name}")
async def get_stock(item_name: str):
    item_in_real_stock = stock.check_real_by_name(item_name)
    item_in_reserved_stock = stock.check_reserved_by_name(item_name)
    return {
        "Real Stock": item_in_real_stock,
        "Reserved Stock": item_in_reserved_stock
    }

if __name__ == "__main__":
    uvicorn.run("main:app",host="127.0.0.1",port=8000,reload=True)

