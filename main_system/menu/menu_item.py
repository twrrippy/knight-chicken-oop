from main_system.enum import MenuItemStatus
class MenuItem:
    def __init__(self, name: str, price: float, status: MenuItemStatus) -> None:
        self.__name = name
        self.__price = price
        self.__status = status
    @property
    def name(self): return self.__name
    @property
    def price(self): return self.__price
    @property
    def status(self): return self.__status