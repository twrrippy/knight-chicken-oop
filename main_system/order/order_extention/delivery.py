from main_system.enum import DeliveryStatus
from main_system.external_platform.delivery_provider import DeliveryProvider
from typing import Optional, Dict, Any
from fastapi import HTTPException
class Delivery:
    def __init__(self, delivery_id: str, provider: DeliveryProvider, distance: float):
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