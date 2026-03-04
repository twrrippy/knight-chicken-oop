from main_system.log.receipt import Receipt
from main_system.order.order import Order, OrderStatus
from main_system.order.order_extention.booking import Booking, Room, BookingStatus
from main_system.external_platform.delivery_provider import DeliveryProvider
from main_system.external_platform.payment_method import PaymentMethod
from actor.customer import Member, Coupon, FixedAmountCoupon, PercentCoupon
from actor.staff import Staff
from __future__ import annotations
from typing import Optional, List, Tuple, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
from fastmcp import FastMCP
import uuid
import random
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
        
        # if order.order_type == OrderType.EVENT and staff.role != StaffRole.PartyStaff:
        #     raise HTTPException(400, "Invalid Staff Role for Event Order")
            
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