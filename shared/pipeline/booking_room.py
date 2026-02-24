# uvicorn shared.pipeline.booking_room:app --reload

import uuid
from fastapi import Body, FastAPI, HTTPException, Query, status
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
# from fastmcp import FastMCP
from abc import ABC, abstractmethod

from shared.pipeline.Event_order_Payment import Coupon, CouponStatus, EventOrder, PaymentStrategy, Receipt, RoomType
from shared.pipeline.Event_order_Payment import Cash, CreditCard, OrderType, QRCode
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

    
class Transaction:
    def __init__(self, target_id: str, amount: float, strategy: str, status: str, payment_id: str, coupon_code: Optional[str] = None, order_type: OrderType = OrderType.GENERAL, staff_id: str = "SYSTEM"):
      self._id = f"TXN-{uuid.uuid4().hex[:12].upper()}"
      self._target_id = target_id
      self._amount = amount
      self._strategy = strategy
      self._status = status
      self._payment_id = payment_id
      self._coupon_code = coupon_code
      self._timestamp = datetime.now()
      self._order_type = order_type
      self._staff_id = staff_id

    def mark_success(self): self._status = Status.SUCCESS
    def mark_failed(self): self._status = Status.FAILED

    @property
    def id(self): return self._id
    @property
    def timestamp(self): return self._timestamp
    @property
    def status(self): return self._status
    @property
    def amount(self): return self._amount
    @property
    def strategy(self): return self._strategy
    @property
    def coupon_code(self): return self._coupon_code
    @property
    def target_id(self): return self._target_id
    @property
    def order_type(self): return self._order_type
    @property
    def staff_id(self): return self._staff_id

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

class PartyStaff(Staff):
    """Party Staff Role"""
    def __init__(self, id: str, name: str):
        super().__init__(id, name)

    def check_room_avaliability(self, room: str, start: datetime, hours: int):
        return restaurant_system.is_slot_avaliable(room, start, hours)

    def check_in_booking():
        pass

    def check_out_booking():
        pass



class KitchenStaff(Staff):
    """Kitchen Staff Role"""
    def __init__(self, id: str, name: str):
        super().__init__(id, name)

class FrontStaff(Staff):
    """Front Staff Role"""
    def __init__(self, id: str, name: str):
        super().__init__(id, name)

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
        self._event_order: Optional[EventOrder] = None
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
        self._transaction_list: List[Transaction] = []
        self._coupon_list: List[Coupon] = []
        self._members: List[Member] = []
        self._rooms: List[Room] = []
        self._staff_list: List[Staff] = []
        self._booking_list: List[Booking] = []
        self._payment_strategies: List[PaymentStrategy] = []

    def add_log(self, transaction: Transaction):
      self._transaction_list.append(transaction)
      print(f"[SYSTEM LOG] {transaction.timestamp} | {transaction.id} | {transaction.status} | {transaction.amount} THB | Staff: {transaction.staff_id}")
    def add_member(self, member: Member): self._members.append(member)
    def add_coupon(self, coupon: Coupon): self._coupon_list.append(coupon)
    def add_booking(self, booking: Booking): self._booking_list.append(booking)
    def get_member(self, m_id: str): return next((m for m in self._members if m.id == m_id), None)
    def get_room(self, r_id: str): return next((r for r in self._rooms if r.room_id == r_id), None)
    def get_staff(self, s_id: str): return next((s for s in self._staff_list if s.id == s_id), None)
    def add_room(self, room: Room): self._rooms.append(room)
    def add_member(self, member: Member): self._members.append(member)
    def add_payment_strategy(self, strategy: PaymentStrategy): self._payment_strategies.append(strategy)
    def add_staff(self, staff): self._staff_list.append(staff)

    def get_payment_strategy(self, strategy_name: str) -> PaymentStrategy:
        for s in self._payment_strategies:
            if s.name.lower() == strategy_name.lower(): return s
        raise HTTPException(status_code=400, detail="Unknown Strategy")
    
    def booking_room(self, staff_id: str, member_id: str, room_id: str, hours: int, amount_paid: float, strategy: str, start_time: datetime, payment_details: Dict[str, Any] = {}):
        staff = self.get_staff(staff_id)
        if not isinstance(staff, PartyStaff):
            raise HTTPException(status_code=403, detail="Only Party Staff can handle bookings")

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
        pay_strat = self.get_payment_strategy(strategy)
        success, txn_id, receipt_or_msg = pay_strat.pay(booking.required_deposit, **payment_details)
        transaction = Transaction(
            target_id=booking.id,
            amount=booking.required_deposit,
            strategy=strategy.lower(),
            status=BookingStatus.PENDING,
            payment_id=txn_id,
            staff_id=staff_id
            )

        if success:
            transaction.mark_success()
            self.add_log(transaction)
            booking.status = BookingStatus.DEPOSIT_PAID
        else:
            transaction.mark_failed()
            self.add_log(transaction)
            raise HTTPException(status_code=400, detail=f"Payment Failed: {receipt_or_msg}")
        
        self.add_booking(booking)
        

        return {
            "message": "Booking successfully confirmed in one step",
            "booking_id": booking.id,
            "transaction_id": transaction.id,
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
    strategy: str = Query(..., description="Payment strategy to use (e.g. QRCode, CreditCard)"),
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
        payload = restaurant_system.booking_room(staff_id, member_id, room_id, hours, amount_paid, strategy, start_time=start_time, payment_details=payment_details)
        return success_response_status(status= status.HTTP_200_OK,payload= payload)
    except Exception as e:
        raise error_response_status(status= status.HTTP_500_INTERNAL_SERVER_ERROR, message=str(e))

# ==================================================
# API Admin
# ==================================================
@app.get("/admin/get-logs", tags=["Admin & Testing"])
async def get_logs():
    """retrieve all audit logs from the centralized logging system"""
    return {"logs": Restaurant._transaction_list}

@app.get("/admin/get-all-members", tags=["Admin & Testing"])
async def get_all_members():
    """show all members in the system"""
    return [
        {
            "member_id": m.id,
            "name": m.name,
            "tier": m.tier
        } for m in Restaurant._members
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
        } for r in Restaurant._rooms
    ]

@app.get("/admin/get-all-staff", tags=["Admin & Testing"])
async def get_all_staff():
    """get all staff"""
    return [
        {
            "staff_id": s.id,
            "name": s.name,
        } for s in Restaurant._staff_list
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

restaurant_system.add_staff(PartyStaff("S01", "Alice"))
restaurant_system.add_staff(PartyStaff("S02", "Bob"))

qr_code_system = QRCode("S1", "QRCode")
credit_card_system = CreditCard("S2", "CreditCard")
cash_system = Cash("S3", "Cash")

restaurant_system.add_payment_strategy(qr_code_system)
restaurant_system.add_payment_strategy(credit_card_system)
restaurant_system.add_payment_strategy(cash_system)