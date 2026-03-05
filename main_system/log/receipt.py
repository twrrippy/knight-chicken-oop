import uuid
from shared.utils.simulate import SimulationClock
from main_system.order.order import Order
from main_system.external_platform.payment_method import PaymentMethod
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
    