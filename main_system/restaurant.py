from __future__ import annotations
from main_system.authentication import AuthManager
from main_system.log.receipt import Receipt
from main_system.order.order import Order, OrderStatus
from main_system.order.order_extention.booking import Booking, Room, BookingStatus, RoomStatus, TimeSlot
from main_system.external_platform.delivery_provider import DeliveryProvider
from main_system.external_platform.payment_method import PaymentMethod
from shared.utils.simulate import SimulationClock
from actor.customer import Member, Coupon, FixedAmountCoupon, PercentCoupon

from typing import TYPE_CHECKING, Optional, List, Tuple, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from main_system.enum import Enum, MemberTier
from fastmcp import FastMCP
import uuid
import random

if TYPE_CHECKING:
    from actor.staff import Staff

class Restaurant:
    def __init__(self):
        self.__receipts: List['Receipt'] = []
        self.__coupon_list: List['Coupon'] = []
        self.__members: List['Member'] = []
        self.__staff_list: List['Staff'] = []
        self.__bookings: List['Booking'] = []  
        self.__orders: List['Order'] = []      
        self.__payment_methods: List['PaymentMethod'] = []
        self.__room_list: List['Room'] = []
        self.__delivery_providers: List['DeliveryProvider'] = []
        self.__auth_manager = AuthManager()
        # ตัวนับสำหรับการรันเลข ID
        self.__member_counter = 1
        self.__staff_counter = 1

    def add_delivery_provider(self, provider: 'DeliveryProvider'): self.__delivery_providers.append(provider)
    def get_delivery_provider(self, provider_name: str) -> 'DeliveryProvider':
        for p in self.__delivery_providers:
            if p.platform_name.lower() == provider_name.lower(): return p
        raise HTTPException(404, "Delivery Provider Not Found")
    
    def add_room(self, room: 'Room'): self.__room_list.append(room)
    def get_room(self, room_id: str) -> 'Room':
        for r in self.__room_list:
            if r.id == room_id: return r
        raise HTTPException(404, "Room Not Found")
    
    def add_booking(self, booking: 'Booking'): self.__bookings.append(booking)
    def get_booking(self, booking_id: str) -> 'Booking':
        for b in self.__bookings:
            if b.id == booking_id: return b
        raise HTTPException(404, "Booking Not Found")

    def add_order(self, order: 'Order'): self.__orders.append(order)
    def get_order(self, order_id: str) -> 'Order':
        for o in self.__orders:
            if o.id == order_id: return o
        raise HTTPException(404, "Order Not Found")

    def add_payment_method(self, method: 'PaymentMethod'): self.__payment_methods.append(method)
    def get_payment_method(self, method_name: str) -> 'PaymentMethod':
        for s in self.__payment_methods:
            if s.name.lower() == method_name.lower(): return s
        raise HTTPException(400, "Invalid Payment Method")

    def add_receipts(self, receipt: 'Receipt'): 
        self.__receipts.append(receipt)
         # print(f"[SYSTEM LOG] {receipt.timestamp} | {receipt.id} | {receipt.status} | {receipt.amount} THB")
    def get_receipts_by_order_id(self, order_id: str) -> 'Receipt':
        for r in self.__receipts:
            if r.order.id == order_id: return r
        raise HTTPException(404, "Receipt Not Found")

    def add_member(self, member: 'Member'): self.__members.append(member)
    def get_member_by_id(self, id: str) -> 'Member':
        for m in self.__members:
            if m.id == id: return m
        raise HTTPException(404, "Member Not Found")
    
    def add_coupon(self, coupon: 'Coupon'): self.__coupon_list.append(coupon)
    def get_coupon(self, code: str) -> 'Coupon': 
        for c in self.__coupon_list: 
            if c.code == code: return c
        raise HTTPException(404, "Coupon Not Found")

    def add_staff(self, staff: 'Staff'): self.__staff_list.append(staff)    
    def get_staff(self, id: str) -> 'Staff':
        for s in self.__staff_list:
            if s.id == id: return s
        raise HTTPException(404, "Staff Not Found")    
    
    def check_and_issue_reward(self, order: 'Order'):
        if not isinstance(order.customer, 'Member'):
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
    
    def check_and_issue_member_teir(self, order: 'Order'):
        if not isinstance(order.customer, 'Member'):
            return None

        member = order.customer
        spending = order.subtotal

    def get_payment_method(self, method_name: str) -> 'PaymentMethod':
        for s in self.__payment_methods:
            if s.name.lower() == method_name.lower(): return s
        raise HTTPException(status_code=400, detail="Unknown Method")
    
    def booking_room(self, staff_id: str, member_id: str, room_id: str, hours: int, amount_paid: float, pay_method: str, start_time: datetime, payment_details: Dict[str, Any] = {}):
        staff = self.get_staff(staff_id)
        if not isinstance(staff, 'Staff'):
            raise HTTPException(status_code=403, detail="Only Staff can handle bookings")

        member = self.get_member_by_id(member_id)
        if not member or not isinstance(member, 'Member'):
            raise HTTPException(status_code=404, detail="Member not found")
        
        room = self.get_room(room_id)
        if not room or not isinstance(room, 'Room'):
            raise HTTPException(status_code=404, detail="Room not found")

        if not self.is_slot_avaliable(room, start_time, hours):
            raise HTTPException(status_code=400, detail="Time slot already occupied")
        
        time_slot = TimeSlot(start_time, hours)
        booking = Booking(member, room, time_slot)

        if amount_paid != booking.deposit:
            raise HTTPException(status_code=404, detail=f"Insufficient Amount: need {booking.deposit} THB")
        
        pay_med = self.get_payment_method(pay_method)
        message = booking.pay_deposit(pay_med, payment_details)
        
        self.add_booking(booking)
        return message

    def is_slot_avaliable(self, room, start, hours):
        end = start + timedelta(hours=hours)
        for b in self.__bookings:
            if b.room.id == room.id: 
                if b.status not in [BookingStatus.CANCELLED, BookingStatus.COMPLETED]:
                    if start < b.time_slot.end_time and end > b.time_slot.start_time:
                        return False
        return True

    @classmethod
    def auto_check_no_show(cls):
        now = SimulationClock.get_time()
        for b in cls.__bookings:
            deadline = b.time_slot.start_time + timedelta(minutes=30)
            if b.status == BookingStatus.DEPOSIT_PAID and now > deadline:
                b.status = BookingStatus.CANCELLED
                b.room.status = RoomStatus.AVAILABLE

    def login(self, username, password):
        member = next((m for m in self.__members if m.username == username and m.password == password), None)
        staff = next((s for s in self.__staff_list if s.username == username and s.password == password), None)
        if member:
            return self.__auth_manager.create_session(member.id)
        
        if staff:
            return self.__auth_manager.create_session(staff.id)
        
        raise HTTPException(401, "Invalid username or password")

    def logout(self, token: str):
        session = self.__auth_manager.get_session(token)
        if session:
            session.invalidate()
            return True
        return False
    
    # --- Member Registration ---
    def register_member(self, username: str, password: str, name: str, phone: str = "0000000000") -> 'Member':
        # ตรวจสอบว่า Username ซ้ำไหม
        if any(m.username == username for m in self.__members) or any(s.username == username for s in self.__staff_list):
            raise HTTPException(400, "Username already exists")
        
        # ระบบสร้าง ID ให้อัตโนมัติ
        new_id = f"M-{self.__member_counter:03d}" # ผลลัพธ์จะเป็น M-001, M-002...
        
        # สร้าง Member (Tier เริ่มต้นเป็น Bronze อัตโนมัติใน __init__)
        new_member = Member(new_id, name, MemberTier.BRONZE, username, password, phone)
        
        self.__members.append(new_member)
        self.__member_counter += 1
        return new_member

    # --- Staff Registration ---
    def register_staff(self, username: str, password: str, name: str, phone: str = "0000000000") -> 'Staff':
        from actor.staff import Staff
        if any(s.username == username for s in self.__staff_list) or any(m.username == username for m in self.__members):
            raise HTTPException(400, "Username already exists")

        new_id = f"S-{self.__staff_counter:03d}"
        
        new_staff = Staff(new_id, name, phone, username, password)
        
        self.__staff_list.append(new_staff)
        self.__staff_counter += 1
        return new_staff
    
    def get_all_members(self) -> List['Member']: return self.__members
    def get_all_staff(self) -> List['Staff']: return self.__staff_list
    def get_all_rooms(self) -> List['Room']: return self.__room_list
    def get_all_receipts(self) -> List['Receipt']: return self.__receipts
    
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
    
restaurant = Restaurant()