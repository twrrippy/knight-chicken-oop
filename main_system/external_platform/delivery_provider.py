from main_system.enum import PlatformName, DeliveryStatus
from typing import TYPE_CHECKING, Tuple
from fastapi import HTTPException
import random
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class Delivery:
    def __init__(self, delivery_id: str, provider: 'DeliveryProvider', distance: float):
        self.__delivery_id = delivery_id
        self.__provider = provider
        self.__distance = distance
        self.__status = DeliveryStatus.PENDING
        self.__tracking_id: Optional[str] = None
        self.__rider_name: Optional[str] = None
    
    @property
    def tracking_id(self): return self.__tracking_id
    @property
    def rider_name(self): return self.__rider_name
    @property
    def id(self): return self.__delivery_id
    @property
    def provider(self): return self.__provider
    @property
    def distance(self): return self.__distance
    @property
    def status(self): return self.__status
    @property
    def fee(self):
        return self.provider.calculate_fee(self.distance)
    
    def request_rider(self):
        success, rider_name, tracking_id = self.provider.request_rider(self)
        if success:
            self.__rider_name = rider_name
            self.__tracking_id = tracking_id
            self.__status = DeliveryStatus.DRIVER_ASSIGNED
            return success, rider_name, tracking_id
        raise HTTPException(400, "Rider Request Failed")

    def mark_delivered(self):
        self.__status = DeliveryStatus.DELIVERED

    def mark_as_paid(self):
        self.__status = DeliveryStatus.PAID

    def mark_canceled(self):
        self.__status = DeliveryStatus.CANCELED

    def get_details(self) -> Dict[str, Any]:
        return {
            "type": "Delivery Details",
            "status": self.status,
            "delivery_id": self.id,
            "provider": self.provider.platform_name,
            "tracking_id": self.tracking_id,
            "rider_name": self.rider_name,
            "distance": self.distance,
            "fee": self.fee
        }
class DeliveryProvider(ABC):
    def __init__(self, platform_name: PlatformName) -> None:
        self.__platform_name = platform_name
    
    def request_rider(self, delivery: 'Delivery') -> Tuple[bool, str, str]:
        if not delivery.provider.platform_name == self.platform_name:
            raise HTTPException(400, "Invalid Provider")
        if delivery.status != DeliveryStatus.PENDING:
            raise HTTPException(400, "Delivery Already Assigned")

        is_success = True
        match self.platform_name:
            case PlatformName.GRAB:
                rider_name = random.choice(["สุธนิษฐา จารุตัน", "คมพิชญ์ คำป้อง", "ชูวิทย์ มาตรเหลือง"])
                tracking_id = f"GRB-{random.randint(1000000, 9999999)}"
            case PlatformName.LINE_MAN:
                rider_name = random.choice(["ขวัญหล้า บุญวิวัฒนาการ", "สุสกาวรัตน์อัจฉรา ศรีหะจันทร์", "อัศนีชัย สุติ"])
                tracking_id = f"LMN-{random.randint(1000000, 9999999)}"
            case PlatformName.SHOPEE_FOOD:
                rider_name = random.choice(["ทนากร เอี้ยวพันธ์", "ละม้าย ศรีพลับ", "รุจาภา สันทาลุนัย"])
                tracking_id = f"SHP-{random.randint(1000000, 9999999)}"

        return (is_success, rider_name, tracking_id)

    def calculate_fee(self, distance_km: float) -> float:
        match self.platform_name:
            case PlatformName.GRAB:
                return distance_km * 10
            case PlatformName.LINE_MAN:
                return distance_km * 5
            case PlatformName.SHOPEE_FOOD:
                return distance_km * 2
            case _:
                return 0.0
    
    @property
    def platform_name(self): return self.__platform_name