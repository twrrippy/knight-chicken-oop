from main_system.enum import PlatformName, DeliveryStatus
from main_system.order.order_extention.delivery import Delivery
from typing import Tuple
from fastapi import HTTPException
import random
class DeliveryProvider():
    def __init__(self, platform_name: PlatformName) -> None:
        self.__platform_name = platform_name
    
    def request_rider(self, delivery: Delivery) -> Tuple[bool, str, str]:
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