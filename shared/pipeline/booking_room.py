# uvicorn booking_room:app --reload

import uuid
from fastapi import FastAPI, HTTPException, Query, status
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from enum import Enum
# from fastmcp import FastMCP
from abc import ABC, abstractmethod

from shared.pipeline.room_payment import Coupon, CouponStatus, EventOrder, PaymentStrategy, Receipt, RoomType, Status
from shared.pipeline.delivery_order import OrderType
from shared.utils.response import success_response_status, error_response_status


app = FastAPI()
# mcp = FastMCP()
# ==========================================
# Architectural Classes
# ==========================================

class DepositStatus(Enum):
    UNPAID = "Unpaid"
    PAID = "Paid"
    SEIZED = "Seized"

class BookingStatus(Enum):
    PENDING = "Pending"
    RESERVED = "Reserved"
    IN_USE = "In Use"
    CANCELLED_NOSHOW = "Cancelled_NoShow"
    COMPLETED = "Completed"

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
        BookingManager.auto_check_no_show()

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

class Staff(User):
    """Staff Member Class inheriting from User"""
    def __init__(self, id: str, name: str):
        super().__init__(id, name)

class PartyStaff(Staff):
    """Party Staff Role"""
    def __init__(self, id: str, name: str):
        super().__init__(id, name)

    def check_room_avaliability():
        pass

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

    def add_receipt(self, receipt: Receipt):
        self._receipt_list.append(receipt)

    def add_coupon(self, code: str):
        self._coupon_list.append([code, CouponStatus.AVALIBLE])

    def validate_coupon(self, code: str) -> bool:
        for item in self._coupon_list:
            if item[0] == code and item[1] == CouponStatus.AVALIBLE:
                return True
        return False
    
    def mark_coupon_used(self, code: str) -> bool:
        for item in self._coupon_list:
            if item[0] == code and item[1] == CouponStatus.AVALIBLE:
                item[1] = CouponStatus.USED
                return True
        return False
    
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
        self._start_time = start_time
        self._end_time = start_time + timedelta(hours=hours)
        self._hours = hours
        self._status: BookingStatus = BookingStatus.PENDING
        self._event_order: Optional[EventOrder] = None
        self._base_room_fee = room.price_per_hour * hours
        self._deposit_status : DepositStatus = DepositStatus.UNPAID
        self._required_deposit = self._base_room_fee * 0.5

    @property
    def required_deposit(self):
        discount = 0.0
        if self.member.tier == "Gold":
            discount = self._base_room_fee * 0.2
        return (self._base_room_fee - discount) * 0.5
    
    @property
    def deposit_status(self): return self._deposit_status
    @deposit_status.setter  
    def deposit_status(self, val: str): 
        self._deposit_status = val
    @property
    def hours(self): return self._hours
    @property
    def end_time(self): return self._end_time
    @property
    def start_time(self): return self._start_time
    @property
    def base_room_fee(self): return self._base_room_fee
    @property
    def total_price(self): return self._base_room_fee + (self._event_order.total_price if self._event_order else 0.0)
    @property
    def status(self): return self._status
    @status.setter
    def status(self, val: BookingStatus): self._status = val
    @property
    def room(self): return self._room
    @property
    def total_base_price(self) -> float:
        order_price = self._event_order.total_price if self._event_order else 0.0
        return self._base_room_fee + order_price
    @property
    def room_price(self): return self._base_room_fee
    @property
    def id(self): return self._booking_id
    @property
    def member(self): return self._member
    @property
    def event_order(self): return self._event_order

    def calculate_payment_details(self, coupon: Optional[Coupon] = None) -> Tuple[float, float]:
        base_price = self.total_base_price
        discount = 0.0
        
        if coupon:
            if not self.member.validate_coupon(coupon.code):
                raise ValueError("Member does not have this coupon or used")
            if not coupon.is_applicable(base_price):
                raise ValueError("Does Not Meet Minimum Price")
          
            discount = coupon.apply_coupon(base_price)
        
        price_after_discount = base_price - discount
        final_price = price_after_discount - self.required_deposit

        if final_price < 0:
            final_price = 0.0
        
        return (discount, final_price)
            
    def add_event_order(self, event_order: EventOrder):
        if self._event_order is not None:
            raise ValueError("Already Have Event Order")
        self._event_order = event_order
    
    def get_bill_info(self):
        items = [
            {"name": "Room Charge", "price": self._base_room_fee}
        ]
        if self._event_order:
             items.append({"name": "Event Food", "price": self._event_order.total_price})

        return {
            "customer_name": self._member.name,
            "items": items,
            "total_base_price": self.total_base_price,
            "deposit_deducted": self.required_deposit
        }

class Restaurant:
    transaction_list: List[Transaction] = []
    coupon_list: List[Coupon] = []
    members: List[Member] = []
    rooms: List[Room] = []
    staff_list: List[Staff] = []

    @classmethod
    def add_log(cls, transaction: Transaction):
      cls.transaction_list.append(transaction)
      print(f"[SYSTEM LOG] {transaction.timestamp} | {transaction.id} | {transaction.status} | {transaction.amount} THB | Staff: {transaction.staff_id}")

    @classmethod
    def add_member(cls, member: Member): cls.members.append(member)

    @classmethod
    def add_coupon(cls, coupon: Coupon): cls.coupon_list.append(coupon)

    @classmethod
    def get_member(cls, m_id: str): return next((m for m in cls.members if m.id == m_id), None)

    @classmethod
    def get_room(cls, r_id: str): return next((r for r in cls.rooms if r.room_id == r_id), None)
    
    @classmethod
    def get_staff(cls, s_id: str) -> Optional[Staff]: return next((s for s in cls.staff_list if s.id == s_id), None)
    
    @classmethod
    def add_member(cls, member: Member): cls.members.append(member)

    @classmethod
    def get_coupon_by_code(cls, code: str) -> Optional[Coupon]:
        for coupon in cls.coupon_list:
            if code == coupon.code:
                return coupon
        return None

    def booking_room(self, staff_id: str, member_id: str, room_id: str, hours: int, amount_paid: float, strategy: str, start_time: datetime):
        staff = self.get_staff(staff_id)
        if not isinstance(staff, PartyStaff):
            raise HTTPException(status_code=403, detail="Only Party Staff can handle bookings")

        member = self.get_member(member_id)
        if not member or not isinstance(member, Member):
            raise HTTPException(status_code=404, detail="Member not found")
        
        room = self.get_room(room_id)
        if not room or not isinstance(room, Room):
            raise HTTPException(status_code=404, detail="Room not found")

        end_time = start_time + timedelta(hours=hours)
        if not BookingManager.is_slot_available(room, start_time, end_time):
            raise HTTPException(status_code=400, detail="Time slot already occupied")

        booking = Booking(f"BK-{int(SimulationClock.get_time().timestamp())}", member, room, start_time, hours)

        payment_strategy = PaymentStrategy.get_strategy(strategy)
        success, receipt_or_msg = payment_strategy.pay(booking.required_deposit)
        transaction = Transaction(
        target_id=booking.id,
        amount=booking.required_deposit,
        strategy=strategy.lower(),
        status=BookingStatus.PENDING.value,
        payment_id=receipt_or_msg,
        staff_id=staff_id
    )

        if success:
            transaction.mark_success()
            Restaurant.add_log(transaction)
        else:
            transaction.mark_failed()
            Restaurant.add_log(transaction)
            raise HTTPException(status_code=400, detail=f"Payment Failed: {receipt_or_msg}")
        
        BookingManager.add_booking(booking)
        booking.status = BookingStatus.IN_USE
        booking.deposit_status = DepositStatus.PAID

        return {
            "message": "Booking successfully confirmed in one step",
            "booking_id": booking.id,
            "transaction_id": transaction.id,
            "total_price": booking.required_deposit,
            "amount_paid": amount_paid,
            "status": "Reserved"
        }

class BookingManager:
    _booking_list: List[Booking] = []

    @classmethod
    def add_booking(cls, booking: Booking):
        cls._booking_list.append(booking)

    @classmethod
    def auto_check_no_show(cls):
        """if a booking is not checked in within 30 minutes of start time, cancel it and seize deposit"""
        now = SimulationClock.get_time()
        for b in cls._booking_list:
            deadline = b.start_time + timedelta(minutes=30)
            if b.room.status == RoomStatus.RESERVED and now > deadline:
                b.status = BookingStatus.CANCELLED_NOSHOW
                b.deposit_status = DepositStatus.SEIZED
                b.room.status = RoomStatus.AVAILABLE
                

    @classmethod
    def get_booking_from_id(cls, booking_id: str) -> Optional[Booking]:
      for booking in cls._booking_list:
        if booking.id == booking_id:
          return booking
      return None
    
    @classmethod
    def is_slot_available(cls, room: Room, start: datetime, end: datetime):
        """ตรวจสอบช่วงเวลาทับซ้อนเพื่อให้จองล่วงหน้าได้ """
        for b in cls._booking_list:
            if b.room.room_id == room.room_id and b.status not in [BookingStatus.CANCELLED_NOSHOW, BookingStatus.COMPLETED]:
                if start < b.end_time and end > b.start_time:
                    return False
        return True
    
class PaymentGateway:
    """Simulated Payment Gateway Integration"""
    @staticmethod
    def process_payment(required_amount: float, amount_paid: float, member: Member):
        # Simulate payment processing logic
        return amount_paid >= required_amount

# ==========================================
# FastAPI Endpoints
# ==========================================
@app.post("/party-hub/book-and-confirm", tags=["Booking Process"])
async def book_and_confirm(
    staff_id: str, 
    member_id: str, 
    room_id: str, 
    hours: int, 
    amount_paid: float,
    strategy: str = Query(..., description="Payment strategy to use (e.g. QRCode, CreditCard)"),
    start_time: datetime = Query(..., example="2026-02-09 10:00:00")
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
    """
    try:
        restaurant = Restaurant()
        payload = restaurant.booking_room(staff_id, member_id, room_id, hours, amount_paid, strategy, start_time)
        return success_response_status(status= status.HTTP_200_OK,payload= payload)
    except Exception as e:
        return error_response_status(status= status.HTTP_500_INTERNAL_SERVER_ERROR, message=str(e))

# @app.post("/party-hub/request-booking", tags=["Booking Process"])
# async def request_booking(staff_id: str, member_id: str, room_id: str, hours: int, start_time: datetime= Query(description="format: YYYY-MM-DD HH:MM:SS")):
#     """request_booking: There are 5 rooms for booking.\n
#     R01: VIP, Price: 2000 THB/hour\n
#     R02: Hall, Price: 5000 THB/hour\n
#     R03: Standard, Price: 500 THB/hour\n
#     R04: VIP, Price: 2000 THB/hour\n
#     R05: Standard, Price: 500 THB/hour\n
#     """
#     try:
#         staff = Restaurant.get_staff(staff_id)
#         if not staff:
#             raise HTTPException(status_code=403, detail="Only PartyStaff can handle bookings")
        
#         member = Restaurant.get_member(member_id)
#         room = Restaurant.get_room(room_id)
        
#         if not member or not room:
#             raise HTTPException(status_code=404, detail="Member or Room not found")
#         end_time = start_time + timedelta(hours=hours)
#         if not BookingManager.is_slot_available(room_id, start_time, end_time):
#             raise HTTPException(status_code=400, detail="Time slot already occupied")

#         new_booking = Booking(f"BK-{int(datetime.now().timestamp())}", member, room, start_time, hours)
#         BookingManager.add_booking(new_booking)
#         payload ={
#             "booking_id": new_booking.id,
#             "member_tier": member.tier,
#             "total_room_fee": new_booking.total_price,
#             "deposit_required": new_booking.required_deposit,
#             "status": new_booking.status
#         }
#         return success_response_status(status= status.HTTP_200_OK, payload=payload)
#     except Exception as e:
#         return error_response_status(status= status.HTTP_500_INTERNAL_SERVER_ERROR, message=str(e))


# @app.post("/party-hub/pay-deposit/{booking_id}", tags=["Booking Process"])
# async def pay_deposit(booking_id: str, amount: float, staff_id: str):
#     """Pay deposit for the booking to confirm reservation\n
#     - make sure to pay at least the required deposit amount\n
#     - Warning: Please pay the deposit equal to the required amount only!\n
#     """
#     staff = Restaurant.get_staff(staff_id)
#     if not staff:
#         raise HTTPException(status_code=403, detail="Only PartyStaff can handle bookings")
    
#     booking = BookingManager.get_booking_from_id(booking_id)
#     if not booking or booking.status != "Pending_Payment":
#         raise HTTPException(status_code=400, detail="Invalid booking or already processed")

#     if amount != booking.required_deposit:
#         raise HTTPException(status_code=400, detail="Insufficient deposit amount")
#     if not PaymentGateway.process_payment(amount, booking.member):
#         raise HTTPException(status_code=502, detail="Payment processing failed")
    
#     tx_id = f"TXN-{int(SimulationClock.get_time().timestamp())}"
#     new_tx = Transaction(tx_id, booking_id, amount, staff_id)
#     Restaurant.transactions.append(new_tx)

#     booking.status = "Reserved"
#     booking.deposit_status = "Paid"
#     booking.room.status(RoomStatus.RESERVED)
#     return {"message": "Payment Successful", 
#             "status": booking.status,
#             "booking_details": {
#                 "member": booking.member.name,
#                 "room": booking.room.name,
#                 "start_time": booking.start_time,
#                 "hours": booking.hours,
#                 "Warning": f"Please check in within 30 minutes after {booking.start_time} to avoid no-show cancellation.",
#             },
#             "transaction_id": tx_id
#         }

# @app.post("/party-hub/check-in/{booking_id}", tags=["Booking Process"])
# async def check_in(booking_id: str, staff_id: str):
#     """check in to start using the booked room"""
#     staff = Restaurant.get_staff(staff_id)
#     if not staff:
#         raise HTTPException(status_code=403, detail="Only PartyStaff can handle bookings")
    
#     booking = next((b for b in BookingManager.bookings if b.booking_id == booking_id), None)
#     if not booking or booking.status == "Cancelled_NoShow":
#         raise HTTPException(status_code=400, detail="Booking is not active or seized")
    
#     booking.status = "In-Use"
#     booking.room.update_status("In-Use", booking.member.id)
#     return {"status": "Success", "room_status": booking.room.status}

# @app.post("/party-hub/check-out/{booking_id}", tags=["Booking Process"])
# async def check_out(booking_id: str, staff_id: str):
#     """check out to complete the booking and free the room"""
#     staff = Restaurant.get_staff(staff_id)
#     if not staff:
#         raise HTTPException(status_code=403, detail="Only PartyStaff can handle bookings")
    
#     booking = BookingManager.get_booking(booking_id)
#     if not booking or booking.status != "In-Use":
#         raise HTTPException(status_code=400, detail="Booking is not in use")
    
#     now = SimulationClock.get_time()
#     overtime_fee = 0.0
#     if now > booking.end_time: # calculate overtime fee
#         overtime_hours = (now - booking.end_time).total_seconds() / 3600
#         overtime_fee = overtime_hours * booking.room.price_per_hour * 1.5

#     booking.status = "Completed"
#     booking.room.update_status("Cleaning", staff_id)
#     return {"overtime_fee": round(overtime_fee, 2), "room_status": booking.room.status}

# @app.get("/admin/get-all-bookings", tags=["Admin & Testing"])
# async def get_all_bookings():
#     """get all bookings for auditing purposes"""
#     return [
#         {
#             "id": b.id,
#             "member": b.member.name,
#             "room": b.room.name,
#             "status": b.status,
#             "deposit": b.deposit_status
#         } for b in BookingManager._bookings_list
#     ]

@app.get("/admin/get-logs", tags=["Admin & Testing"])
async def get_logs():
    """retrieve all audit logs from the centralized logging system"""
    return {"logs": Restaurant.transaction_list}

@app.get("/admin/get-all-members", tags=["Admin & Testing"])
async def get_all_members():
    """show all members in the system"""
    return [
        {
            "member_id": m.id,
            "name": m.name,
            "tier": m.tier
        } for m in Restaurant.members
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
        } for r in Restaurant.rooms
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

Restaurant.members = [
    Member("M001", "Bob (Gold)", "Gold"),
    Member("M002", "Jack (Silver)", "Silver"),
    Member("M003", "Anna (Silver)", "Silver"),
]

Restaurant.rooms = [
    Room("R01", RoomType.VIP),
    Room("R02", RoomType.HALL),
    Room("R03", RoomType.STANDARD),
    Room("R04", RoomType.VIP),
    Room("R05", RoomType.STANDARD)
]

Restaurant.staff_list = [
    PartyStaff("S01", "Alice"),
    PartyStaff("S02", "Bob"),
]