from abc import ABC, abstractmethod
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