# uvicorn shared.pipeline.booking_room:app --reload

import random
import uuid
from fastapi import Body, FastAPI, HTTPException, Query, status
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
# from fastmcp import FastMCP
from abc import ABC, abstractmethod
from shared.pipeline.delivery_order import CouponStatus
from shared.pipeline.orderPayment import Coupon, RoomType
from shared.utils.response import success_response_status, error_response_status
from shared.pipeline.cooking import Status


app = FastAPI()
# mcp = FastMCP()
# ==========================================
# Architectural Classes
# ==========================================

class BookingStatus(Enum):
    PENDING = "Pending"
    DEPOSIT_PAID = "Deposit Paid" 
    CHECKED_IN = "Checked In"
    COMPLETED = "Completed"  
    CANCELLED = "Canceled"

class RoomStatus(Enum):
    AVAILABLE = "Available"
    IN_USE = "In-Use"
    CLEANING = "Cleaning"


class SimulationClock:
    """Control Over System Time for Testing Purposes"""
    _current_time = datetime.now()

    @classmethod
    def set_time(cls, new_time: datetime):
        cls._current_time = new_time
        # Trigger time-dependent checks
        Restaurant.auto_check_no_show()

    @classmethod
    def get_time(cls):
        return cls._current_time

    
class Receipt:
    def __init__(self, customer: 'Customer', amount: float, pay_method: str, status: str, coupon_code: Optional[str] = None, order: Optional[Order] = None):
      self._id = f"TXN-{uuid.uuid4().hex[:12].upper()}"
      self._order = order
      self._amount = amount
      self._method = pay_method
      self._status = status
      self._coupon = coupon_code
      self._timestamp = datetime.now()
      self._order_type = None
      self._customer = customer

    def mark_success(self): self._status = Status.SUCCESS

    @property
    def id(self): return self._id
    @property
    def timestamp(self): return self._timestamp
    @property
    def status(self): return self._status
    @property
    def amount(self): return self._amount
    @property
    def strategy(self): return self._method
    @property
    def coupon_code(self): return self._coupon
    @property
    def order_type(self): return self._order_type


# ==========================================
# System Domain Classes
# ==========================================
class User:
    def __init__(self, id: str, name: str, phone: str = ""):
        self._id = id
        self._name = name
        self._phone = phone

    @property
    def id(self):
        return self._id
    
    @property
    def name(self):
        return self._name

class Staff(User):
    """Staff Member Class inheriting from User"""
    def __init__(self, id: str, name: str):
        super().__init__(id, name)

    def check_room_avaliability(self, room: str, start: datetime, hours: int):
            return restaurant_system.is_slot_avaliable(room, start, hours)

    def check_in_booking():
        pass

    def check_out_booking():
        pass
    

class Customer(User):
    """Basic Customer Class inheriting from User"""
    def __init__(self, id: str, name: str):
        super().__init__(id, name)

class Member(Customer):
    def __init__(self, id: str, name: str, tier: str):
        super().__init__(id, name)
        self._coupon_list: List[List[str | CouponStatus]] = [] 
        self._receipt_list: List[Receipt] = []
        self._tier = tier

    @property
    def tier(self):
        return self._tier
    
    @property
    def name(self): return self._name

class Room:
    def __init__(self, room_id: str, room_type: RoomType):
        self._room_id = room_id
        self._room_type = room_type
        self._status: RoomStatus = RoomStatus.AVAILABLE
        if room_type == RoomType.HALL:
            self._capacity = 100
            self._price_per_hour = 5000.0
        elif room_type == RoomType.VIP:
            self._capacity = 20
            self._price_per_hour = 2000.0
        elif room_type == RoomType.STANDARD:
            self._capacity = 10
            self._price_per_hour = 500.0
        else:
            raise ValueError("Unknown room type")
        
        
    @property
    def room_type(self): return self._room_type.value
    @property
    def status(self): return self._status
    @status.setter
    def status(self, new_status: RoomStatus): self._status = new_status
    @property
    def room_id(self): return self._room_id
    @property
    def price_per_hour(self): return self._price_per_hour
        

class Booking:
    def __init__(self, booking_id, member: Member, room: Room, start_time: datetime, hours: int) -> None:
        self._booking_id = booking_id
        self._member = member
        self._room = room
        self._time_slot = TimeSlot(start_time, hours)
        self._status: BookingStatus = BookingStatus.PENDING
        self._base_room_fee = room.price_per_hour * hours
        discount = 0.0
        if self.member.tier == "Gold":
            discount = self._base_room_fee * 0.2

        self.required_deposit = (self._base_room_fee - discount) * 0.5

    @property
    def required_deposit(self):
        return self._required_deposit
    @required_deposit.setter
    def required_deposit(self, amount):
        self._required_deposit = amount
    
    @property
    def deposit_status(self): return self._deposit_status
    @deposit_status.setter  
    def deposit_status(self, val: str): 
        self._deposit_status = val
    @property
    def hours(self): return self._time_slot.hours
    @property
    def end_time(self): return self._time_slot.end_time
    @property
    def start_time(self): return self._time_slot.start_time
    @property
    def base_room_fee(self): return self._base_room_fee
    @property
    def status(self): return self._status
    @status.setter
    def status(self, val: BookingStatus): self._status = val
    @property
    def room(self): return self._room
    @property
    def room_price(self): return self._base_room_fee
    @property
    def id(self): return self._booking_id
    @property
    def member(self): return self._member
    @property
    def time_slot(self): return self._time_slot

class Restaurant:
    def __init__(self):
        self._receipt_list: List[Receipt] = []
        self._coupon_list: List[Coupon] = []
        self._members: List[Member] = []
        self._rooms: List[Room] = []
        self._staff_list: List[Staff] = []
        self._booking_list: List[Booking] = []
        self._payment_method: List[PaymentMethod] = []

    def add_receipt(self, receipt: Receipt):
        self._receipt_list.append(receipt)
        # print(f"[SYSTEM LOG] {receipt.timestamp} | {receipt.id} | {receipt.status} | {receipt.amount} THB")
      
    def add_member(self, member: Member): self._members.append(member)
    def add_coupon(self, coupon: Coupon): self._coupon_list.append(coupon)
    def add_booking(self, booking: Booking): self._booking_list.append(booking)
    def get_member(self, m_id: str): return next((m for m in self._members if m.id == m_id), None)
    def get_room(self, r_id: str): return next((r for r in self._rooms if r.room_id == r_id), None)
    def get_staff(self, s_id: str): return next((s for s in self._staff_list if s.id == s_id), None)
    def add_room(self, room: Room): self._rooms.append(room)
    def add_member(self, member: Member): self._members.append(member)
    def add_payment_strategy(self, method: 'PaymentMethod'): self._payment_method.append(method)
    def add_staff(self, staff): self._staff_list.append(staff)

    def get_payment_method(self, method_name: str) -> 'PaymentMethod':
        for s in self._payment_method:
            if s.name.lower() == method_name.lower(): return s
        raise HTTPException(status_code=400, detail="Unknown Method")
    
    def booking_room(self, staff_id: str, member_id: str, room_id: str, hours: int, amount_paid: float, pay_method: str, start_time: datetime, payment_details: Dict[str, Any] = {}):
        staff = self.get_staff(staff_id)
        if not isinstance(staff, Staff):
            raise HTTPException(status_code=403, detail="Only Staff can handle bookings")

        member = self.get_member(member_id)
        if not member or not isinstance(member, Member):
            raise HTTPException(status_code=404, detail="Member not found")
        
        room = self.get_room(room_id)
        if not room or not isinstance(room, Room):
            raise HTTPException(status_code=404, detail="Room not found")

        if not staff.check_room_avaliability(room, start_time, hours):
            raise HTTPException(status_code=400, detail="Time slot already occupied")

        booking = Booking(f"BK-{int(SimulationClock.get_time().timestamp())}", member, room, start_time, hours)

        if amount_paid != booking.required_deposit:
            raise HTTPException(status_code=404, detail=f"Insufficient Amount: need {booking.required_deposit} THB")
        pay_strat = self.get_payment_method(pay_method)
        success, receipt_or_msg = pay_strat.pay(booking.required_deposit, **payment_details)
        receipt = Receipt(
            amount=booking.required_deposit,
            pay_method=pay_method.lower(),
            status=BookingStatus.PENDING,
            customer=member
            )

        if success:
            receipt.mark_success()
            self.add_receipt(receipt=receipt)
            booking.status = BookingStatus.DEPOSIT_PAID
        else:
            raise HTTPException(status_code=400, detail=f"Payment Failed: {receipt_or_msg}")
        
        self.add_booking(booking)
        

        return {
            "message": "Booking successfully confirmed in one step",
            "booking_id": booking.id,
            "receipt_id": receipt.id,
            "total_price": booking.required_deposit,
            "amount_paid": amount_paid,
            "status": "Reserved"
        }

    def is_slot_avaliable(self, room, start, hours): # เปลี่ยนชื่อ room_id เป็น room ให้สื่อความหมาย
        end = start + timedelta(hours=hours)
        for b in self._booking_list:
            if b.room.room_id == room.room_id: 
                if b.status not in [BookingStatus.CANCELLED, BookingStatus.COMPLETED]:
                    if start < b.time_slot.end_time and end > b.time_slot.start_time:
                        return False
        return True

    @classmethod
    def auto_check_no_show(cls):
        now = SimulationClock.get_time()
        for b in cls._booking_list:
            deadline = b.time_slot.start_time + timedelta(minutes=30)
            if b.status == BookingStatus.DEPOSIT_PAID and now > deadline:
                b.status = BookingStatus.CANCELLED
                b.room.status = RoomStatus.AVAILABLE

class TimeSlot:
    def __init__(self, start_time, hours):
        self._start_time = start_time
        self._end_time = start_time + timedelta(hours=hours)
        self._hours = hours

    @property
    def start_time(self): return self._start_time
    @property
    def end_time(self): return self._end_time
    @property
    def hours(self): return self._hours

class PaymentMethod(ABC):

    def __init__(self, id: str, name: str):
        self.__id = id
        self.__name = name

    @property
    def name(self) -> str: return self.__name

    @abstractmethod
    def pay(self, amount: float, **kwargs) -> Tuple[bool, str]: pass

class QRCode(PaymentMethod):
    def __init__(self, id: str, name: str): super().__init__(id, name)

    @property
    def name(self): return "qrcode"
    
    def pay(self, amount: float, **kwargs) -> Tuple[bool, str]:
        account_number = kwargs.get("account_number")
        if not account_number: return False, "Missing 'account_number'"
        
        success = random.random() < 0.90
        return (True, "Payment Done") if success else (False, "Bank System Offline")

class CreditCard(PaymentMethod):
    def __init__(self, id: str, name: str): super().__init__(id, name)
    
    @property
    def name(self): return "creditcard"

    def pay(self, amount: float, **kwargs) -> Tuple[bool, str]:
        if not kwargs.get("card_number") or not kwargs.get("cvv"): 
            return False, "Missing Card Details"
            
        success = random.random() < 0.80
        return (True, "Payment Done") if success else (False, "Card Declined")

class Cash(PaymentMethod):
    def __init__(self, id: str, name: str): super().__init__(id, name)

    @property
    def name(self): return "cash"
    
    def pay(self, amount: float, **kwargs) -> Tuple[bool, str]:
        received = kwargs.get("cash_received")
        if received is None: return False, "Missing 'cash_received'"
        
        if float(received) < amount: return False, f"Insufficient Cash"
        return True, "Payment Done"

# ==========================================
# FastAPI Endpoints
# ==========================================
@app.post("/party-hub/booking-room", tags=["Booking Process"])
async def book_room(
    staff_id: str, 
    member_id: str, 
    room_id: str, 
    hours: int, 
    amount_paid: float,
    pay_method: str = Query(..., description="Payment strategy to use (e.g. QRCode, CreditCard)"),
    start_time: datetime = Query(..., example="2026-02-09 10:00:00"),
    payment_details: Dict[str, Any] = Body(
        ..., 
        example={"account_number": "000-0-00000-0"}
    )
):
    """request_booking: There are 5 rooms for booking.\n
    R01: VIP, Price: 2000 THB/hour\n
    R02: Hall, Price: 5000 THB/hour\n
    R03: Standard, Price: 500 THB/hour\n
    R04: VIP, Price: 2000 THB/hour\n
    R05: Standard, Price: 500 THB/hour\n
    room_price = price_per_hour * hours\n
    deposit = room_price * 50%\n
    Gold members get 20% discount on room price\n
    - payment_details: ข้อมูลเพิ่มเติมตามประเภทการจ่ายเงิน เช่น 
        - qrcode: {'account_number': 'xxx' } 
        - creditcard: {'card_number': '...', 'cvv': '...'} 
        - cash: {'cash_received': xxx}\n
    """
    try:
        payload = restaurant_system.booking_room(staff_id, member_id, room_id, hours, amount_paid, pay_method, start_time=start_time, payment_details=payment_details)
        return success_response_status(status= status.HTTP_200_OK,payload= payload)
    except Exception as e:
        raise error_response_status(status= status.HTTP_500_INTERNAL_SERVER_ERROR, message=str(e))

# ==================================================
# API Admin
# ==================================================
@app.get("/admin/get-logs", tags=["Admin & Testing"])
async def get_logs():
    """retrieve all audit logs from the centralized logging system"""
    return {"logs": restaurant_system._receipt_list}

@app.get("/admin/get-all-members", tags=["Admin & Testing"])
async def get_all_members():
    """show all members in the system"""
    return [
        {
            "member_id": m.id,
            "name": m.name,
            "tier": m.tier
        } for m in restaurant_system._members
    ]

@app.get("/admin/get-all-rooms", tags=["Admin & Testing"])
async def get_all_rooms():
    """get all rooms in the system"""
    return [
        {
            "room_id": r.room_id,
            "name": r.room_type,
            "status": r.status,
            "price_per_hour": r.price_per_hour,
        } for r in restaurant_system._rooms
    ]

@app.get("/admin/get-all-staff", tags=["Admin & Testing"])
async def get_all_staff():
    """get all staff"""
    return [
        {
            "staff_id": s.id,
            "name": s.name,
        } for s in restaurant_system._staff_list
    ]

@app.post("/simulate/advance-time", tags=["Simulation"])
async def advance_time(minutes: int):
    """advance the simulation clock by specified minutes"""
    new_time = SimulationClock.get_time() + timedelta(minutes=minutes)
    SimulationClock.set_time(new_time)
    return {"current_simulation_time": SimulationClock.get_time()}

# # ==========================================
# # Mock Data Setup
# # ==========================================
restaurant_system = Restaurant()

restaurant_system.add_member(Member("M001", "Bob (Gold)", "Gold"))
restaurant_system.add_member(Member("M002", "Jack (Silver)", "Silver"))

restaurant_system.add_room(Room("R01", RoomType.VIP))
restaurant_system.add_room(Room("R02", RoomType.HALL))
restaurant_system.add_room(Room("R03", RoomType.STANDARD))
restaurant_system.add_room(Room("R04", RoomType.VIP))
restaurant_system.add_room(Room("R05", RoomType.STANDARD))

restaurant_system.add_staff(Staff("S01", "Alice"))
restaurant_system.add_staff(Staff("S02", "Bob"))

qr_code_system = QRCode("S1", "QRCode")
credit_card_system = CreditCard("S2", "CreditCard")
cash_system = Cash("S3", "Cash")

restaurant_system.add_payment_strategy(qr_code_system)
restaurant_system.add_payment_strategy(credit_card_system)
restaurant_system.add_payment_strategy(cash_system)