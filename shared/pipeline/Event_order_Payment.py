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

class TransactionStatus(Enum):
    PENDING = "PENDING"
    FAILED = "FAILED"
    SUCCESS = "SUCCESS"

class SimulationClock:
    __current_time = datetime.now()

    @classmethod
    def set_time(cls, new_time: datetime):
        cls.__current_time = new_time

    @classmethod
    def get_time(cls):
        return cls.__current_time

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

class FixedAmountCoupon(Coupon):
    def __init__(self, id: str, code: str, minimum_price: float, amount: float) -> None:
        super().__init__(id, code, minimum_price)
        if amount > minimum_price:
            raise ValueError("Minimum Price must be >= Amount")
        self.__amount = amount

    def apply_coupon(self, base_price: float) -> float:
        if self.is_applicable(base_price):
            return self.__amount
        raise ValueError(f"Does Not Meet Minimum Price")

class Transaction:
    def __init__(self, order: Order, strategy: PaymentStrategy, status: TransactionStatus, payment_id: str):
      self.__id = f"TXN-{uuid.uuid4().hex[:12].upper()}"
      self.__order = order                 
      self.__amount = order.total_payable_amount
      self.__order_type = order.order_type 
      self.__coupon = order.coupon_used    
      
      self.__strategy = strategy
      self.__status = status
      self.__payment_id = payment_id
      self.__timestamp = SimulationClock.get_time()

    def mark_success(self): self.__status = TransactionStatus.SUCCESS
    def mark_failed(self): self.__status = TransactionStatus.FAILED
    
    @property
    def order(self): return self.__order
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
      "order_type": self.__transaction.order_type.name,
      "customer": bill_info["customer_name"],
      "items": bill_info["items"],
      "booking": bill_info["booking"] if isinstance(self.__source, EventOrder) else "None",
      "subtotal": bill_info["subtotal"],
      "discount": bill_info["discount"],
      "paid_deposit": bill_info.get("paid_deposit", 0.0),
      "final_amount_due": self.__transaction.amount,
      "payment_method": self.__transaction.strategy.name,
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


class FoodOrderItem:
    def __init__(self, food: Food, quantity: int = 1):
        self.__food = food
        self.__quantity = quantity
    
    @property
    def name(self): return f"{self.__food.name} (x{self.__quantity})"
    @property
    def price(self): return self.__food.price * self.__quantity

    def get_details(self) -> Dict[str, Any]:
        return {"name": self.name, "quantity": self.__quantity, "price": self.price}

class Booking:
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

    @property
    def name(self) -> str: 
        return f"Room Balance: {self.__room.id} ({self.__hours} hrs)"
    
    @property
    def price(self) -> float: 
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

class Order(ABC):
    def __init__(self, order_id: str, customer: Customer):
        self._id = order_id
        self._customer: Customer = customer
        self._items: List[FoodOrderItem] = []
        self._status = OrderStatus.PENDING
        self._coupon_used: Optional[Coupon] = None
        
        self._subtotal = 0.0
        self._discount = 0.0
        self._final_price = 0.0

    def add_item(self, item: FoodOrderItem):
        self._items.append(item)

    @property
    @abstractmethod
    def order_type(self) -> OrderType: pass

    def pre_calculate_totals(self, coupon: Optional[Coupon] = None):
        subtotal = sum(item.price for item in self._items)

        discount = 0.0
        if coupon:
             if coupon.status != CouponStatus.AVAILABLE:
                raise ValueError("Coupon Not Available")
             discount = coupon.apply_coupon(subtotal)

        final_price = subtotal - discount
        if final_price < 0: final_price = 0.0
        
        return {
            "Member": {
                "Customer ID": self._customer.id,
                "Name": self._customer.name
            },
            "Order Id": self._id,
            "Item": [item.get_details() for item in self._items],
            "Total Price Before Discount": subtotal,
            "Coupon Code": coupon.code if coupon else "None",
            "Discounted": discount,
            "Total Payable": final_price
        }

    def calculate_totals(self, coupon: Optional[Coupon] = None):
        info = self.pre_calculate_totals(coupon)
        self._subtotal = info.get("Total Price Before Discount")
        self._discount = info.get("Discounted")
        self._final_price = info.get("Total Payable")
        if info.get("Coupon Code") != "None":
            self._coupon_used = coupon
    
        return info

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
            "discount": self._discount
        }

class GeneralOrder(Order):
    @property
    def order_type(self): return OrderType.GENERAL # pyright: ignore[reportIncompatibleMethodOverride]

class EventOrder(Order):
    """ Booking + Food """
    def __init__(self, order_id: str, customer: Member, booking: Booking):
        super().__init__(order_id, customer)
        self.__booking: Booking = booking

    @property
    def order_type(self): return OrderType.EVENT # pyright: ignore[reportIncompatibleMethodOverride]
    
    @property
    def booking(self) -> Booking: return self.__booking

    def pre_calculate_totals(self, coupon: Optional[Coupon] = None): # type: ignore
        subtotal = sum(item.price for item in self._items) + self.booking.full_price
        paid_deposit = self.booking.paid_deposit

        discount = 0.0
        if coupon:
             if coupon.status != CouponStatus.AVAILABLE:
                raise ValueError("Coupon Not Available")
             discount = coupon.apply_coupon(subtotal)

        final_price = subtotal - discount - paid_deposit
        if final_price < 0: final_price = 0.0
        
        return {
            "Member": {
                "Customer ID": self._customer.id,
                "Name": self._customer.name
            },
            "Order Id": self._id,
            "Item": [item.get_details() for item in self._items],
            "Booking": self.booking.get_details(),
            "Total Price Before Discount": subtotal,
            "Coupon Code": coupon.code if coupon else "None",
            "Discounted": discount,
            "Deposit Already Paid" : paid_deposit,
            "Total Payable": final_price
        }

    def get_bill_info(self) -> Dict[str, Any]:
        return {
            "customer_name": self._customer.name,
            "items": [item.get_details() for item in self._items],
            "booking": self.booking.get_details(),
            "subtotal": self._subtotal,
            "discount": self._discount,
            "paid_deposit": self.booking.paid_deposit
        }

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

    def pre_calculate_totals(self, coupon: Coupon | None = None): # type: ignore
        base_result = super().pre_calculate_totals(coupon)
        base_result["Rider Fee"] = self.__rider_fee
        base_result["Total Payable"] += self.__rider_fee

        return base_result
    
    def get_bill_info(self) -> Dict[str, Any]:
        info = super().get_bill_info()
        info['items'].append({"name": "Delivery Fee", "quantity": 1, "price": self.__rider_fee})
        info['subtotal'] += self.__rider_fee 
        return info
    
class PaymentStrategy(ABC):
    def __init__(self, id: str, name: str):
        self.__id = id
        self.__name = name

    @property
    @abstractmethod
    def name(self) -> str: pass

    @abstractmethod
    def pay(self, amount: float, **kwargs) -> Tuple[bool, str, str]: pass

class QRCode(PaymentStrategy):
    def __init__(self, id: str, name: str): super().__init__(id, name)

    @property
    def name(self): return "qrcode"
    
    def pay(self, amount: float, **kwargs) -> Tuple[bool, str, str]:
        txn_id = f"Txn-{uuid.uuid4().hex[:8].upper()}"
        account_number = kwargs.get("account_number")
        if not account_number: return False, txn_id, "Missing 'account_number'"
        
        success = random.random() < 0.90
        return (True, txn_id, "Payment Done") if success else (False, txn_id, "Bank System Offline")

class CreditCard(PaymentStrategy):
    def __init__(self, id: str, name: str): super().__init__(id, name)
    
    @property
    def name(self): return "creditcard"

    def pay(self, amount: float, **kwargs) -> Tuple[bool, str, str]:
        txn_id = f"Txn-{uuid.uuid4().hex[:8].upper()}"
        if not kwargs.get("card_number") or not kwargs.get("cvv"): 
            return False, txn_id, "Missing Card Details"
            
        success = random.random() < 0.80
        return (True, txn_id, "Payment Done") if success else (False, txn_id, "Card Declined")

class Cash(PaymentStrategy):
    def __init__(self, id: str, name: str): super().__init__(id, name)

    @property
    def name(self): return "cash"
    
    def pay(self, amount: float, **kwargs) -> Tuple[bool, str, str]:
        txn_id = f"Txn-{uuid.uuid4().hex[:8].upper()}"
        received = kwargs.get("cash_received")
        if received is None: return False, txn_id, "Missing 'cash_received'"
        
        if float(received) < amount: return False, txn_id, f"Insufficient Cash"
        return True, txn_id, "Payment Done"

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

    @property
    def kitchen(self): return self.__kitchen

    def add_booking(self, booking: Booking): self.__bookings.append(booking)
    def get_booking(self, booking_id: str) -> Optional[Booking]:
        for b in self.__bookings:
            if b.id == booking_id: return b
        return None

    def add_order(self, order: Order): self.__orders.append(order)
    def get_order(self, order_id: str) -> Optional[Order]:
        for o in self.__orders:
            if o.id == order_id: return o
        return None

    def add_payment_strategy(self, strategy: PaymentStrategy): self.__payment_strategies.append(strategy)
    def get_payment_strategy(self, strategy_name: str) -> PaymentStrategy:
        for s in self.__payment_strategies:
            if s.name.lower() == strategy_name.lower(): return s
        raise HTTPException(status_code=400, detail="Unknown Strategy")

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

## API

@mcp.tool
@app.post("/payment/calculate_order/{order_id}")
async def calculate_order(order_id: str, staff_id: str, coupon_code: Optional[str] = Query(default=None)):
    """
    คำนวณยอดเงินที่ต้องชำระสำหรับ Order (Pre-calculation / Preview)
    
    หน้าที่:
    - ดึงข้อมูล Order ตาม ID (Format: ORD-xxx-xxx)
    - ตรวจสอบสิทธิ์พนักงาน (staff_id) ว่าสามารถเข้าถึงประเภท Order นั้นๆ ได้หรือไม่
    - (Optional) ทดลองคำนวณส่วนลดถ้าใส่ coupon_code มา เพื่อดูยอดก่อนจ่ายจริง
    
    การทำงาน:
    - ระบบจะคืนค่า JSON สรุปรายละเอียดออเดอร์ทั้งหมด (รายการอาหาร, รายละเอียดการจองห้อง, ค่าส่ง ฯลฯ)
    - แสดงยอดรวมก่อนลด, ส่วนลดจากคูปอง, เงินมัดจำที่หักออก (ถ้ามี), และยอดสุทธิ (Total Payable) เพื่อให้พนักงานแจ้งลูกค้า
    - ฟังก์ชันนี้เป็นแบบ Stateless จะยังไม่บันทึกการใช้คูปองหรือเปลี่ยนแปลงสถานะใดๆ จนกว่าจะเรียก /confirm_pay
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
        if isinstance(order.customer, Member):
            coupon = order.customer.get_coupon_by_code(coupon_code)
        else:
            raise HTTPException(409, "Only members can use coupons")
        if not coupon: raise HTTPException(404, "Coupon Not Found")

    try:
        return order.pre_calculate_totals(coupon)
    except ValueError as e:
         raise HTTPException(400, str(e))

@mcp.tool
@app.post("/payment/confirm_pay/{order_id}")
async def confirm_pay(order_id: str, staff_id: str, strategy: str, coupon_code: Optional[str] = Query(default=None), payment_details: Dict[str, Any] = {}):
    """
    ยืนยันการชำระเงิน คำนวณยอดสุดท้าย และออกใบเสร็จ (Execute Payment)

    หน้าที่:
    - ยืนยันยอดชำระสุทธิและตัดเงินจริงตาม Payment Strategy ที่เลือก
    - อัปเดตสถานะของออบเจ็กต์ต่างๆ ที่เกี่ยวข้องในระบบเมื่อชำระเงินสำเร็จ
    
    Arguments:
    - order_id: รหัสออเดอร์ (Format: ORD-xxx-xxx)
    - staff_id: รหัสพนักงานผู้ทำรายการ
    - strategy: วิธีการชำระเงิน (เช่น "qrcode", "creditcard", "cash")
    - coupon_code: (Optional) โค้ดคูปองที่ต้องการใช้งาน
    - payment_details: ข้อมูลเพิ่มเติมตามประเภทการจ่ายเงิน เช่น 
        - qrcode: {"account_number": "xxx" } 
        - creditcard: {"card_number": "...", "cvv": "..."} 
        - cash: {"cash_received": xxx}

    ผลลัพธ์เมื่อทำรายการสำเร็จ:
    1. Order -> เปลี่ยนสถานะเป็น PAID
    2. Transaction -> บันทึกประวัติและเปลี่ยนสถานะเป็น SUCCESS
    3. Booking & Room -> หากเป็น EventOrder จะเปลี่ยนสถานะจองเป็น CHECKED_IN และห้องเป็น IN_USE
    4. Kitchen -> ส่งรายการอาหารเข้าคิวห้องครัว
    5. Coupon -> ถูกมาร์คว่าใช้งานแล้ว (NOT_AVAILABLE)
    6. Receipt -> สร้างใบเสร็จ เก็บลงประวัติลูกค้า และคืนค่า JSON ให้ Frontend
    """

    order = restaurant_system.get_order(order_id)
    if not order: raise HTTPException(404, "Order Not Found")
    if order.status == OrderStatus.PAID: raise HTTPException(409, "Already Paid")

    staff = restaurant_system.get_staff(staff_id)
    if not staff: raise HTTPException(400, "Invalid Staff")

    coupon = None
    if coupon_code:
        if isinstance(order.customer, Member):
            coupon = order.customer.get_coupon_by_code(coupon_code)
        else:
            raise HTTPException(409, "Only members can use coupons")
        if not coupon: raise HTTPException(404, "Coupon Not Found")

    if coupon and coupon.status != CouponStatus.AVAILABLE:
        raise HTTPException(400, "Coupon is Already Used")
    
    order.calculate_totals(coupon)
    if not isinstance(order.total_payable_amount, float): raise  HTTPException(409, "Can't Calculate Final Price")
    if order.total_payable_amount < 0: raise  HTTPException(409, "Final Price is Below 0")

    try:
        pay_strategy = restaurant_system.get_payment_strategy(strategy)
    except HTTPException as e: raise e

    success, txn_id, note = pay_strategy.pay(order.total_payable_amount, **payment_details)
    
    if order.total_payable_amount == 0: success = True

    transaction = Transaction(order=order, strategy=pay_strategy, status=TransactionStatus.PENDING, payment_id=txn_id)

    if success:
        order.status = OrderStatus.PAID
        transaction.mark_success()
        
        if isinstance(order, EventOrder) and order.booking:
            order.booking.mark_checked_in()
            order.booking.room.mark_room_in_use()

        restaurant_system.kitchen.add_order(order)

        if coupon: coupon.mark_as_used()
        
        restaurant_system.add_transaction(transaction)
        receipt = Receipt(transaction, order)

        if isinstance(order.customer, Member):
            order.customer.add_receipt(receipt)
        
        return receipt.generate()
    else:
        transaction.mark_failed()
        restaurant_system.add_transaction(transaction)
        raise HTTPException(402, f"Payment Failed: {note}")

# ==========================================
#             MOCK DATA SETUP
# ==========================================
print("Initializing Comprehensive Mock Data...")

# ------------------------------------------
# 1. SETUP SYSTEM & STRATEGIES
# ------------------------------------------
qr_code_system = QRCode("S1", "QRCode (PromptPay)")
credit_card_system = CreditCard("S2", "CreditCard (Visa/Master)")
cash_system = Cash("S3", "Cash")

restaurant_system.add_payment_strategy(qr_code_system)
restaurant_system.add_payment_strategy(credit_card_system)
restaurant_system.add_payment_strategy(cash_system)

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
m_silver = Member("M-002", "คุณหญิง (Silver)", MemberTier.SILVER)
m_bronze = Member("M-003", "นายเอ (Bronze)", MemberTier.BRONZE)
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
c1 = PercentCoupon("CPN-10", "WELCOME10", 0, 10.0)           # ลด 10% ไม่มีขั้นต่ำ
c2 = PercentCoupon("CPN-20", "VIP20", 1000, 20.0)            # ลด 20% ขั้นต่ำ 1000
c3 = PercentCoupon("CPN-50", "BIGLOT50", 5000, 50.0)         # ลด 50% ขั้นต่ำ 5000 (สำหรับจัดเลี้ยง)
c4 = FixedAmountCoupon("CPN-F100", "MINUS100", 500, 100.0)   # ลด 100 บาท ขั้นต่ำ 500

restaurant_system.add_coupon(c1)
restaurant_system.add_coupon(c2)
restaurant_system.add_coupon(c3)
restaurant_system.add_coupon(c4)

m_gold.add_coupon(c1)
m_gold.add_coupon(c4)  # ให้ Gold ลองใช้คูปองลดเงินสดด้วย
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

# Booking A: VIP (Gold Member) - จ่ายมัดจำแล้ว พร้อมเข้าใช้
# Gold Member ได้ลดค่าห้อง 20% -> (2000*5)*0.8 = 8000
b_vip = Booking("BK-VIP", m_gold, r_vip, datetime.now(), 5) # 5 ชม.
b_vip.mark_paid_deposit() # จ่ายมัดจำแล้ว 4000
restaurant_system.add_booking(b_vip)

# Booking B: Standard (Silver Member) - จ่ายมัดจำแล้ว
b_std = Booking("BK-STD", m_silver, r_std, datetime.now(), 2) # 2 ชม. (1000 บาท)
b_std.mark_paid_deposit() # จ่ายมัดจำแล้ว 500
restaurant_system.add_booking(b_std)

# Booking C: จอง Hall ใหญ่ (ยังไม่จ่ายมัดจำ) - เอาไปทำ Order ยังไม่ได้
b_hall = Booking("BK-HALL", m_bronze, r_hall, datetime.now() + timedelta(days=1), 4)
restaurant_system.add_booking(b_hall)

# ------------------------------------------
# 6. ORDERS (The Core Scenarios)
# ------------------------------------------

# === CASE 1: General Order (ทานข้าวปกติ ไม่จองห้อง) ===
gen_order = GeneralOrder("ORD-GEN-001", m_bronze)
gen_order.add_item(FoodOrderItem(food_map["Wagyu Steak"], 1))
gen_order.add_item(FoodOrderItem(food_map["Coke Refill"], 2))
restaurant_system.add_order(gen_order)


# === CASE 2: Event Order (จัดเลี้ยงในห้อง VIP + สั่งอาหารเพียบ) ===
evt_order_1 = EventOrder("ORD-EVT-001", m_gold, b_vip)
evt_order_1.add_item(FoodOrderItem(food_map["Party Set L (Chicken + Pizza)"], 3))
evt_order_1.add_item(FoodOrderItem(food_map["Ice Cream Tower"], 2))
restaurant_system.add_order(evt_order_1)


# === CASE 3: Event Order (ห้อง Standard เอาไว้เทส FixedAmountCoupon) ===
evt_order_2 = EventOrder("ORD-EVT-002", m_silver, b_std)
evt_order_2.add_item(FoodOrderItem(food_map["French Fries"], 2))
restaurant_system.add_order(evt_order_2)


# === CASE 4: Delivery Order (สั่งกลับบ้าน มีการบวกค่า Rider Fee) ===
del_order = DeliveryOrder("ORD-DEL-001", m_new, "123 Condo A, Bangkok", rider_fee=50.0)
del_order.add_item(FoodOrderItem(food_map["French Fries"], 1))
del_order.add_item(FoodOrderItem(food_map["Spaghetti Carbonara"], 2))
restaurant_system.add_order(del_order)


# === CASE 5: Order ที่จ่ายเงินแล้ว (Paid History) ===
paid_order = GeneralOrder("ORD-PAID-999", m_silver)
paid_order.add_item(FoodOrderItem(food_map["Coke Refill"], 1))
paid_order.calculate_totals() # คำนวณราคาก่อนเซ็ตสถานะ
paid_order.status = OrderStatus.PAID

# สร้าง Transaction ย้อนหลังเก็บไว้ เพื่อแสดงประวัติ
txn = Transaction(paid_order, qr_code_system, TransactionStatus.SUCCESS, "TXN-MOCK-OLD")
txn.mark_success()
restaurant_system.add_transaction(txn)
restaurant_system.add_order(paid_order)

print("System Ready! Data Loaded.")

if __name__ == "__main__":
    mcp.run()