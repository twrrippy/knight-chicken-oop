from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Dict, Any
from source.utils.enum import RoomStatus, RoomType, BookingStatus

if TYPE_CHECKING:
    from source.restaurant import Member
    
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

    def mark_room_available(self):
        self.__status = RoomStatus.AVAILABLE

    def mark_room_cleaning(self):
        self.__status = RoomStatus.CLEANING

    @property
    def price_per_hour(self): return self.__price_per_hour
    @property
    def id(self): return self.__room_id
    @property
    def status(self): return self.__status
    @property
    def type(self): return self.__room_type
    @property
    def capacity(self): return self.__capacity

class Booking:
    def __init__(self, id: str, member: 'Member', room: 'Room', time_slot: 'TimeSlot'):
        self.__id = id
        self.__member = member
        self.__room = room
        self.__time_slot = time_slot
        self.__status = BookingStatus.PENDING

    def mark_as_deposit_paid(self):
        self.__status = BookingStatus.DEPOSIT_PAID

    def mark_as_paid(self):
        self.__status = BookingStatus.PAID

    def mark_completed(self):
        self.__status = BookingStatus.COMPLETED
        self.room.mark_room_cleaning()
    
    def mark_checked_in(self):
        self.__status = BookingStatus.CHECKED_IN
        self.room.mark_room_in_use()

    def mark_cancelled(self):
        self.__status = BookingStatus.CANCELLED
        self.room.mark_room_available()

    def get_details(self) -> Dict[str, Any]:
        return {
            "type": "Booking Details",
            "status": self.status,
            "booking_id": self.id,
            "room_id": self.room.id,
            "room_type": self.room.type,
            "time_slot": self.time_slot.start_time.strftime("%Y-%m-%d %H:00:00"),
            "full_price": self.full_price,
            "deposit": self.deposit,
            "amount_due": self.amount_due
        }
    
    @property
    def full_price(self): 
        return self.room.price_per_hour * self.time_slot.hours - self.member.get_member_discount(self.room.price_per_hour * self.time_slot.hours)
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
