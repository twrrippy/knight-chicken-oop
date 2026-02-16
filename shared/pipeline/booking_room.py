# uvicorn booking_room:app --reload

from fastapi import FastAPI, HTTPException, Query
from datetime import datetime, timedelta
from typing import List, Optional

app = FastAPI()

# ==========================================
# Architectural Classes
# ==========================================

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

class Log:
    """Centralized Logging System for Auditing"""
    _logs = []

    @classmethod
    def add_entry(cls, user_id: str, action: str, before: str, after: str):
        entry = {
            "timestamp": SimulationClock.get_time(),
            "user_id": user_id,
            "action": action,
            "data_before": before,
            "data_after": after
        }
        cls._logs.append(entry)

    @classmethod
    def get_all_logs(cls):
        return cls._logs
    
class Transaction:
    """Financial Transaction Record"""
    def __init__(self, tx_id: str, booking_id: str, amount: float, staff_id: str):
        self.tx_id = tx_id
        self.booking_id = booking_id
        self.amount = amount
        self.timestamp = SimulationClock.get_time()
        self.staff_id = staff_id

# ==========================================
# System Domain Classes
# ==========================================
class User:
    """Basic User Class"""
    def __init__(self, id: str, name: str, phone: str = ""):
        self.id = id
        self.name = name
        self.phone = phone

    @property
    def get_id(self):
        return self.id

class Staff(User):
    """Staff Member Class inheriting from User"""
    def __init__(self, id: str, name: str, role: str):
        super().__init__(id, name)
        self.role = role

class PartyStaff(Staff):
    """Party Staff Role"""
    def __init__(self, id: str, name: str):
        super().__init__(id, name, role="Party Host")

class Customer(User):
    """Basic Customer Class inheriting from User"""
    def __init__(self, id: str, name: str):
        super().__init__(id, name)

class Member(Customer):
    def __init__(self, id: str, name: str, tier: str):
        super().__init__(id, name)
        self.tier = tier # Bronze, Silver, Gold

class Room:
    def __init__(self, room_id: str, name: str):
        self.room_id = room_id
        self.name = name
        self.status = "Available" # Available, Reserved, In-Use, Cleaning
        if name == "Hall":
            self.capacity = 100
            self.price_per_hour = 5000.0
        elif name == "VIP":
            self.capacity = 20
            self.price_per_hour = 2000.0
        elif name == "Standard":
            self.capacity = 10
            self.price_per_hour = 500.0
        else:
            raise ValueError("Unknown room type")
        

    def update_status(self, new_status: str, id: str = "System"):
        old_status = self.status
        self.status = new_status
        Log.add_entry(id, f"ROOM_{self.room_id}_STATUS", old_status, new_status)

class Booking:
    def __init__(self, booking_id: str, member: Member, room: Room, start_time: datetime, hours: int):
        self.booking_id = booking_id
        self.member = member
        self.room = room
        self.start_time = start_time
        self.end_time = start_time + timedelta(hours=hours)
        self.hours = hours
        self.status = "Pending_Payment" # Pending_Payment, Reserved, In-Use, Completed, Cancelled_NoShow
        self.deposit_status = "Unpaid"

        # calculate fees and discounts based on member tier
        self.base_room_fee = room.price_per_hour * hours
        discount_rate = 0.20 if member.tier == "Gold" else 0.0
        self.discount_amount = self.base_room_fee * discount_rate
        self.total_price = self.base_room_fee - self.discount_amount
        self.required_deposit = self.total_price * 0.5 # 50% deposit required


class Restaurant:
    members: List[Member] = []
    rooms: List[Room] = []
    staff_list: List[PartyStaff] = []
    transactions: List[Transaction] = []

    @classmethod
    def get_member(cls, m_id: str):
        return next((m for m in cls.members if m.id == m_id), None)

    @classmethod
    def get_room(cls, r_id: str):
        return next((r for r in cls.rooms if r.room_id == r_id), None)
    
    @classmethod
    def get_staff(cls, s_id: str) -> Optional[PartyStaff]:
        return next((s for s in cls.staff_list if s.id == s_id), None)
    
    @classmethod
    def add_member(cls, member: Member):
        cls.members.append(member)

    def _create_transaction(self, booking_id: str, amount: float, staff_id: str) -> Transaction:
        tx_id = f"TXN-{int(SimulationClock.get_time().timestamp())}"
        new_tx = Transaction(tx_id, booking_id, amount, staff_id)
        Restaurant.transactions.append(new_tx)
        return tx_id

    def booking_room(self, staff_id: str, member_id: str, room_id: str, hours: int, amount_paid: float, start_time: datetime):
        staff = self.get_staff(staff_id)
        if staff.role != "Party Host" and not staff :
            raise HTTPException(status_code=403, detail="Only PartyStaff can handle bookings")

        member = self.get_member(member_id)
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")
        
        room = self.get_room(room_id)
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")

        end_time = start_time + timedelta(hours=hours)
        if not BookingManager.is_slot_available(room_id, start_time, end_time):
            raise HTTPException(status_code=400, detail="Time slot already occupied")

        temp_booking = Booking(f"BK-{int(SimulationClock.get_time().timestamp())}", member, room, start_time, hours)

        if not PaymentGateway.process_payment(required_amount=temp_booking.required_deposit, amount_paid=amount_paid, member=member):
            raise HTTPException(status_code=502, detail="Payment Gateway Error")

        tx_id = self._create_transaction(temp_booking.booking_id, amount_paid, staff_id)

        temp_booking.status = "Reserved"
        temp_booking.deposit_status = "Paid"
        room.update_status("Reserved", staff_id)
        
        BookingManager.bookings.append(temp_booking)

        return {
            "message": "Booking successfully confirmed in one step",
            "booking_id": temp_booking.booking_id,
            "transaction_id": tx_id,
            "total_price": temp_booking.total_price,
            "amount_paid": amount_paid,
            "status": "Reserved"
        }

class BookingManager:
    bookings: List[Booking] = []

    @classmethod
    def auto_check_no_show(cls):
        """if a booking is not checked in within 30 minutes of start time, cancel it and seize deposit"""
        now = SimulationClock.get_time()
        for b in cls.bookings:
            deadline = b.start_time + timedelta(minutes=30)
            if b.status == "Reserved" and now > deadline:
                old_status = b.status
                b.status = "Cancelled_NoShow"
                b.deposit_status = "Seized"
                b.room.update_status("Available")
                Log.add_entry("System", f"BOOKING_{b.booking_id}_NOSHOW", old_status, b.status)

    @classmethod
    def get_booking(cls, b_id: str) -> Optional[Booking]:
        return next((b for b in cls.bookings if b.booking_id == b_id), None)
    
    @classmethod
    def is_slot_available(cls, room_id: str, start: datetime, end: datetime):
        """ตรวจสอบช่วงเวลาทับซ้อนเพื่อให้จองล่วงหน้าได้ """
        for b in cls.bookings:
            if b.room.room_id == room_id and b.status not in ["Cancelled_NoShow", "Completed"]:
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
    restaurant = Restaurant()
    return restaurant.booking_room(staff_id, member_id, room_id, hours, amount_paid, start_time)

@app.post("/party-hub/request-booking", tags=["Booking Process"])
async def request_booking(staff_id: str, member_id: str, room_id: str, hours: int, start_time: datetime= Query(description="format: YYYY-MM-DD HH:MM:SS")):
    """request_booking: There are 5 rooms for booking.\n
    R01: VIP, Price: 2000 THB/hour\n
    R02: Hall, Price: 5000 THB/hour\n
    R03: Standard, Price: 500 THB/hour\n
    R04: VIP, Price: 2000 THB/hour\n
    R05: Standard, Price: 500 THB/hour\n
    """
    staff = Restaurant.get_staff(staff_id)
    if not staff:
        raise HTTPException(status_code=403, detail="Only PartyStaff can handle bookings")
    
    member = Restaurant.get_member(member_id)
    room = Restaurant.get_room(room_id)
    
    if not member or not room:
        raise HTTPException(status_code=404, detail="Member or Room not found")
    end_time = start_time + timedelta(hours=hours)
    if not BookingManager.is_slot_available(room_id, start_time, end_time):
        raise HTTPException(status_code=400, detail="Time slot already occupied")

    new_booking = Booking(f"BK-{int(datetime.now().timestamp())}", member, room, start_time, hours)
    BookingManager.bookings.append(new_booking)
    return {
        "booking_id": new_booking.booking_id,
        "member_tier": member.tier,
        "total_room_fee": new_booking.total_price,
        "deposit_required": new_booking.required_deposit,
        "status": new_booking.status
    }

@app.post("/party-hub/pay-deposit/{booking_id}", tags=["Booking Process"])
async def pay_deposit(booking_id: str, amount: float, staff_id: str):
    """Pay deposit for the booking to confirm reservation\n
    - make sure to pay at least the required deposit amount\n
    - Warning: Please pay the deposit equal to the required amount only!\n
    """
    staff = Restaurant.get_staff(staff_id)
    if not staff:
        raise HTTPException(status_code=403, detail="Only PartyStaff can handle bookings")
    
    booking = BookingManager.get_booking(booking_id)
    if not booking or booking.status != "Pending_Payment":
        raise HTTPException(status_code=400, detail="Invalid booking or already processed")

    if amount != booking.required_deposit:
        raise HTTPException(status_code=400, detail="Insufficient deposit amount")
    if not PaymentGateway.process_payment(amount, booking.member):
        raise HTTPException(status_code=502, detail="Payment processing failed")
    
    tx_id = f"TXN-{int(SimulationClock.get_time().timestamp())}"
    new_tx = Transaction(tx_id, booking_id, amount, staff_id)
    Restaurant.transactions.append(new_tx)

    booking.status = "Reserved"
    booking.deposit_status = "Paid"
    booking.room.update_status("Reserved", booking.member.id)
    return {"message": "Payment Successful", 
            "status": booking.status,
            "booking_details": {
                "member": booking.member.name,
                "room": booking.room.name,
                "start_time": booking.start_time,
                "hours": booking.hours,
                "Warning": f"Please check in within 30 minutes after {booking.start_time} to avoid no-show cancellation.",
            },
            "transaction_id": tx_id
        }

@app.post("/party-hub/check-in/{booking_id}", tags=["Booking Process"])
async def check_in(booking_id: str, staff_id: str):
    """check in to start using the booked room"""
    staff = Restaurant.get_staff(staff_id)
    if not staff:
        raise HTTPException(status_code=403, detail="Only PartyStaff can handle bookings")
    
    booking = next((b for b in BookingManager.bookings if b.booking_id == booking_id), None)
    if not booking or booking.status == "Cancelled_NoShow":
        raise HTTPException(status_code=400, detail="Booking is not active or seized")
    
    booking.status = "In-Use"
    booking.room.update_status("In-Use", booking.member.id)
    return {"status": "Success", "room_status": booking.room.status}

@app.post("/party-hub/check-out/{booking_id}", tags=["Booking Process"])
async def check_out(booking_id: str, staff_id: str):
    """check out to complete the booking and free the room"""
    staff = Restaurant.get_staff(staff_id)
    if not staff:
        raise HTTPException(status_code=403, detail="Only PartyStaff can handle bookings")
    
    booking = BookingManager.get_booking(booking_id)
    if not booking or booking.status != "In-Use":
        raise HTTPException(status_code=400, detail="Booking is not in use")
    
    now = SimulationClock.get_time()
    overtime_fee = 0.0
    if now > booking.end_time: # calculate overtime fee
        overtime_hours = (now - booking.end_time).total_seconds() / 3600
        overtime_fee = overtime_hours * booking.room.price_per_hour * 1.5

    booking.status = "Completed"
    booking.room.update_status("Cleaning", staff_id)
    return {"overtime_fee": round(overtime_fee, 2), "room_status": booking.room.status}

@app.get("/admin/get-all-bookings", tags=["Admin & Testing"])
async def get_all_bookings():
    """get all bookings for auditing purposes"""
    return [
        {
            "id": b.booking_id,
            "member": b.member.name,
            "room": b.room.name,
            "status": b.status,
            "deposit": b.deposit_status
        } for b in BookingManager.bookings
    ]

@app.get("/admin/get-logs", tags=["Admin & Testing"])
async def get_logs():
    """retrieve all audit logs from the centralized logging system"""
    return {"logs": Log.get_all_logs()}

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
            "name": r.name,
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

# ==========================================
# Mock Data Setup
# ==========================================

Restaurant.members = [
    Member("M001", "Bob (Gold)", "Gold"),
    Member("M002", "Jack (Bronze)", "Bronze"),
    Member("M003", "Anna (Silver)", "Silver"),
]

Restaurant.rooms = [
    Room("R01", "VIP"),
    Room("R02", "Hall"),
    Room("R03", "Standard"),
    Room("R04", "VIP"),
    Room("R05", "Standard")
]

Restaurant.staff_list = [
    PartyStaff("S01", "Alice"),
    PartyStaff("S02", "Bob"),
]