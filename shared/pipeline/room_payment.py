from __future__ import annotations
from typing import Optional, List, Tuple
from fastapi import FastAPI, HTTPException, Query
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
from fastmcp import FastMCP
import uuid
import random

app = FastAPI()
mcp = FastMCP()

class Status(Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
class OrderType(Enum):
    GENERAL = "General"
    DELIVERY = "Delivery"
    EVENT = "Event"

class DeliveryPlatformName(Enum):
    GRAB_FOOD = "GrabFood"
    LINEMAN = "LineMan"

class OrderStatus(Enum):
    PENDING = "Pending"
    PLACED = "Placed"
    PAID = "Paid"
    COOKING = "Cooking"
    READY_TO_PICKUP = "Ready"      
    COMPLETED = "Completed"
    CANCLED = "Cancled"  

class CouponStatus(Enum):
    USED = "Used"
    AVALIBLE = "Avalible"

class EventOrderStatus(Enum):
    PENDING = "Pending"
    QUEUED = "Queued"

class BookingStatus(Enum):
    PENDING = "Pending"
    IN_USE = "In Use"

class RoomStatus(Enum):
    AVAILABLE = "Available"
    RESERVED = "Reserved"
    IN_USE = "In-Use"
    CLEANING = "Cleaning"

class RoomType(Enum):
    VIP = "VIP"
    STANDARD = "Standard"
    HALL = "Hall"

class MemberTier(Enum):
    BRONZE = "Bronze"
    SILVER = "Silver"
    GOLD = "Gold"

class SimulationClock:
    _current_time = datetime.now()

    @classmethod
    def set_time(cls, new_time: datetime):
        cls._current_time = new_time

    @classmethod
    def get_time(cls):
        return cls._current_time

class Coupon(ABC):
    def __init__(self, id, code, minimum_price) -> None:
        self._id = id
        self._code = code
        self._minimum_price = minimum_price

    @property
    def code(self):
        return self._code

    def is_applicable(self, base_price: float) -> bool:
        return base_price >= self._minimum_price

    @abstractmethod
    def apply_coupon(self, base_price: float) -> float:
        pass

class PercentCoupon(Coupon):
    def __init__(self, id, code, minimum_price, percent) -> None:
        super().__init__(id, code, minimum_price)
        if not (0 <= percent <= 100):
            raise ValueError("Percent must be in range 0-100")
        self._percent = percent

    def apply_coupon(self, base_price: float) -> float:
        if self.is_applicable(base_price):
            return base_price * (self._percent / 100)
        return 0.0

class User:
    def __init__(self, id: str, name: str, phone: str = ""):
        self._id = id
        self._name = name
        self._phone = phone

    @property
    def get_id(self):
        return self._id

class Staff(User):
    def __init__(self, id: str, name: str, role: str):
        super().__init__(id, name)
        self.role = role
    
class PartyStaff(Staff):
    def __init__(self, id: str, name: str):
        super().__init__(id, name, role="Party Staff")

class Customer(User):
    def __init__(self, id: str, name: str):
        super().__init__(id, name)

class Member(Customer):
    def __init__(self, id: str, name: str, tier: MemberTier):
        super().__init__(id, name)
        self._coupon_list: List[List[str | CouponStatus]] = [] 
        self._receipt_list: List[Receipt] = []
        self._tier = tier

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

class EventOrder:
    def __init__(self, id, total_price: float) -> None:
        self._id = id
        self._total_price = total_price
        self._status: EventOrderStatus = EventOrderStatus.PENDING

    @property
    def id(self):
        return self._id
    
    @property
    def total_price(self):
        return self._total_price
    
    @property
    def status(self):
        return self._status
    
    @status.setter
    def status(self, status: EventOrderStatus):
        self._status = status

class Room:
    def __init__(self, room_id: str, room_type: RoomType):
        self.room_id = room_id
        self.room_type = room_type
        self.status: RoomStatus = RoomStatus.AVAILABLE
        if room_type == RoomType.HALL:
            self.capacity = 100
            self.price_per_hour = 5000.0
        elif room_type == RoomType.VIP:
            self.capacity = 20
            self.price_per_hour = 2000.0
        elif room_type == RoomType.STANDARD:
            self.capacity = 10
            self.price_per_hour = 500.0
        else:
            raise ValueError("Unknown room type")

class Booking:
    def __init__(self, booking_id, member: Member, room: Room, start_time: datetime, hours: int) -> None:
        self._booking_id = booking_id
        self._member = member
        self._room = room
        self._start_time = start_time
        self.end_time = start_time + timedelta(hours=hours)
        self.hours = hours
        self._status: BookingStatus = BookingStatus.PENDING
        self._event_order: Optional[EventOrder] = None
        self._base_room_fee = room.price_per_hour * hours
        self.deposit_status = "Unpaid"
        self.required_deposit = self._base_room_fee * 0.5

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
    def status(self) -> BookingStatus: return self._status
    @status.setter
    def status(self, val: BookingStatus): self._status = val
    @property
    def event_order(self): return self._event_order

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

class Restaurant:
    transaction_list: List[Transaction] = []
    coupon_list: List[Coupon] = []
    members: List[Member] = []
    rooms: List[Room] = []
    staff_list: List[PartyStaff] = []
    
    @classmethod
    def add_log(cls, transaction: Transaction):
      cls.transaction_list.append(transaction)
      print(f"[SYSTEM LOG] {transaction.timestamp} | {transaction.id} | {transaction.status} | {transaction.amount} THB | Staff: {transaction.staff_id}")

    @classmethod
    def add_member(cls, member: Member):
        cls.members.append(member)

    @classmethod
    def add_coupon(cls, coupon: Coupon):
        cls.coupon_list.append(coupon)

    @classmethod
    def get_coupon_by_code(cls, code: str) -> Optional[Coupon]:
        for coupon in cls.coupon_list:
            if code == coupon.code:
                return coupon
        return None

class BookingManager:
    _booking_list: List[Booking] = []

    @classmethod
    def add_booking(cls, booking: Booking):
        cls._booking_list.append(booking)

    @classmethod
    def get_booking_from_id(cls, booking_id: str) -> Optional[Booking]:
      for booking in cls._booking_list:
        if booking.id == booking_id:
          return booking
      return None
    
class PaymentStrategy(ABC):
    @classmethod
    def get_strategy(cls, name: str):
      for strategy_cls in PaymentStrategy.__subclasses__():
        try:
          if strategy_cls.get_name().lower() == name.lower():
            return strategy_cls
        except NotImplementedError:
          continue
      raise HTTPException(status_code=400, detail=f"Unknown Strategy: {name}")
    
    @staticmethod
    @abstractmethod
    def get_name() -> str:
      pass
    @staticmethod
    @abstractmethod
    def pay(amount: float) -> Tuple[bool, str]:
      pass

class QRCode(PaymentStrategy):
    @staticmethod
    def get_name() -> str: return "QRCode"
    @staticmethod
    def pay(amount: float) -> Tuple[bool, str]:
      success = random.random() < 0.90
      if success : return True, f"REC-{uuid.uuid4().hex[:8].upper()}"
      return False, "Payment Declined"

class CreditCard(PaymentStrategy):
    @staticmethod
    def get_name() -> str: return "CreditCard"
    @staticmethod
    def pay(amount: float) -> Tuple[bool, str]:
      success = random.random() < 0.80
      if success : return True, f"REC-{uuid.uuid4().hex[:8].upper()}"
      return False, "Payment Declined"

class Cash(PaymentStrategy):
    @staticmethod
    def get_name() -> str: return "Cash"
    @staticmethod
    def pay(amount: float) -> Tuple[bool, str]:
      success = random.random() < 0.99
      if success : return True, f"REC-{uuid.uuid4().hex[:8].upper()}"
      return False, "Payment Declined"

class Receipt:
  def __init__(self, transaction: Transaction, source_object):
    self._transaction = transaction
    self._source = source_object

  def generate(self):
    bill_info = self._source.get_bill_info()
    discounted_amount = bill_info["total_base_price"] - self._transaction.amount

    return {
      "receipt_no": self._transaction.id,
      "date": self._transaction.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
      "merchant": "Knight Chicken Fast Food Co.",
      "order_type": self._transaction.order_type,
      "customer": bill_info["customer_name"],
      "items": bill_info["items"],
      "total_base_price": bill_info["total_base_price"],
      "discount_coupon": self._transaction.coupon_code,
      "deposit_deducted": bill_info["deposit_deducted"],
      "discount_amount": discounted_amount,
      "final_amount_due": self._transaction.amount,
      "payment_method": self._transaction.strategy,
      "status": "PAID"
    }

@mcp.tool
@app.get("/partyroom-payment/get_base_price/{booking_id}")
async def get_base_price(booking_id: str):
    booking = BookingManager.get_booking_from_id(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking Not Found")
    
    return {
        "booking_id": booking.id,
        "room_price": booking.room_price,
        "order_price": booking.event_order.total_price if booking.event_order else 0,
        "total_base_price": booking.total_base_price,
        "deposit_required": booking.required_deposit
    }

@mcp.tool
@app.post("/partyroom-payment/pay/{booking_id}")
async def pay_event(booking_id: str, strategy: str, coupon_code: Optional[str] = Query(default=None)):
    booking = BookingManager.get_booking_from_id(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking Not Found")
    
    if booking.status != BookingStatus.PENDING:
        raise HTTPException(status_code=409, detail="Booking already paid")
    
    coupon = None
    if coupon_code:
        coupon = Restaurant.get_coupon_by_code(coupon_code)
        if not coupon:
                raise HTTPException(status_code=400, detail="Coupon Not Found")

    try:
      discount, final_total = booking.calculate_payment_details(coupon)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    payment_strategy = PaymentStrategy.get_strategy(strategy)
    success, receipt_or_msg = payment_strategy.pay(final_total)

    transaction = Transaction(booking_id,final_total,strategy.lower(), "PENDING", receipt_or_msg, coupon_code if discount > 0 else None, order_type=OrderType.EVENT)

    if success:
        booking.status = BookingStatus.IN_USE
        if booking.event_order:
            booking.event_order.status = EventOrderStatus.QUEUED
        
        member = booking.member
        if coupon_code and discount > 0:
          if not member.mark_coupon_used(coupon_code):
              raise HTTPException(status_code=500, detail="can't mark coupon as used") 

        transaction.mark_success()
        Restaurant.add_log(transaction)

        receipt = Receipt(transaction, booking)
        member.add_receipt(receipt)
        return receipt.generate()
    
    else:
        transaction.mark_failed()
        Restaurant.add_log(transaction)

        raise HTTPException(status_code=402, detail=f"Payment Failed: {receipt_or_msg}")
    

## mock data ##

BookingManager._booking_list.clear()

Restaurant.rooms = [
    Room("R01", RoomType.VIP),
    Room("R02", RoomType.HALL),
    Room("R03", RoomType.STANDARD),
    Room("R04", RoomType.VIP),
    Room("R05", RoomType.STANDARD)
]

alice = Member("M001", "Alice", MemberTier.GOLD)
bob = Member("M002", "Bob", MemberTier.BRONZE)
Restaurant.add_member(alice)
Restaurant.add_member(bob)

c1 = PercentCoupon("C001", "SAVE10", 100, 10.0)
c2 = PercentCoupon("C002", "SAVE20", 500, 20.0)
Restaurant.add_coupon(c1)
Restaurant.add_coupon(c2)

alice.add_coupon("SAVE10")
bob.add_coupon("SAVE10")
bob.add_coupon("SAVE20")

order1 = EventOrder("ORD-001", 150.0)
b1 = Booking("B001", alice, Restaurant.rooms[0], datetime.now(), 2)
b1.add_event_order(order1)
BookingManager.add_booking(b1)

order2 = EventOrder("ORD-002", 600.0)
b2 = Booking("B002", bob, Restaurant.rooms[2], datetime.now(), 1)
b2.add_event_order(order2)
BookingManager.add_booking(b2)

order3 = EventOrder("ORD-003", 50.0)
b3 = Booking("B003", alice, Restaurant.rooms[0], datetime.now(), 1)
b3.add_event_order(order3)
BookingManager.add_booking(b3)

b4 = Booking("B004", bob, Restaurant.rooms[4], datetime.now(), 2)
BookingManager.add_booking(b4)

print("Mock Data Initialized. Ready to test.")

if __name__ == "__main__":
    mcp.run()