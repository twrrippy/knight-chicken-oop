from enum import Enum
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
    RESERVED = "Reserved"
    CONFIRMED = "Confirmed"
    PAIDED = "Paid"
    COOKING = "Cooking"
    READY = "Ready"
    SERVED = "Served"
    CANCELED = "Canceled"

class OrderItemStatus(Enum):
    PENDING = "Pending"
    ADDED = "Added to Order"
    RESERVED = "Reserved"
    OUT_OF_STOCK = "Out of Stock"
    COOKING = "Cooking"
    READY = "Ready"
    SERVED = "Served"
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
    PAID = "Paid" 
    CHECKED_IN = "Checked In"
    COMPLETED = "Completed"  
    CANCELLED = "Canceled"  

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

class TransactionStatus(str, Enum):
    PENDING = "PENDING"
    FAILED = "FAILED"
    SUCCESS = "SUCCESS"

class MenuItemStatus(str, Enum):
    AVAILABLE = "Available"
    UNAVAILABLE = "Unavailable"

class ItemStatus(Enum):
    AVAILABLE = "Available"
    RESERVED = "Reserved"
class IngredientType(Enum):
    STRICT = "Strict"
    CUSTOMIZABLE = "Customizable"