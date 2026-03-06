from main_system.enum import PlatformName, DeliveryStatus
from typing import TYPE_CHECKING, Tuple
from fastapi import HTTPException
import random
from abc import ABC, abstractmethod

if TYPE_CHECKING:
    from main_system.order.order_extention.delivery import Delivery

class DeliveryProvider(ABC):
    def __init__(self, platform_name: PlatformName) -> None:
        self.__platform_name = platform_name
        self._riders_name = []
        self._minimum_fee = 0
        self._price_per_km = 0

    def request_rider(self, delivery: Delivery) -> Tuple[bool, str]:
        if delivery.status != DeliveryStatus.PENDING:
            raise HTTPException(400, "Delivery Already Assigned")

        is_success = True
        rider_name = random.choice(self._riders_name)
        return (is_success, rider_name)

    @abstractmethod
    def calculate_fee(self, distance_km: float) -> float:
        pass
    
    @property
    def platform_name(self): return self.__platform_name

class GrabDeliveryProvider(DeliveryProvider):
    def __init__(self) -> None:
        super().__init__(PlatformName.GRAB)
        self._minimum_fee = 10
        self._price_per_km = 10
        self._riders_name: list[str] = ["สุธนิษฐา จารุตัน", "คมพิชญ์ คำป้อง", "ชูวิทย์ มาตรเหลือง"]
    
    def request_rider(self, delivery: Delivery) -> Tuple[bool, str, str]:
        is_success, rider_name = super().request_rider(delivery)
        tracking_id = f"GRB-{random.randint(1000000, 9999999)}"
        return is_success, rider_name, tracking_id

    def calculate_fee(self, distance_km: float) -> float:
        """
        คำนวณค่าส่งของ Grab:
        - คิดราคาตามระยะทาง (10 บาท/กม.)
        - หากระยะทางเกิน 5 กม. จะบวกค่า Surge เพิ่มอีก 5 บาทต่อกม. ที่เกินมา
        - ราคาขั้นต่ำ 10 บาท
        """
        price = distance_km * self._price_per_km
        if distance_km > 5:
            price += (distance_km - 5) * 5
        return price if price > self._minimum_fee else self._minimum_fee
    
class LineManDeliveryProvider(DeliveryProvider):
    def __init__(self) -> None:
        super().__init__(PlatformName.LINE_MAN)
        self._minimum_fee = 15
        self._price_per_km = 12
        self._riders_name: list[str] = ["ขวัญหล้า บุญวิวัฒนาการ", "สุสกาวรัตน์อัจฉรา ศรีหะจันทร์", "อัศนีชัย สุติ"]

    def request_rider(self, delivery: Delivery) -> Tuple[bool, str, str]:
        is_success, rider_name = super().request_rider(delivery)
        tracking_id = f"LMN-{random.randint(1000000, 9999999)}"
        return is_success, rider_name, tracking_id

    def calculate_fee(self, distance_km: float) -> float:
        """
        คำนวณค่าส่งของ LineMan:
        - 3 กิโลเมตรแรกคิดราคาเหมาจ่าย (15 บาท)
        - กิโลเมตรที่ 4 เป็นต้นไป คิดเพิ่มกิโลเมตรละ 12 บาท
        """
        if distance_km <= 3:
            return self._minimum_fee
        return self._minimum_fee + ((distance_km - 3) * self._price_per_km)

class ShopeeFoodDeliveryProvider(DeliveryProvider):
    def __init__(self) -> None:
        super().__init__(PlatformName.SHOPEE_FOOD)
        self._minimum_fee = 5
        self._price_per_km = 3
        self._riders_name: list[str] = ["ทนากร เอี้ยวพันธ์", "ละม้าย ศรีพลับ", "รุจาภา สันทาลุนัย"]
    
    def request_rider(self, delivery: Delivery) -> Tuple[bool, str, str]:
        is_success, rider_name = super().request_rider(delivery)
        tracking_id = f"SHP-{random.randint(1000000, 9999999)}"
        return is_success, rider_name, tracking_id

    def calculate_fee(self, distance_km: float) -> float:
        """
        คำนวณค่าส่งของ ShopeeFood:
        - คิดราคาตามระยะทาง (3 บาท/กม.)
        - มอบส่วนลดพิเศษ 10% จากราคาปกติ
        - ราคาขั้นต่ำ 5 บาท
        """
        price = distance_km * self._price_per_km
        discounted = price * 0.9
        return discounted if discounted > self._minimum_fee else self._minimum_fee