from abc import ABC,abstractmethod
from fastapi import HTTPException
from main_system.enum import CouponStatus

class Customer(ABC):
    pass

class Guest(Customer):
    pass

class Member(Customer):
    pass

class Coupon(ABC):
    def __init__(self, id, code, minimum_price) -> None:
        self.__id = id
        self.__code = code
        self.__minimum_price = minimum_price
        self.__status: CouponStatus = CouponStatus.AVAILABLE

    @property
    def minimum_price(self): return self.__minimum_price
    @property
    def status(self): return self.__status
    @property
    def code(self): return self.__code

    def is_applicable(self, base_price: float) -> bool:
        return base_price >= self.__minimum_price

    @abstractmethod
    def apply_coupon(self, base_price: float) -> float: pass

    def mark_as_used(self):
        self.__status = CouponStatus.NOT_AVAILABLE

class PercentCoupon(Coupon):
    def __init__(self, id, code, minimum_price, percent) -> None:
        super().__init__(id, code, minimum_price)
        if not (0 <= percent <= 100):
            raise ValueError("Percent must be in range 0-100")
        self.__percent = percent

    def apply_coupon(self, base_price: float) -> float:
        if self.is_applicable(base_price):
            return base_price * (self.__percent / 100)
        raise HTTPException(409, f"Does Not Meet Minimum Price {self.minimum_price}")

class FixedAmountCoupon(Coupon):
    def __init__(self, id: str, code: str, minimum_price: float, amount: float) -> None:
        super().__init__(id, code, minimum_price)
        if amount > minimum_price:
            raise ValueError("Minimum Price must be >= Amount")
        self.__amount = amount

    def apply_coupon(self, base_price: float) -> float:
        if self.is_applicable(base_price):
            return self.__amount
        raise HTTPException(409, f"Does Not Meet Minimum Price {self.minimum_price}")
