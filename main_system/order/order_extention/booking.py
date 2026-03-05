from datetime import datetime, timedelta
from fastapi import HTTPException
from typing import Dict, Any
from main_system.enum import RoomStatus, RoomType, BookingStatus
from actor.customer import Member
from shared.utils.simulate import SimulationClock
from main_system.external_platform.payment_method import PaymentMethod
class TimeSlot:
    def __init__(self, start_time: datetime, hours: int):
        self.__start_time = start_time
        self.__end_time = start_time + timedelta(hours=hours)
        self.__hours = hours

    @property
    def start_time(self): return self.__start_time
    @property
    def end_time(self): return self.__end_time
    @property
    def hours(self): return self.__hours

class Room:
    def __init__(self, room_id: str, room_type: RoomType):
        self.__room_id = room_id
        self.__room_type = room_type
        self.__status = RoomStatus.AVAILABLE
        if room_type == RoomType.HALL: 
            self.__price_per_hour = 5000.0
            self.__capacity = 100
        elif room_type == RoomType.VIP: 
            self.__price_per_hour = 2000.0
            self.__capacity = 20
        elif room_type == RoomType.STANDARD: 
            self.__price_per_hour = 500.0
            self.__capacity = 10
        else:
            raise ValueError("Unknown room type")
    
    def mark_room_in_use(self):
        self.__status = RoomStatus.IN_USE

    @property
    def price_per_hour(self): return self.__price_per_hour
    @property
    def room_id(self): return self.__room_id
    @property
    def status(self): return self.__status
    @status.setter
    def status(self, new_status: RoomStatus): self._status = new_status
    @property
    def room_type(self): return self.__room_type
    @property
    def capacity(self): return self.__capacity
class Booking:
    def __init__(self, booking_id, member: Member, room: Room, time_slot: TimeSlot):
        self.__id = booking_id
        self.__member = member
        self.__room = room
        self.__time_slot = time_slot
        self.__status = BookingStatus.PENDING

    # def __init__(self, booking_id, member: Member, room: Room, start_time: datetime, hours: int) -> None:
    #     self._booking_id = booking_id
    #     self._member = member
    #     self._room = room
    #     self._time_slot = TimeSlot(start_time, hours)
    #     self._status: BookingStatus = BookingStatus.PENDING
    #     self._base_room_fee = room.price_per_hour * hours
    #     discount = 0.0
    #     if self.member.tier == "Gold":
    #         discount = self._base_room_fee * 0.2

    #     self.required_deposit = (self._base_room_fee - discount) * 0.5

    # @property
    # def required_deposit(self):
    #     return self._required_deposit
    # @required_deposit.setter
    # def required_deposit(self, amount):
    #     self._required_deposit = amount
    
    # @property
    # def deposit_status(self): return self._deposit_status
    # @deposit_status.setter  
    # def deposit_status(self, val: str): 
    #     self._deposit_status = val
    # @property
    # def hours(self): return self._time_slot.hours
    # @property
    # def end_time(self): return self._time_slot.end_time
    # @property
    # def start_time(self): return self._time_slot.start_time
    # @property
    # def base_room_fee(self): return self._base_room_fee
    # @status.setter
    # def status(self, val: BookingStatus): self._status = val
    # @property
    # def room_price(self): return self._base_room_fee
    # @property
    # def id(self): return self._booking_id

    def pay_deposit(self, method: PaymentMethod, payment_details: Dict[str, Any] = {}) -> Dict:
        sucess, note = method.pay(self.deposit, **payment_details)
        if not sucess: raise HTTPException(400, note)
        self.__status = BookingStatus.DEPOSIT_PAID
        return {
            "booking_no": self.id,
            "date": SimulationClock.get_time().strftime("%Y-%m-%d %H:%M:%S"),
            "merchant": "Knight Chicken Fast Food Co.",
            
            "customer_info": {
                "name": self.member.name,
                "tier": self.member.tier
            },
            
            "booking_details": self.get_details(),
            
            "financial_summary": {
                "subtotal": self.full_price,
                "deposit paid": self.deposit,
                "amount_due": self.amount_due
            },
            
            "payment_record": {
                "method": method.name,
                "status": "deposit Paid"
            }
        }

    def mark_completed(self):
        self.__status = BookingStatus.COMPLETED
    
    def mark_checked_in(self):
        self.__status = BookingStatus.CHECKED_IN

    def get_details(self) -> Dict[str, Any]:
        return {
            "type": "Booking Details",
            "status": self.status,
            "booking_id": self.id,
            "room_id": self.room.id,
            "room_type": self.room.type,
            "time_slot": self.time_slot.start_time,
            "full_price": self.full_price,
            "deposit": self.deposit,
            "amount_due": self.amount_due
        }
    
    @property
    def full_price(self): return self.room.price_per_hour * self.time_slot.hours
    @property
    def deposit(self): return self.full_price * 0.5
    @property
    def amount_due(self): return self.full_price - self.deposit

    @property
    def id(self): return self.__id
    @property
    def member(self): return self.__member
    @property
    def room(self): return self.__room
    @property
    def time_slot(self): return self.__time_slot
    @property
    def status(self): return self.__status