from abc import ABC, abstractmethod
from fastapi import HTTPException
from typing import TYPE_CHECKING, List
from main_system.enum import CouponStatus, MemberTier

if TYPE_CHECKING:
    # บรรทัดนี้จะทำงานเฉพาะตอน VSCode ตรวจโค้ด (Intellisense) 
    # แต่ตอนรันจริง Python จะข้ามไปเลย ทำให้ไม่เกิด Circular Import
    from main_system.log.receipt import Receipt

class Customer(ABC):
    def __init__(self, id: str, name: str, phone: str = ""):
        self.__id = id
        self.__name = name
        self.__phone = phone

    @property
    def id(self):
        return self.__id

    @property
    def name(self):
        return self.__name

    @property
    def phone(self):
        return self.__phone

class Guest(Customer):
    pass

class Member(Customer):
    def __init__(self, id: str, name: str, tier: MemberTier, username: str, password: str, phone: str = ""):
        super().__init__(id, name, phone)
        self.__coupon_list: List[Coupon] = [] 
        self.__receipt_list: List['Receipt'] = []
        self.__tier: MemberTier = tier
        self.__points: int = 0
        self.__username = username
        self.__password = password

    def add_receipt(self, receipt: 'Receipt'): self.__receipt_list.append(receipt)
    def add_coupon(self, coupon: 'Coupon'): self.__coupon_list.append(coupon)
    
    def get_coupon_by_code(self, code: str):
        for coupon in self.__coupon_list:
            if coupon.code == code: return coupon
        raise HTTPException(404, "Coupon Not Found")

    def get_member_discount(self, base_price: float):
        match self.tier:
            case MemberTier.GENERAL: return 0.0
            case MemberTier.BRONZE: return base_price * 0.05
            case MemberTier.SILVER: return base_price * 0.10
            case MemberTier.GOLD: return base_price * 0.15
        return 0.0

    @property
    def tier(self) -> MemberTier: return self.__tier
    @property
    def username(self): return self.__username
    @property
    def password(self): return self.__password

    def check_username(self, username: str) -> bool:
        return hasattr(self, "_username") and self.__username == username

    def check_password(self, password: str) -> bool:
        return hasattr(self, "_password") and self.__password == password

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
