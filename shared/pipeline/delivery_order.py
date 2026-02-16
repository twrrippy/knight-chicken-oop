from __future__ import annotations
from typing import Optional, List, Tuple
from fastapi import FastAPI, HTTPException, Query
from abc import ABC, abstractmethod
from datetime import datetime
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

##### Delivery #####

class Food:
    def __init__(self, name, price):
        self.name = name
        self.price = price

class DeliveryOrder:
    def __init__(self, id: str, customer_id: str, platform: DeliveryPlatformName):
        self._id = id
        self._customer_id = customer_id
        self._platform = platform
        self._food_list: list[Food] = []
        self._total_price: float = 0.0
        self._status = OrderStatus.PENDING
        self._receipt_id = None

    def add_food(self, food: Food):
        self._food_list.append(food)
        self._total_price += food.price

    def mark_as_paid(self):
        self._status = OrderStatus.PAID
    
    def get_bill_info(self):
        items = [{"name": f.name, "price": f.price} for f in self._food_list]
        
        return {
            "customer_name": self._customer_id,
            "items": items,
            "total_base_price": self._total_price
        }

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

##### Booking #####

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

class Restaurant:
    _transaction_list: List[Transaction] = []
    _coupon_list: List[Coupon] = []
    _order_queue: list[DeliveryOrder] = []
    _menu = [
        Food("Chicken", 50.5), 
        Food("Burger", 89.0), 
        Food("Coke", 25.0)
        ]
    
    @classmethod
    def add_log(cls, transaction: Transaction):
      cls._transaction_list.append(transaction)
      print(f"[SYSTEM LOG] {transaction.timestamp} | {transaction.id} | {transaction.status} | {transaction.amount} THB")

    
    @classmethod
    def get_menu(cls):
        return cls._menu
    
    @classmethod
    def receive_order(cls, order: DeliveryOrder):
        if order.status == OrderStatus.PAID:
            cls._order_queue.append(order)
        else:
            raise HTTPException(status_code=400, detail=f"Order Not paid yet")

    @classmethod
    def add_coupon(cls, coupon: Coupon):
        cls._coupon_list.append(coupon)

    @classmethod
    def get_coupon_by_code(cls, code: str) -> Optional[Coupon]:
        for coupon in cls._coupon_list:
            if code == coupon.code:
                return coupon
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
    
class Transaction:
    def __init__(self, target_id: str, amount: float, strategy: str, status: str, payment_id: str, coupon_code: Optional[str] = None, order_type: OrderType = OrderType.GENERAL):
      self._id = f"TXN-{uuid.uuid4().hex[:12].upper()}"
      self._target_id = target_id
      self._amount = amount
      self._strategy = strategy
      self._status = status
      self._payment_id = payment_id
      self._coupon_code = coupon_code
      self._timestamp = datetime.now()
      self._order_type = order_type

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
      "discount_amount": discounted_amount,
      "total_paid": self._transaction.amount,
      "payment_method": self._transaction.strategy,
      "status": "PAID"
    }
  

# API Endpoints 
    
@mcp.tool
async def create_delivery_order(order_id: str, customer_id: str, platform_name: str):
    """
    สร้าง create_delivery_order และจ่ายเงินเสร็จสิ้น แล้ว ส่ง order ที่ชำระเงินสำเร็จไป ต่อคิวทำอาหารในครัวต่อ
    
    :type order_id: str
    :type customer_id: str
    :type platform_name: str
    """
    try:
        platform = DeliveryPlatformName(platform_name) 
    except ValueError:
        platform = DeliveryPlatformName.GRAB_FOOD
        
    order = DeliveryOrder(order_id, customer_id, platform)

    menu = Restaurant.get_menu()

    for _ in range(2):
        food = random.choice(menu)
        order.add_food(food)

    total = order.total_price
    success, receipt_or_msg = CreditCard.pay(total)

    transaction = Transaction(order.id,total,CreditCard.get_name().lower(), "PENDING", receipt_or_msg, order_type=OrderType.DELIVERY)

    if success:
        transaction.mark_success()
        order.mark_as_paid()
        Restaurant.add_log(transaction)
        receipt = Receipt(transaction, order)
        Restaurant.receive_order(order)

        return receipt.generate()
    
    else:
        transaction.mark_failed()
        Restaurant.add_log(transaction)

        raise HTTPException(status_code=402, detail=f"Payment Failed: {receipt_or_msg}")

# ==========================================
# Mock Data
# ==========================================
# Clear lists

if __name__ == "__main__":
    mcp.run()