from __future__ import annotations
from typing import Optional, List, Tuple, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
from fastmcp import FastMCP
import uuid
import random

"""
TODO: 
    - ส่วนลด member teir  -> Done
    - จ่ายเงิน Deposit -> Done
    - VAT + Service Charge
    - Points system
    - point -> upgrade member tier
    - Void Bill แล้ว? คืนเงินให้ลูกค้าไหม หรือคืนเป็น coupons
    - Tip?
    - Better Delivery -> เหลือแต่ตอนเรียกไปใช้ ยังไม่ได้ทำ
    - ใส่รหัสเข้าใช้ ยืนยันตัวก่อนใช้ระบบ แบบ staff ใส่ id + รหัส ถ้าถูก ก็เป็น session นั้นๆได้?
    - พวก api เอาไว้ดูพวก ใบเสร็จ บลาๆ
    - check in
    - check out
"""

app = FastAPI()
mcp = FastMCP("PartyRoomPayment System")

class PlatformName(str, Enum):
    GRAB = "Grab"
    LINE_MAN = "Line Man"
    SHOPEE_FOOD = "Shopee Food"

class OrderType(str, Enum):
    GENERAL = "General"   
    DELIVERY = "Delivery" 
    EVENT = "Event"       

class OrderStatus(str, Enum):
    PENDING = "Pending"
    PAID = "Paid"
    READY = "Ready"
    CANCELED = "Canceled"

class DeliveryStatus(str, Enum):
    PENDING = "Pending"
    PAID = "Paid"
    DRIVER_ASSIGNED = "Driver Assigned"
    IN_TRANSIT = "In Transit"
    DELIVERED = "Delivered"
    CANCELED = "Canceled"

class BookingStatus(str, Enum):
    PENDING = "Pending"
    DEPOSIT_PAID = "Deposit Paid" 
    CHECKED_IN = "Checked In"
    COMPLETED = "Completed"    

class RoomStatus(str, Enum):
    AVAILABLE = "Available"
    RESERVED = "Reserved"
    IN_USE = "In-Use"
    CLEANING = "Cleaning"

class RoomType(str, Enum):
    VIP = "VIP"
    STANDARD = "Standard"
    HALL = "Hall"

class MemberTier(str, Enum):
    GENERAL = "General"
    BRONZE = "Bronze"
    SILVER = "Silver"
    GOLD = "Gold"

class CouponStatus(str, Enum):
    AVAILABLE = "Available"
    NOT_AVAILABLE = "Not Available"

class StaffRole(str, Enum):
    PartyStaff = "Party Staff"
    KitchenStaff = "Kitchen Staff"

class TransactionStatus(str, Enum):
    PENDING = "PENDING"
    FAILED = "FAILED"
    SUCCESS = "SUCCESS"

class MenuItemStatus(str, Enum):
    AVAILABLE = "Available"
    UNAVAILABLE = "Unavailable"

class SimulationClock:
    __current_time = datetime.now()

    @classmethod
    def set_time(cls, new_time: datetime):
        cls.__current_time = new_time

    @classmethod
    def get_time(cls):
        return cls.__current_time

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
        raise HTTPException(409, f"Does Not Meet Minimum Price {self.minimum_price}")

class FixedAmountCoupon(Coupon):
    def __init__(self, id: str, code: str, minimum_price: float, amount: float) -> None:
        super().__init__(id, code, minimum_price)
        if amount > minimum_price:
            raise ValueError("Minimum Price must be >= Amount")
        self.__amount = amount

    def apply_coupon(self, base_price: float) -> float:
        if self.is_applicable(base_price):
            return self.__amount
        raise HTTPException(409, f"Does Not Meet Minimum Price {self.minimum_price}")

class Receipt:
    def __init__(self, order: Order, method: PaymentMethod):
      self.__id = f"TXN-{uuid.uuid4().hex[:12].upper()}"
      self.__order = order                 
      self.__method = method
      self.__timestamp = SimulationClock.get_time()

    @property
    def id(self): return self.__id
    @property
    def order(self): return self.__order
    @property
    def method(self): return self.__method
    @property
    def timestamp(self): return self.__timestamp

    def generate(self):
        order = self.order
        coupon_code = order.coupon_used.code if order.coupon_used else "None"
        deposit_deducted = order.booking.deposit if order.booking else 0.0
        
        return {
            "receipt_no": self.id,
            "date": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "merchant": "Knight Chicken Fast Food Co.",
            
            "customer_info": {
                "name": order.customer.name,
                "tier": order.customer.tier
            },
            
            "order_summary": {
                "order_id": order.id,
                "order_type": order.order_type
            },
            
            "itemized_bill": {
                "foods": [item.get_details() for item in order.order_item],
                "booking_details": order.booking.get_details() if order.booking else "None",
                "delivery_details": order.delivery.get_details() if order.delivery else "None"
            },
            
            "financial_summary": {
                "subtotal": order.subtotal,
                "coupon_applied": coupon_code,
                "discount_amount": order.discount,
                "deposit_deducted": deposit_deducted,
                "net_amount_due": order.total_payable_amount
            },
            
            "payment_record": {
                "method": self.method.name,
                "status": "SUCCESS"
            }
        }
    
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

class Customer(User):
    def __init__(self, id: str, name: str) -> None:
        super().__init__(id, name)
        self.__tier: MemberTier = MemberTier.GENERAL

    @property
    def tier(self) -> MemberTier: return self.__tier

class Member(Customer):
    def __init__(self, id: str, name: str, tier: MemberTier):
        super().__init__(id, name)
        self.__coupon_list: List[Coupon] = [] 
        self.__receipt_list: List[Receipt] = []
        self.__tier: MemberTier = tier
        self.__points: int = 0

    def add_receipt(self, receipt: Receipt): self.__receipt_list.append(receipt)
    def add_coupon(self, coupon: Coupon): self.__coupon_list.append(coupon)
    
    def get_coupon_by_code(self, code: str):
        for coupon in self.__coupon_list:
            if coupon.code == code: return coupon
        raise HTTPException(404, "Coupon Not Found")

    def get_member_discount(self, base_price: float):
        match self.tier:
            case MemberTier.GENERAL: return 0.0
            case MemberTier.BRONZE: return base_price * 0.05
            case MemberTier.SILVER: return base_price * 0.10
            case MemberTier.GOLD: return base_price * 0.15
        return 0.0

    @property
    def tier(self) -> MemberTier: return self.__tier

class OrderItem:
    def __init__(self, menu_item: MenuItem, quantity: int):
        self.__menu_item = menu_item
        self.__quantity = quantity
    @property
    def menu_item(self): return self.__menu_item
    @property
    def quantity(self): return self.__quantity
    @property
    def price(self): return self.__menu_item.price * self.__quantity

    def get_details(self) -> Dict[str, Any]:
        return {
            "name": self.menu_item.name,
            "quantity": self.quantity,
            "price": self.menu_item.price
        }

class MenuItem:
    def __init__(self, name: str, price: float, status: MenuItemStatus) -> None:
        self.__name = name
        self.__price = price
        self.__status = status
    @property
    def name(self): return self.__name
    @property
    def price(self): return self.__price
    @property
    def status(self): return self.__status

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

class Booking:
    def __init__(self, booking_id, member: Member, room: Room, time_slot: TimeSlot):
        self.__id = booking_id
        self.__member = member
        self.__room = room
        self.__time_slot = time_slot
        self.__status = BookingStatus.PENDING

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

class DeliveryProvider():
    def __init__(self, platform_name: PlatformName) -> None:
        self.__platform_name = platform_name
    
    def request_rider(self, delivery: Delivery) -> Tuple[bool, str, str]:
        if not delivery.provider.platform_name == self.platform_name:
            raise HTTPException(400, "Invalid Provider")
        if delivery.status != DeliveryStatus.PENDING:
            raise HTTPException(400, "Delivery Already Assigned")

        is_success = True
        match self.platform_name:
            case PlatformName.GRAB:
                rider_name = random.choice(["สุธนิษฐา จารุตัน", "คมพิชญ์ คำป้อง", "ชูวิทย์ มาตรเหลือง"])
                tracking_id = f"GRB-{random.randint(1000000, 9999999)}"
            case PlatformName.LINE_MAN:
                rider_name = random.choice(["ขวัญหล้า บุญวิวัฒนาการ", "สุสกาวรัตน์อัจฉรา ศรีหะจันทร์", "อัศนีชัย สุติ"])
                tracking_id = f"LMN-{random.randint(1000000, 9999999)}"
            case PlatformName.SHOPEE_FOOD:
                rider_name = random.choice(["ทนากร เอี้ยวพันธ์", "ละม้าย ศรีพลับ", "รุจาภา สันทาลุนัย"])
                tracking_id = f"SHP-{random.randint(1000000, 9999999)}"

        return (is_success, rider_name, tracking_id)

    def calculate_fee(self, distance_km: float) -> float:
        match self.platform_name:
            case PlatformName.GRAB:
                return distance_km * 10
            case PlatformName.LINE_MAN:
                return distance_km * 5
            case PlatformName.SHOPEE_FOOD:
                return distance_km * 2
            case _:
                return 0.0
    
    @property
    def platform_name(self): return self.__platform_name

class Delivery:
    def __init__(self, delivery_id: str, provider: DeliveryProvider, distance: float):
        self.__delivery_id = delivery_id
        self.__provider = provider
        self.__distance = distance
        self.__status = DeliveryStatus.PENDING
        self.__tracking_id: Optional[str] = None
        self.__rider_name: Optional[str] = None
    
    @property
    def tracking_id(self): return self.__tracking_id
    @property
    def rider_name(self): return self.__rider_name
    @property
    def id(self): return self.__delivery_id
    @property
    def provider(self): return self.__provider
    @property
    def distance(self): return self.__distance
    @property
    def status(self): return self.__status
    @property
    def fee(self):
        return self.provider.calculate_fee(self.distance)
    
    def request_rider(self):
        success, rider_name, tracking_id = self.provider.request_rider(self)
        if success:
            self.__rider_name = rider_name
            self.__tracking_id = tracking_id
            self.__status = DeliveryStatus.DRIVER_ASSIGNED
            return success, rider_name, tracking_id
        raise HTTPException(400, "Rider Request Failed")

    def mark_delivered(self):
        self.__status = DeliveryStatus.DELIVERED

    def mark_as_paid(self):
        self.__status = DeliveryStatus.PAID

    def mark_canceled(self):
        self.__status = DeliveryStatus.CANCELED

    def get_details(self) -> Dict[str, Any]:
        return {
            "type": "Delivery Details",
            "status": self.status,
            "delivery_id": self.id,
            "provider": self.provider.platform_name,
            "tracking_id": self.tracking_id,
            "rider_name": self.rider_name,
            "distance": self.distance,
            "fee": self.fee
        }

class Order:
    def __init__(self, order_id: str, customer: Customer):
        self.__id = order_id
        self.__customer: Customer = customer
        self.__order_list: List[OrderItem] = []
        self.__status = OrderStatus.PENDING
        self.__coupon_used: Optional[Coupon] = None
        self.__booking: Optional[Booking] = None
        self.__delivery: Optional[Delivery] = None
        self.__subtotal = 0.0
        self.__discount = 0.0
        self.__final_price = 0.0

    def add_item(self, item: OrderItem):
        self.__order_list.append(item)

    def add_booking(self, booking: Booking):
        if self.booking: raise HTTPException(409, "Booking Already Exists")
        self.__booking = booking

    def add_delivery(self, delivery: Delivery):
        if self.delivery: raise HTTPException(409, "Delivery Already Exists")
        self.__delivery = delivery

    def pre_calculate_totals(self, coupon_code: Optional[str] = None):
        coupon = None
        if coupon_code:
            if isinstance(self.customer, Member):
                coupon = self.customer.get_coupon_by_code(coupon_code)
            else:
                raise HTTPException(409, "Only members can use coupons")
        
        subtotal = sum(item.price for item in self.order_item)
        deposit = 0.0

        if self.booking:
            subtotal += self.booking.full_price
            deposit = self.booking.deposit

        if self.delivery:
            subtotal += self.delivery.fee

        coupon_discount = 0.0
        if coupon:
             if coupon.status != CouponStatus.AVAILABLE:
                raise HTTPException(409, "Coupon Not Available")
             coupon_discount = coupon.apply_coupon(subtotal)
        
        teir_discount = 0.0
        if isinstance(self.customer, Member):
            teir_discount = self.customer.get_member_discount(subtotal)

        discount = min(teir_discount + coupon_discount, subtotal)

        final_price = subtotal - discount - deposit
        if final_price < 0: final_price = 0.0
        
        return {
            "Member": {
                "Customer ID": self.customer.id,
                "Name": self.customer.name
            },
            "Order Id": self.id,
            "Food": [item.get_details() for item in self.order_item],
            "Booking": self.booking.get_details() if self.booking else "None",
            "Delivery": self.delivery.get_details() if self.delivery else "None",
            "Total Price Before Discount": subtotal,
            "Coupon Code": coupon.code if coupon else "None",
            "Discounted": discount,
            "Final Price": final_price
        }

    def calculate_totals(self, coupon_code: Optional[str] = None):
        info = self.pre_calculate_totals(coupon_code)
        self.__subtotal = info.get("Total Price Before Discount")
        self.__discount = info.get("Discounted")
        self.__final_price = info.get("Final Price")
        if coupon_code and isinstance(self.customer, Member):
            self.__coupon_used = self.customer.get_coupon_by_code(coupon_code)
        return info
    
    def execute_payment(self, method: PaymentMethod, payment_details: Dict[str, Any] = {}, coupon_code: Optional[str] = None) -> Receipt:
        coupon = None
        if coupon_code:
            if isinstance(self.customer, Member):
                coupon = self.customer.get_coupon_by_code(coupon_code)
            else:
                raise HTTPException(409, "Only members can use coupons")
            
        info = self.calculate_totals(coupon_code)
        total_payable = info["Final Price"]

        if total_payable > 0:
            success, note = method.pay(total_payable, **payment_details)
        else:
            success = True
            note = "Payment Done"

        if success:
            self.status = OrderStatus.PAID

            if self.booking:
                self.booking.mark_checked_in()
                self.booking.room.mark_room_in_use()
            
            if self.delivery:
                self.delivery.mark_as_paid()

            if coupon: coupon.mark_as_used()

            receipt = Receipt(self, method)
            if isinstance(self.customer, Member):
                self.customer.add_receipt(receipt)
            return receipt
        else:
            raise HTTPException(400, note)

    @property
    def subtotal(self): return self.__subtotal
    @property
    def discount(self): return self.__discount
    @property
    def booking(self): return self.__booking
    @property
    def delivery(self): return self.__delivery
    @property
    def order_type(self): 
        if self.booking: return OrderType.EVENT
        elif self.delivery: return OrderType.DELIVERY
        return OrderType.GENERAL
    @property
    def id(self): return self.__id
    @property
    def total_payable_amount(self): return self.__final_price
    @property
    def coupon_used(self): return self.__coupon_used
    @property
    def order_item(self): return self.__order_list
    @property
    def customer(self): return self.__customer
    @property
    def status(self): return self.__status
    @status.setter
    def status(self, val: OrderStatus): self.__status = val
    
class PaymentMethod(ABC):
    def __init__(self, id: str, name: str):
        self.__id = id
        self.__name = name

    @property
    @abstractmethod
    def name(self) -> str: pass

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

class Restaurant:
    def __init__(self):
        self.__receipts: List[Receipt] = []
        self.__coupon_list: List[Coupon] = []
        self.__members: List[Member] = []
        self.__staff_list: List[Staff] = []
        self.__bookings: List[Booking] = []  
        self.__orders: List[Order] = []      
        self.__payment_strategies: List[PaymentMethod] = []
        self.__room_list: List[Room] = []
        self.__delivery_providers: List[DeliveryProvider] = []

    def add_delivery_provider(self, provider: DeliveryProvider): self.__delivery_providers.append(provider)
    def get_delivery_provider(self, provider_name: str) -> DeliveryProvider:
        for p in self.__delivery_providers:
            if p.platform_name.lower() == provider_name.lower(): return p
        raise HTTPException(404, "Delivery Provider Not Found")
    
    def add_room(self, room: Room): self.__room_list.append(room)
    def get_room(self, room_id: str) -> Room:
        for r in self.__room_list:
            if r.id == room_id: return r
        raise HTTPException(404, "Room Not Found")
    
    def add_booking(self, booking: Booking): self.__bookings.append(booking)
    def get_booking(self, booking_id: str) -> Booking:
        for b in self.__bookings:
            if b.id == booking_id: return b
        raise HTTPException(404, "Booking Not Found")

    def add_order(self, order: Order): self.__orders.append(order)
    def get_order(self, order_id: str) -> Order:
        for o in self.__orders:
            if o.id == order_id: return o
        raise HTTPException(404, "Order Not Found")

    def add_payment_method(self, method: PaymentMethod): self.__payment_strategies.append(method)
    def get_payment_method(self, method_name: str) -> PaymentMethod:
        for s in self.__payment_strategies:
            if s.name.lower() == method_name.lower(): return s
        raise HTTPException(400, "Invalid Payment Method")

    def add_receipts(self, r: Receipt): self.__receipts.append(r)
    def get_receipts_by_order_id(self, order_id: str) -> Receipt:
        for r in self.__receipts:
            if r.order.id == order_id: return r
        raise HTTPException(404, "Receipt Not Found")

    def add_member(self, m: Member): self.__members.append(m)
    def get_member_by_id(self, id: str) -> Member:
        for m in self.__members:
            if m.id == id: return m
        raise HTTPException(404, "Member Not Found")
    
    def add_coupon(self, c: Coupon): self.__coupon_list.append(c)
    def get_coupon(self, code: str) -> Coupon: 
        for c in self.__coupon_list: 
            if c.code == code: return c
        raise HTTPException(404, "Coupon Not Found")

    def add_staff(self, s: Staff): self.__staff_list.append(s)    
    def get_staff(self, id: str) -> Staff:
        for s in self.__staff_list:
            if s.id == id: return s
        raise HTTPException(404, "Staff Not Found")    
    
    def check_and_issue_reward(self, order: Order):
        if not isinstance(order.customer, Member):
            return None

        member = order.customer
        spending = order.subtotal
        if not spending: return None
    
        reward_coupon = None

        if spending >= 3000:
            code = f"RW20-{uuid.uuid4().hex[:6].upper()}"
            reward_coupon = PercentCoupon(f"CPN-{code}", code, 1000.0, 20.0)
        elif spending >= 1000:
            code = f"RWF100-{uuid.uuid4().hex[:6].upper()}"
            reward_coupon = FixedAmountCoupon(f"CPN-{code}", code, 500.0, 100.0)

        if reward_coupon:
            member.add_coupon(reward_coupon)
            return reward_coupon.code
            
        return None
    
    def check_and_issue_member_teir(self, order: Order):
        if not isinstance(order.customer, Member):
            return None

        member = order.customer
        spending = order.subtotal
    
    ### --------- API --------- ###
    
    def preview_booking_details(self, booking_id: str):
        booking = self.get_booking(booking_id)
        return booking.get_details()
    
    def process_pay_deposit(self, booking_id: str, method_name: str, payment_details: Dict[str, Any]):
        booking = self.get_booking(booking_id)
        method = self.get_payment_method(method_name)
        if booking.status != BookingStatus.PENDING:
            raise HTTPException(400, "Booking Already Paid")
        
        return booking.pay_deposit(method, payment_details)
    
    def process_order_payment(self, order_id: str, staff_id: str, coupon_code: Optional[str], method_name: str, payment_details: Dict[str, Any]):
        method = self.get_payment_method(method_name)
        staff = self.get_staff(staff_id)
        order = self.get_order(order_id)
        
        if order.order_type == OrderType.EVENT and staff.role != StaffRole.PartyStaff:
            raise HTTPException(400, "Invalid Staff Role for Event Order")
            
        if order.status == OrderStatus.PAID: 
            raise HTTPException(400, "Order Already Paid")
            
        receipt = order.execute_payment(method, payment_details, coupon_code)
        self.add_receipts(receipt)
        
        reward_code = self.check_and_issue_reward(order)
        
        receipt_data = receipt.generate()
        if reward_code:
            receipt_data["reward_issued"] = f"Congratulations! You received a new coupon: {reward_code}"
            
        return receipt_data
    
    def preview_order_bill(self, order_id: str, staff_id: str, coupon_code: Optional[str]):
        order = self.get_order(order_id)
        if order.status == OrderStatus.PAID: raise HTTPException(400, "Order Already Paid")
        staff = self.get_staff(staff_id)
        return order.pre_calculate_totals(coupon_code)

restaurant_system = Restaurant()

@mcp.tool
@app.get("/booking/preview_booking/{booking_id}")
async def preview_booking(booking_id: str):
    """
    
    """
    return restaurant_system.preview_booking_details(booking_id)

@mcp.tool
@app.post("/booking/pay_deposit/{booking_id}")
async def pay_deposit(booking_id: str, method: str, payment_details: Dict[str, Any]):
    """
    
    """
    return restaurant_system.process_pay_deposit(booking_id, method, payment_details)

@mcp.tool
@app.post("/payment/confirm_pay/{order_id}")
async def confirm_pay(order_id: str, staff_id: str, method: str, coupon_code: Optional[str] = Query(default=None), payment_details: Dict[str, Any] = {}):
    """
    ยืนยันการชำระเงิน คำนวณยอดสุดท้าย และออกใบเสร็จ (Execute Payment)

    หน้าที่:
    - ยืนยันยอดชำระสุทธิและตัดเงินจริงตาม Payment Method ที่เลือก
    - อัปเดตสถานะของออบเจ็กต์ต่างๆ ที่เกี่ยวข้องในระบบเมื่อชำระเงินสำเร็จ
    
    Arguments:
    - order_id: รหัสออเดอร์ (Format: ORD-xxx-xxx)
    - staff_id: รหัสพนักงานผู้ทำรายการ
    - method: วิธีการชำระเงิน (เช่น "qrcode", "creditcard", "cash")
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
    return restaurant_system.process_order_payment(order_id, staff_id, coupon_code, method, payment_details)

@mcp.tool
@app.post("/payment/preview_order/{order_id}")
async def preview_order(order_id: str, staff_id: str, coupon_code: Optional[str] = Query(default=None)):
    """
    คำนวณยอดเงินที่ต้องชำระสำหรับ Order (Preview)
    
    หน้าที่:
    - ดึงข้อมูล Order ตาม ID (Format: ORD-xxx-xxx)
    - ตรวจสอบสิทธิ์พนักงาน (staff_id) ว่าสามารถเข้าถึงประเภท Order นั้นๆ ได้หรือไม่
    - (Optional) ทดลองคำนวณส่วนลดถ้าใส่ coupon_code มา เพื่อดูยอดก่อนจ่ายจริง
    
    การทำงาน:
    - ระบบจะคืนค่า JSON สรุปรายละเอียดออเดอร์ทั้งหมด (รายการอาหาร, รายละเอียดการจองห้อง, ค่าส่ง ฯลฯ)
    - แสดงยอดรวมก่อนลด, ส่วนลดจากคูปอง, เงินมัดจำที่หักออก (ถ้ามี), และยอดสุทธิ (Final Price) เพื่อให้พนักงานแจ้งลูกค้า
    - ฟังก์ชันนี้เป็นแบบ Stateless จะยังไม่บันทึกการใช้คูปองหรือเปลี่ยนแปลงสถานะใดๆ จนกว่าจะเรียก /confirm_pay
    """

    return restaurant_system.preview_order_bill(order_id, staff_id, coupon_code)