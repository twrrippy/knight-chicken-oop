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

# ==========================================
# 1. ENUMS
# ==========================================
class OrderType(Enum):
    GENERAL = "General"   
    DELIVERY = "Delivery" 
    EVENT = "Event"       

class OrderStatus(Enum):
    PENDING = "Pending"
    PAID = "Paid"
    CANCELED = "Canceled"

class BookingStatus(Enum):
    PENDING = "Pending"
    DEPOSIT_PAID = "Deposit Paid" 
    CHECKED_IN = "Checked In"
    COMPLETED = "Completed"       

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

# ==========================================
# 2. UTILITIES & INTERFACES
# ==========================================
class SimulationClock:
    __current_time = datetime.now()

    @classmethod
    def set_time(cls, new_time: datetime):
        cls.__current_time = new_time

    @classmethod
    def get_time(cls):
        return cls.__current_time

# ==========================================
# 3. CORE CLASSES (User, Coupon, Transaction)
# ==========================================
class Coupon(ABC):
    def __init__(self, id, code, minimum_price) -> None:
        self.__id = id
        self.__code = code
        self.__minimum_price = minimum_price
        self.__status: CouponStatus = CouponStatus.AVAILABLE

    @property
    def minimum_price(self): return self.__minimum_price
    @property
    def status(self): return self.__status
    @property
    def code(self): return self.__code

    def is_applicable(self, base_price: float) -> bool:
        return base_price >= self.__minimum_price

    @abstractmethod
    def apply_coupon(self, base_price: float) -> float: pass

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
        raise ValueError(f"Does Not Meet Minimum Price")

class Transaction:
    def __init__(self, source: Order, strategy: str, status: str, payment_id: str, staff_id: str = "SYSTEM"):
      self.__id = f"TXN-{uuid.uuid4().hex[:12].upper()}"
      self.__source = source            
      self.__target_id = source.id      
      self.__amount = source.total_payable_amount
      self.__order_type = source.order_type 
      self.__coupon = source.coupon_used    
      
      self.__strategy = strategy
      self.__status = status
      self.__payment_id = payment_id
      self.__timestamp = SimulationClock.get_time()
      self.__staff_id = staff_id

    def mark_success(self): self.__status = "SUCCESS"
    def mark_failed(self): self.__status = "FAILED"
    
    @property
    def id(self): return self.__id
    @property
    def timestamp(self): return self.__timestamp
    @property
    def amount(self): return self.__amount
    @property
    def strategy(self): return self.__strategy
    @property
    def order_type(self): return self.__order_type
    @property
    def status(self): return self.__status

class User:
    def __init__(self, id: str, name: str):
        self.__id = id
        self.__name = name
    @property
    def id(self): return self.__id
    @property
    def name(self): return self.__name

class Staff(User):
    def __init__(self, id: str, name: str, role: StaffRole):
        super().__init__(id, name)
        self.__role = role
    @property
    def role(self): return self.__role

class PartyStaff(Staff):
    def __init__(self, id: str, name: str):
        super().__init__(id, name, role=StaffRole.PartyStaff)

class Customer(User): pass

class Receipt:
  def __init__(self, transaction: Transaction, source_object: Order):
    self.__transaction = transaction
    self.__source = source_object

  def generate(self):
    bill_info = self.__source.get_bill_info()
    return {
      "receipt_no": self.__transaction.id,
      "date": self.__transaction.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
      "merchant": "Knight Chicken Fast Food Co.",
      "order_type": self.__transaction.order_type,
      "customer": bill_info["customer_name"],
      "items": bill_info["items"],
      "subtotal": bill_info["subtotal"],
      "discount": bill_info["discount"],
      "paid_deposit": bill_info.get("paid_deposit", 0.0),
      "final_amount_due": self.__transaction.amount,
      "payment_method": self.__transaction.strategy,
      "status": self.__transaction.status
    }

class Member(Customer):
    def __init__(self, id: str, name: str, tier: MemberTier):
        super().__init__(id, name)
        self.__coupon_list: List[Coupon] = [] 
        self.__receipt_list: List[Receipt] = []
        self.__tier = tier

    def add_receipt(self, receipt: Receipt): self.__receipt_list.append(receipt)
    def add_coupon(self, coupon: Coupon): self.__coupon_list.append(coupon)
    
    def get_coupon_by_code(self, code: str):
        for coupon in self.__coupon_list:
            if coupon.code == code: return coupon
        return None
    @property
    def tier(self): return self.__tier

class Food:
    def __init__(self, name: str, price: float):
        self.__name = name
        self.__price = price
    @property
    def name(self): return self.__name
    @property
    def price(self): return self.__price

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
    
    def mark_room_in_use(self):
        self.__status = RoomStatus.IN_USE

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

# ==========================================
# 4. ORDER ITEM SYSTEM
# ==========================================
class OrderItem(ABC):
    @property
    @abstractmethod
    def name(self) -> str: pass
    
    @property
    @abstractmethod
    def price(self) -> float: pass 

    @abstractmethod
    def get_details(self) -> Dict[str, Any]: pass

class FoodOrderItem(OrderItem):
    def __init__(self, food: Food, quantity: int = 1):
        self.__food = food
        self.__quantity = quantity
    
    @property
    def name(self): return f"{self.__food.name} (x{self.__quantity})"
    @property
    def price(self): return self.__food.price * self.__quantity

    def get_details(self) -> Dict[str, Any]:
        return {"name": self.name, "quantity": self.__quantity, "price": self.price}

# [CLEANED] Booking is now a pure OrderItem (No circular logic)
class Booking(OrderItem):
    def __init__(self, booking_id, member: Member, room: Room, start_time: datetime, hours: int):
        self.__id = booking_id
        self.__member = member
        self.__room = room
        self.__start_time = start_time
        self.__hours = hours
        
        base_price = room.price_per_hour * hours
        discount_rate = 0.20 if member.tier == MemberTier.GOLD else 0.0
        self.__net_full_price = base_price * (1 - discount_rate)
        
        self.__paid_deposit = self.__net_full_price * 0.5 
        self.__status = BookingStatus.PENDING

    def mark_paid_deposit(self):
        self.__status = BookingStatus.DEPOSIT_PAID

    def mark_completed(self):
        self.__status = BookingStatus.COMPLETED
    
    def mark_checked_in(self):
        self.__status = BookingStatus.CHECKED_IN

    # --- Implement OrderItem ---
    @property
    def name(self) -> str: 
        return f"Room Balance: {self.__room.id} ({self.__hours} hrs)"
    
    @property
    def price(self) -> float: 
        # Price exposed to Order is ONLY the remaining balance
        return self.__net_full_price - self.__paid_deposit

    def get_details(self) -> Dict[str, Any]:
        return {
            "type": "Booking Balance",
            "room_id": self.__room.id,
            "room_type": self.__room.type.value,
            "hours": self.__hours,
            "full_price": self.__net_full_price,
            "deposit_paid": self.__paid_deposit,
            "amount_due": self.price 
        }

    # --- Standard Getters ---
    @property
    def id(self): return self.__id
    @property
    def full_price(self): return self.__net_full_price
    @property
    def paid_deposit(self): return self.__paid_deposit
    @property
    def status(self): return self.__status
    @property
    def room(self): return self.__room
    @property
    def hours(self): return self.__hours

# ==========================================
# 5. ORDER SYSTEM
# ==========================================
class Order(ABC):
    def __init__(self, order_id: str, customer: Member):
        self._id = order_id
        self._customer = customer
        self._items: List[OrderItem] = []
        self._status = OrderStatus.PENDING
        self._coupon_used: Optional[Coupon] = None
        
        self._subtotal = 0.0
        self._discount = 0.0
        self._final_price = 0.0
        self._deposit_deducted = 0.0

    def add_item(self, item: OrderItem):
        self._items.append(item)

    @property
    @abstractmethod
    def order_type(self) -> OrderType: pass

    def calculate_totals(self, coupon: Optional[Coupon] = None):
        # 1. Sum up all items (Booking Balance + Food)
        self._subtotal = sum(item.price for item in self._items)
        
        # 2. Track Deposit (For info only, already deducted in Booking.price)
        self._deposit_deducted = 0.0
        for item in self._items:
            if isinstance(item, Booking):
                self._deposit_deducted += item.paid_deposit

        # 3. Apply Coupon
        self._discount = 0.0
        if coupon:
             if coupon.status != CouponStatus.AVAILABLE:
                raise ValueError("Coupon Not Available")
             self._discount = coupon.apply_coupon(self._subtotal)
             self._coupon_used = coupon
        else:
             self._coupon_used = None

        self._final_price = self._subtotal - self._discount
        if self._final_price < 0: self._final_price = 0.0
        
        # 4. Construct Return JSON
        return {
            "Member": {
                "Name": self._customer.name,
                "Tier": self._customer.tier.value
            },
            "Order Id": self._id,
            "Item": [item.get_details() for item in self._items],
            "Total Price Before Discount": self._subtotal,
            "Coupon Code": coupon.code if coupon else "None",
            "Discounted": self._discount,
            "Deposit Already Paid": self._deposit_deducted,
            "Total Payable": self._final_price
        }

    @property
    def id(self): return self._id
    @property
    def total_payable_amount(self): return self._final_price
    @property
    def coupon_used(self): return self._coupon_used
    @property
    def items(self): return self._items
    @property
    def customer(self): return self._customer
    @property
    def status(self): return self._status
    @status.setter
    def status(self, val): self._status = val

    def get_bill_info(self) -> Dict[str, Any]:
        return {
            "customer_name": self._customer.name,
            "items": [item.get_details() for item in self._items],
            "subtotal": self._subtotal,
            "discount": self._discount,
            "paid_deposit": self._deposit_deducted
        }

# --- Specific Orders ---
class GeneralOrder(Order):
    @property
    def order_type(self): return OrderType.GENERAL # pyright: ignore[reportIncompatibleMethodOverride]

class EventOrder(Order):
    """ Booking + Food """
    @property
    def order_type(self): return OrderType.EVENT # pyright: ignore[reportIncompatibleMethodOverride]
    
    @property
    def linked_booking(self) -> Optional[Booking]:
        for item in self.items:
            if isinstance(item, Booking):
                return item
        return None
    
    def add_booking_item(self, booking: Booking):
        if booking.status != BookingStatus.DEPOSIT_PAID:
            raise ValueError("Booking deposit must be paid first")
        if self.linked_booking:
             raise ValueError("Order already has a booking")
        self.add_item(booking)

class DeliveryOrder(Order):
    """ Order สำหรับเดลิเวอรี่ (เพิ่มใหม่) """
    def __init__(self, order_id: str, customer: Member, delivery_address: str, rider_fee: float = 0.0):
        super().__init__(order_id, customer)
        self.__delivery_address = delivery_address
        self.__rider_fee = rider_fee # ค่าส่ง

    @property
    def order_type(self): return OrderType.DELIVERY
    
    @property
    def delivery_address(self): return self.__delivery_address

    def calculate_totals(self, coupon: Optional[Coupon] = None):
        base_result = super().calculate_totals(coupon)
        
        # บวกค่าส่งเข้าไปใน final price
        self._final_price += self.__rider_fee
        
        # Update result dict
        base_result["Rider Fee"] = self.__rider_fee
        base_result["Total Payable"] = self._final_price
        return base_result
    
    def get_bill_info(self) -> Dict[str, Any]:
        info = super().get_bill_info()
        info['items'].append({"name": "Delivery Fee", "quantity": 1, "price": self.__rider_fee})
        info['subtotal'] += self.__rider_fee 
        return info

# ==========================================
# 6. PAYMENT STRATEGIES
# ==========================================
class PaymentStrategy(ABC):
    def __init__(self, id: str, name: str):
        self.__id = id
        self.__name = name

    @property
    def name(self): return self.__name

    @abstractmethod
    def pay(self, amount: float, **kwargs) -> Tuple[bool, str, str]: pass

class QRCode(PaymentStrategy):
    def __init__(self, id: str, name: str): super().__init__(id, name)
    
    def pay(self, amount: float, **kwargs) -> Tuple[bool, str, str]:
        txn_id = f"Txn-{uuid.uuid4().hex[:8].upper()}"
        account_number = kwargs.get("account_number")
        if not account_number: return False, txn_id, "Missing 'account_number'"
        
        success = random.random() < 0.90
        return (True, txn_id, "Payment Done") if success else (False, txn_id, "Bank System Offline")

class CreditCard(PaymentStrategy):
    def __init__(self, id: str, name: str): super().__init__(id, name)
    
    def pay(self, amount: float, **kwargs) -> Tuple[bool, str, str]:
        txn_id = f"Txn-{uuid.uuid4().hex[:8].upper()}"
        if not kwargs.get("card_number") or not kwargs.get("cvv"): 
            return False, txn_id, "Missing Card Details"
            
        success = random.random() < 0.80
        return (True, txn_id, "Payment Done") if success else (False, txn_id, "Card Declined")

class Cash(PaymentStrategy):
    def __init__(self, id: str, name: str): super().__init__(id, name)
    
    def pay(self, amount: float, **kwargs) -> Tuple[bool, str, str]:
        txn_id = f"Txn-{uuid.uuid4().hex[:8].upper()}"
        received = kwargs.get("cash_received")
        if received is None: return False, txn_id, "Missing 'cash_received'"
        
        if float(received) < amount: return False, txn_id, f"Insufficient Cash"
        return True, txn_id, "Payment Done"

# ==========================================
# 7. CENTRAL SYSTEM
# ==========================================
class Kitchen:
    def __init__(self):
        self.__order_queue: List[Order] = []

    def add_order(self, order: Order):
        # Only add if has food
        has_food = any(isinstance(item, FoodOrderItem) for item in order.items)
        if has_food:
            self.__order_queue.append(order)
            print(f"[KITCHEN] Order {order.id} received. Preparing...")

class Restaurant:
    def __init__(self):
        self.__transaction_list: List[Transaction] = [] 
        self.__coupon_list: List[Coupon] = []
        self.__members: List[Member] = []
        self.__staff_list: List[Staff] = []
        self.__kitchen = Kitchen()
        
        self.__bookings: List[Booking] = []  
        self.__orders: List[Order] = []      
        self.__payment_strategies: List[PaymentStrategy] = []

    # Getters
    @property
    def kitchen(self): return self.__kitchen

    # --- Booking Mgmt ---
    def add_booking(self, booking: Booking): self.__bookings.append(booking)
    def get_booking(self, booking_id: str) -> Optional[Booking]:
        for b in self.__bookings:
            if b.id == booking_id: return b
        return None

    # --- Order Mgmt ---
    def add_order(self, order: Order): self.__orders.append(order)
    def get_order(self, order_id: str) -> Optional[Order]:
        for o in self.__orders:
            if o.id == order_id: return o
        return None

    # --- Strategy Mgmt ---
    def add_payment_strategy(self, strategy: PaymentStrategy): self.__payment_strategies.append(strategy)
    def get_payment_strategy(self, strategy_name: str) -> PaymentStrategy:
        for s in self.__payment_strategies:
            if s.name.lower() == strategy_name.lower(): return s
        raise HTTPException(status_code=400, detail="Unknown Strategy")

    # --- Others ---
    def add_transaction(self, t: Transaction): 
        self.__transaction_list.append(t)
        print(f"[LOG] Txn: {t.id} | Status: {t.status} | Amt: {t.amount}")

    def add_member(self, m: Member): self.__members.append(m)
    def add_coupon(self, c: Coupon): self.__coupon_list.append(c)
    def add_staff(self, s: Staff): self.__staff_list.append(s)

    def get_coupon(self, code: str) -> Optional[Coupon]: 
        for c in self.__coupon_list: 
            if c.code == code: return c
        return None
    
    def get_staff(self, id: str) -> Optional[Staff]:
        for s in self.__staff_list:
            if s.id == id: return s
        return None

    def get_member(self, id: str) -> Optional[Member]:
        for m in self.__members:
            if m.id == id: return m
        return None

restaurant_system = Restaurant()

# ==========================================
# 8. API ENDPOINTS
# ==========================================

@mcp.tool
@app.post("/payment/calculate_order/{order_id}")
async def calculate_order(order_id: str, staff_id: str, coupon_code: Optional[str] = Query(default=None)):
    """
    คำนวณยอดเงินที่ต้องชำระสำหรับ Order (Pre-calculation)
    
    หน้าที่:
    - ดึงข้อมูล Order ตาม ID (Format: ORD-xxx-xxx)
    - ตรวจสอบสิทธิ์พนักงาน (staff_id)
    - (Optional) ทดลองคำนวณส่วนลดถ้าใส่ coupon_code มา
    
    การทำงาน:
    ระบบจะคืนค่า JSON ที่ระบุรายละเอียด Order ทั้งหมด, 
    ส่วนลดที่ได้ (ถ้ามี), และยอดสุทธิ (Total Price) เพื่อให้พนักงานแจ้งลูกค้าก่อนกดจ่ายจริง
    หากยังไม่ได้ใช้คูปอง สามารถเรียกฟังก์ชั่นเดิมเพื่อใส่ หรือไม่ใส่คูปองใหม่ได้
    """
    order = restaurant_system.get_order(order_id)
    if not order: raise HTTPException(404, "Order Not Found")
    if order.status == OrderStatus.PAID: raise HTTPException(409, "Already Paid")
    
    staff = restaurant_system.get_staff(staff_id)
    if not staff: 
        raise HTTPException(400, "Invalid Staff")
    if order.order_type == OrderType.EVENT and staff.role != StaffRole.PartyStaff:
        raise HTTPException(400, "Invalid Staff Role")
    
    coupon = None
    if coupon_code:
        coupon = restaurant_system.get_coupon(coupon_code)
        if not coupon: raise HTTPException(404, "Coupon Not Found")

    try:
        return order.calculate_totals(coupon)
    except ValueError as e:
         raise HTTPException(400, str(e))

@mcp.tool
@app.post("/payment/confirm_pay/{order_id}")
async def confirm_pay(order_id: str, staff_id: str, strategy: str, payment_details: Dict[str, Any] = {}):
    """
    ยืนยันการชำระเงินและออกใบเสร็จ (Execute Payment)

    หน้าที่:
    - ตัดเงินจริงตาม Strategy ที่เลือก (qrcode, creditcard, cash)
    - เปลี่ยนสถานะต่างๆ ในระบบเมื่อจ่ายสำเร็จ
    
    Arguments:
    - booking_id: รหัสการจอง
    - staff_id: รหัสพนักงานผู้ทำรายการ
    - strategy: วิธีการชำระเงิน ('qrcode', 'creditcard', 'cash')
    - payment_details: ข้อมูลเพิ่มเติม เช่น {'account_number': xxx } หรือ {'card_number': '...', 'cvv': '...'} หรือ {'cash_received': xxx}

    ผลลัพธ์เมื่อสำเร็จ:
    1. Status -> PAID
    2. Order -> ส่งเข้า Kitchen Queue
    3. Coupon -> Mark as Used (ถ้ามี)
    4. Transaction -> บันทึกลงระบบ Restaurant
    5. Receipt -> สร้างและเก็บ
    """

    # 1. Validation
    order = restaurant_system.get_order(order_id)
    if not order: raise HTTPException(404, "Order Not Found")
    if order.status == OrderStatus.PAID: raise HTTPException(409, "Already Paid")

    staff = restaurant_system.get_staff(staff_id)
    if not staff: raise HTTPException(400, "Invalid Staff")

    if order.coupon_used and order.coupon_used.status != CouponStatus.AVAILABLE:
        raise HTTPException(400, "Coupon is Already Used")
    
    # 2. Ensure price is calculated
    if order.total_payable_amount == 0.0:
        order.calculate_totals(coupon=None)

    # 3. Process Payment
    try:
        pay_strategy = restaurant_system.get_payment_strategy(strategy)
    except HTTPException as e: raise e

    success, txn_id, note = pay_strategy.pay(order.total_payable_amount, **payment_details)

    transaction = Transaction(source=order, strategy=strategy, status="PENDING", payment_id=txn_id, staff_id=staff_id)

    if success:
        # Success Update
        order.status = OrderStatus.PAID
        transaction.mark_success()
        
        # 1. Update Booking & Room
        if isinstance(order, EventOrder) and order.linked_booking:
            order.linked_booking.mark_checked_in()
            order.linked_booking.room.mark_room_in_use()

        # 2. Send to Kitchen
        restaurant_system.kitchen.add_order(order)

        # 3. Mark Coupon
        if order.coupon_used: order.coupon_used.mark_as_used()
        
        # 4. Save
        restaurant_system.add_transaction(transaction)
        receipt = Receipt(transaction, order)
        order.customer.add_receipt(receipt)
        
        return receipt.generate()
    else:
        # Failure Update
        transaction.mark_failed()
        restaurant_system.add_transaction(transaction)
        raise HTTPException(402, f"Payment Failed: {note}")

# ==========================================
#             MOCK DATA SETUP
# ==========================================
print("Initializing Extended Mock Data...")

# ------------------------------------------
# 1. SETUP SYSTEM & STRATEGIES
# ------------------------------------------
# Clear lists if running repeatedly (optional)
# restaurant_system = Restaurant() 

restaurant_system.add_payment_strategy(QRCode("S1", "QRCode (PromptPay)"))
restaurant_system.add_payment_strategy(CreditCard("S2", "CreditCard (Visa/Master)"))
restaurant_system.add_payment_strategy(Cash("S3", "Cash"))

# ------------------------------------------
# 2. STAFF & MEMBERS (Covering all Tiers)
# ------------------------------------------
# Staff
admin = PartyStaff("ST-ADMIN", "Admin Staff")
chef = Staff("ST-CHEF", "Gordon", StaffRole.KitchenStaff)
waiter = PartyStaff("ST-WAITER", "Peter")

restaurant_system.add_staff(admin)
restaurant_system.add_staff(chef)
restaurant_system.add_staff(waiter)

# Members
m_gold = Member("M-001", "เสี่ยตง (Gold)", MemberTier.GOLD)      # ส่วนลดห้อง 20%
m_silver = Member("M-002", "คุณหญิง (Silver)", MemberTier.SILVER) # (สมมติในอนาคตมีส่วนลด)
m_bronze = Member("M-003", "นายเอ (Bronze)", MemberTier.BRONZE)   # ลูกค้าทั่วไป
m_new = Member("M-004", "น้องบี (New)", MemberTier.BRONZE)

restaurant_system.add_member(m_gold)
restaurant_system.add_member(m_silver)
restaurant_system.add_member(m_bronze)
restaurant_system.add_member(m_new)

# ------------------------------------------
# 3. FOOD MENU
# ------------------------------------------
menu = [
    Food("French Fries", 89.0),
    Food("Coke Refill", 49.0),
    Food("Wagyu Steak", 1299.0),
    Food("Spaghetti Carbonara", 250.0),
    Food("Party Set L (Chicken + Pizza)", 899.0),
    Food("Ice Cream Tower", 399.0)
]
# Helper dict to find food easily
food_map = {f.name: f for f in menu}

# ------------------------------------------
# 4. COUPONS
# ------------------------------------------
c1 = PercentCoupon("CPN-10", "WELCOME10", 0, 10.0)      # ลด 10% ไม่มีขั้นต่ำ
c2 = PercentCoupon("CPN-20", "VIP20", 1000, 20.0)       # ลด 20% ขั้นต่ำ 1000
c3 = PercentCoupon("CPN-50", "BIGLOT50", 5000, 50.0)    # ลด 50% ขั้นต่ำ 5000 (สำหรับจัดเลี้ยง)

restaurant_system.add_coupon(c1)
restaurant_system.add_coupon(c2)
restaurant_system.add_coupon(c3)

m_gold.add_coupon(c1)
m_silver.add_coupon(c2)
m_bronze.add_coupon(c3)
m_new.add_coupon(c2)

# ------------------------------------------
# 5. ROOMS & BOOKINGS
# ------------------------------------------
# Create Rooms
r_vip = Room("R-VIP-01", RoomType.VIP)      # 2000/hr
r_std = Room("R-STD-01", RoomType.STANDARD) # 500/hr
r_hall = Room("R-HALL-01", RoomType.HALL)   # 5000/hr

# --- Scenario A: Booking ที่จ่ายมัดจำแล้ว (พร้อมเข้าใช้) ---
b_vip = Booking("BK-VIP", m_gold, r_vip, datetime.now(), 5) # 5 ชม.
# Gold Member ได้ลดค่าห้อง 20% -> (2000*5)*0.8 = 8000
b_vip.mark_paid_deposit() # จ่ายมัดจำ 4000
restaurant_system.add_booking(b_vip)

# --- Scenario B: Booking จอง Hall ใหญ่ (ยังไม่จ่ายมัดจำ) ---
# อันนี้จะยังเอาไปทำ Order ไม่ได้ จนกว่าจะจ่ายมัดจำ
b_hall = Booking("BK-HALL", m_silver, r_hall, datetime.now() + timedelta(days=1), 4)
restaurant_system.add_booking(b_hall)

# ------------------------------------------
# 6. ORDERS (The Core Scenarios)
# ------------------------------------------

# === CASE 1: General Order (ทานข้าวปกติ ไม่จองห้อง) ===
# ลูกค้า: m_bronze
# สั่ง: สเต็ก และ โค้ก
gen_order = GeneralOrder("ORD-GEN-001", m_bronze)
gen_order.add_item(FoodOrderItem(food_map["Wagyu Steak"], 1))
gen_order.add_item(FoodOrderItem(food_map["Coke Refill"], 2))
restaurant_system.add_order(gen_order)


# === CASE 2: Event Order (จัดเลี้ยงในห้อง VIP) ===
# ลูกค้า: m_gold (จาก b_vip ด้านบน)
# สั่ง: ห้อง VIP + ชุด Party Set
evt_order = EventOrder("ORD-EVT-001", m_gold)

# Link Booking (ระบบจะดึงยอดที่เหลือหลังหักมัดจำมาคำนวณ)
evt_order.add_booking_item(b_vip) 

# สั่งอาหารเข้าห้อง
evt_order.add_item(FoodOrderItem(food_map["Party Set L (Chicken + Pizza)"], 2))
evt_order.add_item(FoodOrderItem(food_map["Ice Cream Tower"], 1))
restaurant_system.add_order(evt_order)


# === CASE 3: Delivery Order (สั่งกลับบ้าน) ===
# ลูกค้า: m_new
# สั่ง: เฟรนช์ฟรายส์ + สปาเก็ตตี้
# ค่าส่ง: 50 บาท
del_order = DeliveryOrder("ORD-DEL-001", m_new, "123 Condo A, Bangkok", rider_fee=50.0)
del_order.add_item(FoodOrderItem(food_map["French Fries"], 1))
del_order.add_item(FoodOrderItem(food_map["Spaghetti Carbonara"], 1))
restaurant_system.add_order(del_order)


# === CASE 4: Order ที่จ่ายเงินแล้ว (Paid History) ===
# จำลองว่า Order นี้ทำรายการเสร็จสิ้นแล้ว เพื่อดูประวัติ
paid_order = GeneralOrder("ORD-PAID-999", m_silver)
paid_order.add_item(FoodOrderItem(food_map["Coke Refill"], 1))
paid_order.calculate_totals() # คำนวณราคาก่อน
paid_order.status = OrderStatus.PAID

# สร้าง Transaction ย้อนหลังเก็บไว้
txn = Transaction(paid_order, "QRCode", "SUCCESS", "TXN-MOCK-OLD", "ST-WAITER")
txn.mark_success()
restaurant_system.add_transaction(txn)
restaurant_system.add_order(paid_order)

print("System Ready! Data Loaded:")

if __name__ == "__main__":
    mcp.run()