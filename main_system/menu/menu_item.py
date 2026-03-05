from main_system.enum import MenuItemStatus, ItemStatus, IngredientType
from pydantic import BaseModel
from datetime import timedelta
from abc import ABC, abstractmethod
import copy
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main_system.restaurant import restaurant
class Item:
    @staticmethod
    def is_valid_price(price: float):
        return price > 0
    
    def __init__(self, name: str, price: float):
        if not Item.is_valid_price(price):
            raise ValueError("INVALID: Price")
        self.__name = name
        self.__price = price
        self.__status = ItemStatus.AVAILABLE

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
        self.update_price(original_menu)
        return {
            "name": self.__name,
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
