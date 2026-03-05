from typing import Optional
import uuid
from fastapi import HTTPException, FastAPI, Query

from shared.pipeline.booking_room import SimulationClock


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
    @property
    def phone(self):
        return self.__phone
    @phone.setter
    def phone(self, phone):
        self.__phone = phone

class Staff(User):
    def __init__(self, id: str, name: str, tier: str, username: str, password: str, phone):
        super().__init__(id, name, phone)
        self.__tier = tier
        self.__username = username
        self.__password = password
    
    def username(self, username):
        self.__username = username

    def check_username(self, username):
        return self.__username == username
    
    def password(self, password):
        self.__password = password
    
    def check_password(self, password):
        return self.__password == password

class Customer(User):
    pass
class Member(Customer):
    def __init__(self, id: str, name: str, tier: str, username: str, password: str, phone):
        super().__init__(id, name, phone)
        self.__tier = tier
        self.__username = username
        self.__password = password

    @property
    def tier(self):
        return self.__tier
    
    
    def username(self, username):
        self.__username = username

    def check_username(self, username):
        return self.__username == username
    
    def password(self, password):
        self.__password = password
    
    def check_password(self, password):
        return self.__password == password


class Session:
    def __init__(self, id: str):
        self.__token = f"TK-{uuid.uuid4().hex[:8].upper()}"
        self.__id = id
        self.__login_time = SimulationClock.get_time()
        self.__is_active = True

    def invalidate(self):
        self.__is_active = False

class AuthManager:
    """Class สำหรับจัดการ Authentication โดยเฉพาะ (Repository Pattern)"""
    def __init__(self):
        self.__sessions: list[Session] = []

    def create_session(self, staff_id: str) -> Session:
        # ลบ Session เก่าของ Staff คนนี้ก่อน (ถ้ามี) เพื่อให้ Login ได้ที่เดียว
        self.revoke_staff_sessions(staff_id)
        
        new_session = Session(staff_id)
        self.__sessions.append(new_session)
        return new_session

    def get_session(self, token: str) -> Optional[Session]:
        return next((s for s in self.__sessions if s.token == token and s._is_active), None)

    def revoke_staff_sessions(self, staff_id: str):
        for s in self.__sessions:
            if s.staff_id == staff_id:
                s.invalidate()

class Restaurant:
    def __init__(self):
        # ... ข้อมูลเดิมที่มีอยู่ ...
        self.__staff_list: list[Staff] = []
        self.__members: list[Member] = []
        self.__auth_manager = AuthManager()
        # ตัวนับสำหรับการรันเลข ID
        self.__member_counter = 1
        self.__staff_counter = 1

    def login(self, username, password):
        # ค้นหา Staff จาก username และ password
        member = next((m for m in self.__members if m.check_username(username) and m.check_password(password)), None)
        if member:
            return self.__auth_manager.create_session(member.id)
        staff = next((s for s in self.__staff_list if s.check_username(username) and s.check_password(password)), None)
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
    def register_member(self, username: str, password: str, name: str, phone: str = "") -> Member:
        # ตรวจสอบว่า Username ซ้ำไหม
        if any(m.check_username(username) for m in self.__members):
            raise HTTPException(400, "Username already exists")
        
        # ระบบสร้าง ID ให้อัตโนมัติ
        new_id = f"M-{self.__member_counter:03d}" # ผลลัพธ์จะเป็น M-001, M-002...
        
        # สร้าง Member (Tier เริ่มต้นเป็น Bronze อัตโนมัติใน __init__)
        new_member = Member(new_id, name, "Bronze", username, password, phone)
        
        self.__members.append(new_member)
        self.__member_counter += 1
        return new_member

    # --- Staff Registration ---
    def register_staff(self, username: str, password: str, name: str) -> Staff:
        if any(s.username == username for s in self.__staff_list):
            raise HTTPException(400, "Username already exists")

        new_id = f"S-{self.__staff_counter:03d}"
        
        new_staff = Staff(new_id, name, username, password)
        
        self.__staff_list.append(new_staff)
        self.__staff_counter += 1
        return new_staff
    
    def get_staff(self, s_id: str): return next((s for s in self.__staff_list if s.id == s_id), None)
    
restaurant_system = Restaurant()
app = FastAPI()

@app.post("/auth/login", tags=["Authentication"])
async def login(username: str, password: str):
    """เข้าสู่ระบบด้วย username และ password เพื่อรับ Token"""
    token = restaurant_system.login(username, password)
    return {"access_token": token, "token_type": "bearer"}

@app.post("/auth/logout", tags=["Authentication"])
async def logout(token: str = Query(...)):
    """ออกจากระบบและทำลาย Token"""
    success = restaurant_system.logout(token)
    if success:
        return {"message": "Logged out successfully"}
    raise HTTPException(status_code=400, detail="Invalid Token")

@app.post("/register/member", tags=["Registration"])
async def member_sign_up(
    username: str, 
    password: str, 
    display_name: str, 
    phone: Optional[str] = None
):
    """ลงทะเบียนลูกค้าใหม่: ระบบจะ Generate ID และตั้ง Tier เป็น Bronze ให้เอง"""
    member = restaurant_system.register_member(username, password, display_name, phone)
    return {
        "message": "Welcome to Party Hub!",
        "your_id": member.id,
        "username": member.username,
        "tier": member.tier
    }

@app.post("/register/staff", tags=["Registration"])
async def staff_sign_up(username: str, password: str, name: str):
    """ลงทะเบียนพนักงานใหม่: ระบบจะ Generate ID (S-xxx) ให้อัตโนมัติ"""
    staff = restaurant_system.register_staff(username, password, name)
    return {
        "message": "Staff registered successfully",
        "staff_id": staff.id,
        "name": staff.name
    }