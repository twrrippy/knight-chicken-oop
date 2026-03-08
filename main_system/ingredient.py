from main_system.enum import ItemStatus, IngredientType
from pydantic import BaseModel
from datetime import timedelta
from abc import ABC, abstractmethod
import copy
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
    
    @status.setter
    def status(self, status: ItemStatus): self.__status = status
    
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

    def custom(self, quantity: int):
        if self.__type == IngredientType.CUSTOMIZABLE:
            self.modify(quantity)
        else:
            raise TypeError("CAN NOT Custom this Item.")
        
    @property
    def ingredient_to_dict(self):
        return {
            "name": self.__item.name,
            "quantity": self.__quantity
        }
        
