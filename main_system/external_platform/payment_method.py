from abc import ABC, abstractmethod
from typing import Tuple
import random
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
        if not account_number: return False, 'Missing "account_number"'
        
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
        return (True, "Payment Done") if success else (False, "Card Declined Please Try Again")

class Cash(PaymentMethod):
    def __init__(self, id: str, name: str): super().__init__(id, name)

    @property
    def name(self): return "cash"
    
    def pay(self, amount: float, **kwargs) -> Tuple[bool, str]:
        received = kwargs.get("cash_received")
        if received is None: return False, 'Missing "cash_received"'
        
        if float(received) < amount: return False, f"Insufficient Cash"
        return True, "Payment Done"

