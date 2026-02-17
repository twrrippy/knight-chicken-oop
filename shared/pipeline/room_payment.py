from __future__ import annotations
from typing import Optional, List, Tuple, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
from fastmcp import FastMCP
import uuid
import random

app = FastAPI()
mcp = FastMCP("PartyRoomPayment System")

# --- Enums ---
class Status(Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

class OrderType(Enum):
    GENERAL = "General"
    DELIVERY = "Delivery"
    EVENT = "Event"

class OrderStatus(Enum):
    PENDING = "Pending"
    PLACED = "Placed"
    PAID = "Paid"
    COOKING = "Cooking"
    READY_TO_PICKUP = "Ready"      
    COMPLETED = "Completed"
    CANCELED = "Canceled"

class EventOrderStatus(Enum):
    PENDING = "Pending"
    QUEUED = "Queued"
    COOKING = "Cooking"
    SERVED = "Served"

class BookingStatus(Enum):
    PENDING = "Pending"
    IN_USE = "In Use"
    PAID = "Paid"

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

class CouponStatus(Enum):
    AVAILABLE = "Available"
    NOT_AVAILABLE = "Not Available"

class StaffRole(Enum):
    PartyStaff = "Party Staff"
    KitchenStaff = "Kitchen Staff"

# --- Utilities ---
class SimulationClock:
    __current_time = datetime.now()

    @classmethod
    def set_time(cls, new_time: datetime):
        cls.__current_time = new_time

    @classmethod
    def get_time(cls):
        return cls.__current_time

# --- Core Classes ---
class Coupon(ABC):
    def __init__(self, id, code, minimum_price) -> None:
        self.__id = id
        self.__code = code
        self.__minimum_price = minimum_price
        self.__status: CouponStatus = CouponStatus.AVAILABLE

    @property
    def minimum_price(self):
        return self.__minimum_price

    @property
    def status(self):
        return self.__status

    @property
    def code(self):
        return self.__code

    def is_applicable(self, base_price: float) -> bool:
        return base_price >= self.__minimum_price

    @abstractmethod
    def apply_coupon(self, base_price: float) -> float:
        pass

    def mark_as_used(self):
        self.__status = CouponStatus.NOT_AVAILABLE

class PercentCoupon(Coupon):
    def __init__(self, id, code, minimum_price, percent) -> None:
        super().__init__(id, code, minimum_price)
        if not (0 <= percent <= 100):
            raise ValueError("Percent must be in range 0-100")
        self.__percent = percent

    def apply_coupon(self, base_price: float) -> float:
        if self.is_applicable(base_price):
            return base_price * (self.__percent / 100)
        raise ValueError(f"Does Not Meet Minimum Price (Min: {self.minimum_price})")

# [NEW] Interface for any object that can be paid
class Payable(ABC):
    @property
    @abstractmethod
    def id(self) -> str: pass
    
    @property
    @abstractmethod
    def total_price(self) -> float: pass

    @property
    @abstractmethod
    def order_type(self) -> OrderType: pass

    @property
    @abstractmethod
    def coupon_used(self) -> Optional[Coupon]: pass

    @abstractmethod
    def get_bill_info(self) -> Dict[str, Any]: pass

class Transaction:
    def __init__(self, source: Payable, strategy: str, status: str, payment_id: str, staff_id: str = "SYSTEM"):
      self.__id = f"TXN-{uuid.uuid4().hex[:12].upper()}"
      self.__source = source            
      self.__target_id = source.id      
      self.__amount = source.total_price 
      self.__order_type = source.order_type 
      self.__coupon = source.coupon_used    
      
      self.__strategy = strategy
      self.__status = status
      self.__payment_id = payment_id
      self.__timestamp = SimulationClock.get_time()
      self.__staff_id = staff_id

    def mark_success(self): self.__status = Status.SUCCESS
    def mark_failed(self): self.__status = Status.FAILED

    @property
    def id(self): return self.__id
    @property
    def timestamp(self): return self.__timestamp
    @property
    def status(self): return self.__status
    @property
    def amount(self): return self.__amount
    @property
    def strategy(self): return self.__strategy
    @property
    def coupon(self): return self.__coupon
    @property
    def target_id(self): return self.__target_id
    @property
    def order_type(self): return self.__order_type
    @property
    def staff_id(self): return self.__staff_id

class User:
    def __init__(self, id: str, name: str, phone: str = ""):
        self.__id = id
        self.__name = name
        self.__phone = phone

    @property
    def id(self):
        return self.__id
    
    @property
    def name(self):
        return self.__name

class Staff(User):
    def __init__(self, id: str, name: str, role: StaffRole):
        super().__init__(id, name)
        self.__role = role
    
    @property
    def role(self):
        return self.__role

class PartyStaff(Staff):
    def __init__(self, id: str, name: str):
        super().__init__(id, name, role=StaffRole.PartyStaff)

class Customer(User):
    def __init__(self, id: str, name: str):
        super().__init__(id, name)

class Receipt:
  def __init__(self, transaction: Transaction, source_object: Payable):
    self.__transaction = transaction
    self.__source = source_object

  def generate(self):
    bill_info = self.__source.get_bill_info()
    discounted_amount = bill_info["total_base_price"] - self.__transaction.amount
    coupon_code = self.__transaction.coupon.code if self.__transaction.coupon else "None"

    return {
      "receipt_no": self.__transaction.id,
      "date": self.__transaction.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
      "merchant": "Knight Chicken Fast Food Co.",
      "order_type": self.__transaction.order_type.value,
      "customer": bill_info["customer_name"],
      "items": bill_info["items"],
      "total_base_price": bill_info["total_base_price"],
      "discount_coupon": coupon_code,
      "deposit_deducted": bill_info.get("deposit_deducted", 0.0),
      "discount_amount": discounted_amount,
      "final_amount_due": self.__transaction.amount,
      "payment_method": self.__transaction.strategy,
      "status": "PAID"
    }

class Member(Customer):
    def __init__(self, id: str, name: str, tier: MemberTier):
        super().__init__(id, name)
        self.__coupon_list: List[Coupon] = [] 
        self.__receipt_list: List[Receipt] = []
        self.__tier = tier

    def add_receipt(self, receipt: Receipt):
        self.__receipt_list.append(receipt)

    def add_coupon(self, coupon: Coupon):
        self.__coupon_list.append(coupon)

    def get_coupon_by_code(self, code: str):
        for coupon in self.__coupon_list:
            if coupon.code == code:
                return coupon
        return None
    
    @property
    def tier(self):
        return self.__tier

class Food:
    def __init__(self, name: str, price: float):
        self.__name = name
        self.__price = price
    
    @property
    def name(self): return self.__name
    @property
    def price(self): return self.__price

    def __str__(self):
        return f"Name : {self.name}, Price : {self.price}"

class EventOrder:
    def __init__(self, id) -> None:
        self.__id = id
        self.__total_price = 0.0
        self.__status: EventOrderStatus = EventOrderStatus.PENDING
        self.__food_list: List[Food] = []

    def add_food(self, food: Food):
        self.__food_list.append(food)
        self.__total_price += food.price

    @property
    def food_list(self): return self.__food_list
    @property
    def id(self): return self.__id
    @property
    def total_price(self): return self.__total_price
    @property
    def status(self): return self.__status
    @status.setter
    def status(self, status: EventOrderStatus): self.__status = status

class Room:
    def __init__(self, room_id: str, room_type: RoomType):
        self.__room_id = room_id
        self.__room_type = room_type
        self.__status: RoomStatus = RoomStatus.AVAILABLE
        if room_type == RoomType.HALL:
            self.__capacity = 100
            self.__price_per_hour = 5000.0
        elif room_type == RoomType.VIP:
            self.__capacity = 20
            self.__price_per_hour = 2000.0
        elif room_type == RoomType.STANDARD:
            self.__capacity = 10
            self.__price_per_hour = 500.0
        else:
            raise ValueError("Unknown room type")
    
    def mark_room_in_use(self):
        self.__status = RoomStatus.IN_USE
    
    @property
    def capacity(self): return self.__capacity
    @property
    def price_per_hour(self): return self.__price_per_hour
    @property
    def id(self): return self.__room_id
    @property
    def type(self): return self.__room_type

class Booking(Payable):
    def __init__(self, booking_id, member: Member, room: Room, start_time: datetime, hours: int) -> None:
        self.__booking_id = booking_id
        self.__member = member
        self.__room = room
        self.__start_time = start_time
        self.__end_time = start_time + timedelta(hours=hours)
        self.__hours = hours
        self.__status: BookingStatus = BookingStatus.PENDING
        self.__event_order: Optional[EventOrder] = None
        self.__deposit_status = "Unpaid"
        self.__room_price = self.room.price_per_hour * self.hours
        self.__required_deposit = self.__room_price  * 0.5
        self.__total_price = 0.0
        self.__coupon_used: Optional[Coupon] =  None

    def calculate_payment_details(self, coupon: Optional[Coupon] = None):
        member = self.member
        room = self.room
        hours = self.hours
        start_time = self.__start_time
        end_time = self.__end_time
        room_price = self.__room_price
        deposit_price = self.__required_deposit
        discount = 0.0

        if not self.event_order:
            raise ValueError("No Order Yet")
        
        food_list = self.event_order.food_list
        food_list_serialized = [{"name": f.name, "price": f.price} for f in food_list]
        order_price = self.event_order.total_price

        base_price = order_price + room_price - deposit_price
        
        if coupon:
            if coupon.status == CouponStatus.NOT_AVAILABLE:
                raise ValueError("Coupon is Not Available")
            discount = coupon.apply_coupon(base_price)
            self.__coupon_used = coupon
        else:
            self.__coupon_used = None

        final_price = base_price - discount
        
        if final_price < 0:
            final_price = 0.0
        
        self.__total_price = final_price
        
        return {
            "Member" : {
                "Name" : member.name,
                "Tier" : member.tier.value
            },
            "Booking Id" : self.id,
            "Item": {
                "Room" : {
                    "Id" : room.id,
                    "Capacity" : room.capacity,
                    "Price Per Hours" : room.price_per_hour,
                    "Start Time" : start_time.strftime("%H:%M"),
                    "End Time" : end_time.strftime("%H:%M"),
                    "Total Hours" : hours,
                    "Deposit" : deposit_price,
                    "Total Room Price" : room_price - deposit_price
                },
                "Order" : {
                    "Food" : food_list_serialized,
                    "Total Order Price" : order_price
                }
            },
            "Total Price Before Discount" : base_price,
            "Coupon Code" : coupon.code if coupon else "None",
            "Discounted" : discount,
            "Total Price" : final_price
        }
            
    def add_event_order(self, event_order: EventOrder):
        if self.__event_order is not None:
            raise ValueError("Already Have Event Order")
        self.__event_order = event_order
    
    def get_bill_info(self):
        items = [
            {"name": f"Room Charge ({self.room.id})", "Total Hours": self.hours, "price": self.room_price}
        ]
        if self.event_order:
             food_list = self.event_order.food_list
             food_list_serialized = [{"name": f.name, "price": f.price} for f in food_list]
             items.append({"name": "Event Food", 
                           "Food": food_list_serialized
                           })

        return {
            "customer_name": self.__member.name,
            "items": items,
            "total_base_price": self.room_price + (self.__event_order.total_price if self.__event_order else 0),
            "deposit_deducted": self.__required_deposit
        }
    
    
    @property
    def order_type(self): return OrderType.EVENT
    @property
    def coupon_used(self): return self.__coupon_used
    @property
    def total_price(self): return self.__total_price
    
    
    @property
    def hours(self): return self.__hours
    @property
    def room(self): return self.__room
    @property
    def room_price(self): return self.__room_price
    @property
    def id(self): return self.__booking_id
    @property
    def member(self): return self.__member
    @property
    def status(self) -> BookingStatus: return self.__status
    @status.setter
    def status(self, val: BookingStatus): self.__status = val
    @property
    def event_order(self): return self.__event_order

# --- Strategies ---
class PaymentStrategy(ABC):
    @staticmethod
    @abstractmethod
    def get_name() -> str:
      pass
    @abstractmethod
    def pay(self, amount: float, **kwargs) -> Tuple[bool, str]:
        pass

class QRCode(PaymentStrategy):
    @staticmethod
    def get_name() -> str: return "QRCode"
    
    def pay(self, amount: float, **kwargs) -> Tuple[bool, str]:
      success = random.random() < 0.90
      if success : return True, f"REC-{uuid.uuid4().hex[:8].upper()}"
      return False, "Payment Declined"

class CreditCard(PaymentStrategy):
    @staticmethod
    def get_name() -> str: return "CreditCard"
    
    def pay(self, amount: float, **kwargs) -> Tuple[bool, str]:
      card_number = kwargs.get("card_number")
      cvv = kwargs.get("cvv")
      if not card_number or not cvv:
           return False, "Card Number or CVV is not Provide"
      
      success = random.random() < 0.80
      if success : return True, f"REC-{uuid.uuid4().hex[:8].upper()}"
      return False, "Payment Declined"

class Cash(PaymentStrategy):
    @staticmethod
    def get_name() -> str: return "Cash"
    
    def pay(self, amount: float, **kwargs) -> Tuple[bool, str]:
      cash_received = kwargs.get("cash_received", 0.0)
      if "cash_received" in kwargs and cash_received < amount:
           return False, "Insufficient Cash"
      return True, f"REC-{uuid.uuid4().hex[:8].upper()}"

# --- Central System ---
class Kitchen:
    def __init__(self):
        self.__order_queue: List[EventOrder] = []

    def add_order(self, order: EventOrder):
        order.status = EventOrderStatus.QUEUED
        self.__order_queue.append(order)
        print(f"[KITCHEN] Order {order.id} added to queue.")

    def get_queue(self):
        return self.__order_queue

class Restaurant:
    def __init__(self):
        self.__transaction_list: List[Transaction] = [] 
        self.__kitchen = Kitchen()
        self.__coupon_list: List[Coupon] = []
        self.__members: List[Member] = []
        self.__rooms: List[Room] = []
        self.__staff_list: List[PartyStaff] = []
        self.__booking_list: List[Booking] = []
        
        # [NEW] Initialize Strategy Instances here
        self.__payment_strategies: Dict[str, PaymentStrategy] = {
            "qrcode": QRCode(),
            "creditcard": CreditCard(),
            "cash": Cash()
        }

    @property
    def kitchen(self): return self.__kitchen
    @property
    def staff_list(self): return self.__staff_list
    @property
    def rooms(self): return self.__rooms
    @property
    def transactions(self): return self.__transaction_list

    def add_transaction(self, transaction: Transaction):
        self.__transaction_list.append(transaction)
        print(f"[SYSTEM LOG] {transaction.timestamp} | {transaction.id} | {transaction.status} | {transaction.amount} THB | Staff: {transaction.staff_id}")

    # [NEW] Get Instance from here
    def get_payment_strategy(self, strategy_name: str) -> PaymentStrategy:
        strategy = self.__payment_strategies.get(strategy_name.lower())
        if not strategy:
            raise HTTPException(status_code=400, detail=f"Unknown Strategy: {strategy_name}")
        return strategy

    def get_staff_by_id(self, staff_id: str):
        for staff in self.__staff_list:
            if staff.id == staff_id:
                return staff
        return None
    
    def add_member(self, member: Member):
        self.__members.append(member)

    def add_coupon(self, coupon: Coupon):
        self.__coupon_list.append(coupon)

    def get_coupon_by_code(self, code: str) -> Optional[Coupon]:
        for coupon in self.__coupon_list:
            if code == coupon.code:
                return coupon
        return None

    def add_booking(self, booking: Booking):
        self.__booking_list.append(booking)

    def get_booking_from_id(self, booking_id: str) -> Optional[Booking]:
      for booking in self.__booking_list:
        if booking.id == booking_id:
          return booking
      return None

# Singleton Instance
restaurant_system = Restaurant()

# --- Tools / Endpoints ---

@mcp.tool
@app.post("/partyroom-payment/calculate_booking/{booking_id}")
async def calculate_booking(booking_id: str, staff_id: str, coupon_code: Optional[str] = Query(default=None)):
    """
    คำนวณยอดเงินที่ต้องชำระสำหรับ Booking (Pre-calculation)
    
    หน้าที่:
    - ดึงข้อมูล Booking ตาม ID (Format: Bxxx)
    - ตรวจสอบสิทธิ์พนักงาน (staff_id ต้องเป็น Party Staff)
    - (Optional) ทดลองคำนวณส่วนลดถ้าใส่ coupon_code มา
    
    การทำงาน:
    ระบบจะคืนค่า JSON ที่ระบุรายละเอียดค่าห้อง, ค่าอาหาร, เงินมัดจำที่หักออก, 
    ส่วนลดที่ได้ (ถ้ามี), และยอดสุทธิ (Total Price) เพื่อให้พนักงานแจ้งลูกค้าก่อนกดจ่ายจริง
    """
    booking = restaurant_system.get_booking_from_id(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking Not Found")
    
    if booking.status != BookingStatus.PENDING:
        raise HTTPException(status_code=409, detail="Booking already paid")
    
    staff = restaurant_system.get_staff_by_id(staff_id=staff_id)
    if not staff or staff.role != StaffRole.PartyStaff:
        raise HTTPException(status_code=400, detail="Staff Not found or Not Party Staff")
    
    coupon = None
    if coupon_code:
        coupon = booking.member.get_coupon_by_code(coupon_code)
        if not coupon:
            raise HTTPException(status_code=404, detail="Coupon Not Found in Member")

    try:
        return booking.calculate_payment_details(coupon)
    except ValueError as e:
         raise HTTPException(status_code=400, detail=str(e))

@mcp.tool
@app.post("/partyroom-payment/confrim_pay/{booking_id}")
async def pay_booking(booking_id: str, staff_id: str, strategy: str, payment_details: Dict[str, Any] = {}):
    """
    ยืนยันการชำระเงินและออกใบเสร็จ (Execute Payment)

    หน้าที่:
    - ตัดเงินจริงตาม Strategy ที่เลือก (qrcode, creditcard, cash)
    - เปลี่ยนสถานะต่างๆ ในระบบเมื่อจ่ายสำเร็จ
    
    Arguments:
    - booking_id: รหัสการจอง
    - staff_id: รหัสพนักงานผู้ทำรายการ
    - strategy: วิธีการชำระเงิน ('qrcode', 'creditcard', 'cash')
    - payment_details: ข้อมูลเพิ่มเติม เช่น {'card_number': '...', 'cvv': '...'} หรือ {'cash_received': 1000}

    ผลลัพธ์เมื่อสำเร็จ:
    1. Booking Status -> PAID
    2. Event Order -> ส่งเข้า Kitchen Queue
    3. Room Status -> IN_USE
    4. Coupon -> Mark as Used (ถ้ามี)
    5. Transaction -> บันทึกลงระบบ Restaurant
    6. Receipt -> สร้างและเก็บเข้าประวัติ Member
    """
    booking = restaurant_system.get_booking_from_id(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking Not Found")
    
    if booking.status != BookingStatus.PENDING:
        raise HTTPException(status_code=409, detail="Booking already paid")
    
    staff = restaurant_system.get_staff_by_id(staff_id=staff_id)
    if not staff or staff.role != StaffRole.PartyStaff:
        raise HTTPException(status_code=400, detail="Staff Not found or Not Party Staff")
    
    if booking.total_price == 0.0 and booking.room_price > 0:
        booking.calculate_payment_details()

    try:
        payment_strategy = restaurant_system.get_payment_strategy(strategy)
    except HTTPException as e:
        raise e

    total_price = booking.total_price

    success, receipt_or_msg = payment_strategy.pay(total_price, **payment_details)

    transaction = Transaction(
        source=booking,
        strategy=strategy.lower(),
        status="PENDING",
        payment_id=receipt_or_msg,
        staff_id=staff_id
    )

    if success:
        booking.status = BookingStatus.PAID
        
        if booking.event_order:
             restaurant_system.kitchen.add_order(booking.event_order)
        
        booking.room.mark_room_in_use()
        
        member = booking.member
        if booking.coupon_used:
          if booking.coupon_used.status != CouponStatus.AVAILABLE:
              booking.calculate_payment_details() # Re-calc to remove invalid coupon
              raise HTTPException(status_code=409, detail="Coupon already used")
          booking.coupon_used.mark_as_used()

        transaction.mark_success()
        restaurant_system.add_transaction(transaction)

        receipt = Receipt(transaction, booking)
        member.add_receipt(receipt)
        
        return receipt.generate()
    else:
        transaction.mark_failed()
        restaurant_system.add_transaction(transaction)
        raise HTTPException(status_code=402, detail=f"Payment Failed: {receipt_or_msg}")

# --- MOCK DATA GENERATION ---

print("Initializing Mock Data...")

# 1. Setup Staff
staff1 = PartyStaff("ST001", "Alice Manager")
staff2 = PartyStaff("ST002", "Bob Service")
restaurant_system.staff_list.extend([staff1, staff2])

# 2. Setup Foods
f1 = Food("Chicken Bucket Large", 599.0)
f2 = Food("Spicy Wings Set", 299.0)
f3 = Food("French Fries Tower", 159.0)
f4 = Food("Coke Pitcher", 90.0)
f5 = Food("Luxury Party Platter", 1200.0)

# 3. Setup Rooms
r1 = Room("R001", RoomType.VIP)      # 2000/hr
r2 = Room("R002", RoomType.STANDARD) # 500/hr
r3 = Room("R003", RoomType.HALL)     # 5000/hr
restaurant_system.rooms.extend([r1, r2, r3])

# 4. Setup Coupons
c1 = PercentCoupon("CP001", "DISCOUNT10", 1000.0, 10.0) 
c2 = PercentCoupon("CP002", "BIGPARTY50", 5000.0, 50.0)
restaurant_system.add_coupon(c1)
restaurant_system.add_coupon(c2)

# 5. Setup Members
m1 = Member("M001", "John Doe", MemberTier.GOLD)
m1.add_coupon(c1) 

m2 = Member("M002", "Jane Smith", MemberTier.SILVER)
m2.add_coupon(c2) 

restaurant_system.add_member(m1)
restaurant_system.add_member(m2)

# 6. Setup Event Orders & Bookings
order1 = EventOrder("ORD-101")
order1.add_food(f1) 
order1.add_food(f4) 
booking1 = Booking("B001", m1, r2, datetime.now().replace(hour=18, minute=0), 3)
booking1.add_event_order(order1)
restaurant_system.add_booking(booking1)

order2 = EventOrder("ORD-102")
order2.add_food(f5) 
order2.add_food(f5) 
order2.add_food(f1) 
order2.add_food(f4) 
booking2 = Booking("B002", m2, r1, datetime.now().replace(hour=19, minute=0), 4)
booking2.add_event_order(order2)
restaurant_system.add_booking(booking2)

print("Mock Data Generated Successfully!")

if __name__ == "__main__":
    mcp.run()

## class diagram ###
"""
classDiagram
%% --- Interfaces & Abstracts ---
class Payable {
    <<interface>>
    +id: str
    +total_price: float
    +order_type: OrderType
    +coupon_used: Coupon
    +get_bill_info() Dict
}

class PaymentStrategy {
    <<abstract>>
    +get_name() str$
    +pay(amount, **kwargs) Tuple[bool, str]*
}

class Coupon {
    <<abstract>>
    -id: str
    -code: str
    -minimum_price: float
    -status: CouponStatus
    +is_applicable(base_price) bool
    +apply_coupon(base_price) float*
    +mark_as_used()
}

%% --- Core Classes ---
class Booking {
    -booking_id: str
    -start_time: datetime
    -end_time: datetime
    -hours: int
    -status: BookingStatus
    -deposit_status: str
    -room_price: float
    -required_deposit: float
    -total_price: float
    +calculate_payment_details(coupon) Dict
    +add_event_order(order)
    +get_bill_info() Dict
}

class Transaction {
    -id: str
    -target_id: str
    -amount: float
    -strategy: str
    -status: Status
    -payment_id: str
    -timestamp: datetime
    -staff_id: str
    +mark_success()
    +mark_failed()
}

class Receipt {
    +generate() Dict
}

class EventOrder {
    -id: str
    -total_price: float
    -status: EventOrderStatus
    +add_food(food)
}

class Room {
    -room_id: str
    -room_type: RoomType
    -status: RoomStatus
    -capacity: int
    -price_per_hour: float
    +mark_room_in_use()
}

class Food {
    -name: str
    -price: float
}

%% --- Users ---
class User {
    -id: str
    -name: str
    -phone: str
}

class Staff {
    -role: StaffRole
}

class PartyStaff {
}

class Customer {
}

class Member {
    -tier: MemberTier
    +add_receipt(receipt)
    +add_coupon(coupon)
    +get_coupon_by_code(code) Coupon
}

%% --- Strategies Implementation ---
class QRCode {
    +pay(amount, **kwargs)
}
class CreditCard {
    +pay(amount, **kwargs)
}
class Cash {
    +pay(amount, **kwargs)
}

%% --- Coupons Implementation ---
class PercentCoupon {
    -percent: float
    +apply_coupon(base_price) float
}

%% --- System / Central ---
class Restaurant {
    -payment_strategies: Dict
    +add_transaction(txn)
    +get_payment_strategy(name)
    +get_staff_by_id(id)
    +add_booking(booking)
    +get_booking_from_id(id)
    +kitchen: Kitchen
}

class Kitchen {
    -order_queue: List[EventOrder]
    +add_order(order)
}

%% --- Relationships ---
%% Inheritance
Payable <|-- Booking
PaymentStrategy <|-- QRCode
PaymentStrategy <|-- CreditCard
PaymentStrategy <|-- Cash
Coupon <|-- PercentCoupon

User <|-- Staff
Staff <|-- PartyStaff
User <|-- Customer
Customer <|-- Member

%% Composition / Aggregation
Restaurant "1" *-- "*" Transaction : stores
Restaurant "1" *-- "*" Booking : stores
Restaurant "1" *-- "*" Member : stores
Restaurant "1" *-- "*" Room : stores
Restaurant "1" *-- "*" PartyStaff : stores
Restaurant "1" *-- "1" Kitchen : has
Restaurant "1" o-- "*" PaymentStrategy : manages instances

Booking "1" o-- "1" Member : made by
Booking "1" o-- "1" Room : books
Booking "1" o-- "0..1" EventOrder : has
Booking "1" o-- "0..1" Coupon : uses

EventOrder "1" *-- "*" Food : contains

Transaction "1" --> "1" Payable : source (Booking)
Transaction "1" --> "0..1" Coupon : uses

Receipt "1" --> "1" Transaction : ref
Receipt "1" --> "1" Payable : source

Member "1" *-- "*" Coupon : holds
Member "1" *-- "*" Receipt : history

Kitchen o-- "*" EventOrder : queues
"""

## sequence Diagram ##
"""
sequenceDiagram
    autonumber
    participant Staff as PartyStaff
    participant API as SystemAPI
    participant Rest as Restaurant (System)
    participant Bk as Booking
    participant Mem as Member

    Note over Staff, Mem: API: /calculate_booking

    Staff->>API: calculate_booking(booking_id, staff_id, coupon_code)
    activate API

    %% 1. Retrieve Data from Central System
    API->>Rest: get_booking_from_id(booking_id)
    activate Rest
    Rest-->>API: return BookingObj
    deactivate Rest

    API->>Rest: get_staff_by_id(staff_id)
    activate Rest
    Rest-->>API: return StaffObj
    deactivate Rest

    %% 2. Coupon Handling
    opt Coupon Code Provided
        API->>Bk: member (Access Member)
        API->>Mem: get_coupon_by_code(code)
        activate Mem
        Mem-->>API: return CouponObj
        deactivate Mem
    end

    %% 3. Calculate Logic
    API->>Bk: calculate_payment_details(CouponObj)
    activate Bk
    Note right of Bk: Internal Logic:<br/>(Room + Order) - Deposit - Discount
    Bk-->>API: return PaymentDetails JSON
    deactivate Bk

    API-->>Staff: Return JSON
    deactivate API

    ###################################
    
    sequenceDiagram
    autonumber
    participant Staff as PartyStaff
    participant API as SystemAPI
    participant Rest as Restaurant (System)
    participant Kit as Kitchen
    participant Bk as Booking
    participant Strat as PaymentStrategy
    participant Txn as Transaction
    participant Rec as Receipt
    participant Mem as Member
    participant Rm as Room
    participant Cpn as Coupon

    Note over Staff, Cpn: API: /confrim_pay

    Staff->>API: pay_booking(booking_id, strategy, details)
    activate API

    %% 1. Retrievals
    API->>Rest: get_booking_from_id(booking_id)
    API->>Rest: get_staff_by_id(staff_id)

    %% 2. Strategy Execution
    API->>Rest: get_payment_strategy(strategy_name)
    activate Rest
    Rest-->>API: return StrategyInstance (Singleton)
    deactivate Rest

    API->>Strat: pay(total_price, **details)
    activate Strat
    Strat-->>API: return (Success, Msg)
    deactivate Strat

    %% 3. Transaction Creation (Using Booking as Source)
    API->>Txn: new Transaction(source=Booking, ...)
    activate Txn
    Txn-->>API: return TxnObj
    deactivate Txn

    alt Payment Success
        %% 4.1 Update Core Statuses
        API->>Bk: status = PAID
        
        %% 4.2 Send to Kitchen (via Restaurant)
        API->>Rest: kitchen
        API->>Kit: add_order(booking.event_order)
        activate Kit
        Kit-->>API: Queue Updated
        deactivate Kit

        API->>Bk: room
        API->>Rm: mark_room_in_use()
        
        %% 4.3 Handle Coupon
        opt Coupon Used
            API->>Cpn: mark_as_used()
        end

        %% 4.4 Finalize Transaction
        API->>Txn: mark_success()
        API->>Rest: add_transaction(TxnObj)

        %% 4.5 Generate Receipt
        API->>Rec: new Receipt(TxnObj, BookingObj)
        activate Rec
        Rec-->>API: return ReceiptObj
        deactivate Rec
        
        API->>Mem: add_receipt(ReceiptObj)

        API->>Rec: generate()
        activate Rec
        Rec-->>API: return Receipt JSON
        deactivate Rec

        API-->>Staff: Return Success JSON
        
    else Payment Failed
        API->>Txn: mark_failed()
        API->>Rest: add_transaction(TxnObj)
        API-->>Staff: Raise HTTP 402 (Payment Failed)
    end
    
    deactivate API
"""