from abc import ABC, abstractmethod
from fastapi import HTTPException
from main_system.utils.enum import CouponStatus

class Coupon(ABC):
    def __init__(self, id, code, minimum_price, max_usage: int = 1) -> None:
        self.__id = id
        self.__code = code
        self.__minimum_price = minimum_price
        self.__status: CouponStatus = CouponStatus.AVAILABLE
        self.__max_usage = max_usage
        self.__used_count = 0

    @property
    def minimum_price(self): return self.__minimum_price
    @property
    def status(self): return self.__status
    @property
    def code(self): return self.__code
    @property
    def max_usage(self): return self.__max_usage
    @property
    def used_count(self): return self.__used_count

    def is_applicable(self, base_price: float) -> bool:
        return base_price >= self.__minimum_price

    @abstractmethod
    def apply_coupon(self, base_price: float) -> float: pass

    def is_available(self) -> bool:
        return self.__status == CouponStatus.AVAILABLE and self.__used_count < self.__max_usage

    def consume(self):
        if self.is_available():
            self.__used_count += 1
            if self.__used_count >= self.__max_usage:
                self.__status = CouponStatus.NOT_AVAILABLE
        else:
            raise ValueError("Coupon is not available or fully used")

class PercentCoupon(Coupon):
    def __init__(self, id, code, minimum_price, percent, max_usage: int = 1) -> None:
        super().__init__(id, code, minimum_price, max_usage)
        if not (0 <= percent <= 100):
            raise ValueError("Percent must be in range 0-100")
        self.__percent = percent

    def apply_coupon(self, base_price: float) -> float:
        if self.is_applicable(base_price):
            return base_price * (self.__percent / 100)
        raise HTTPException(409, f"Does Not Meet Minimum Price {self.minimum_price}")

class FixedAmountCoupon(Coupon):
    def __init__(self, id: str, code: str, minimum_price: float, amount: float, max_usage: int = 1) -> None:
        super().__init__(id, code, minimum_price, max_usage)
        if amount > minimum_price:
            raise ValueError("Minimum Price must be >= Amount")
        self.__amount = amount

    def apply_coupon(self, base_price: float) -> float:
        if self.is_applicable(base_price):
            return self.__amount
        raise HTTPException(409, f"Does Not Meet Minimum Price {self.minimum_price}")
