from typing import Optional
import uuid

from shared.utils.simulate import SimulationClock


class Session:
    def __init__(self, user_id):
        self.__token = f"TK-{uuid.uuid4().hex[:8].upper()}"
        self.__user_id = user_id
        self.__login_time = SimulationClock.get_time()
        self.__is_active = True

    @property
    def token(self): return self.__token

    @property
    def is_active(self): return self.__is_active

    @property
    def user_id(self): return self.__user_id

    def invalidate(self):
        self.__is_active = False

    def check_token(self, token: str):
        return token == self.__token


class AuthManager:
    """Class สำหรับจัดการ Authentication โดยเฉพาะ (Repository Pattern)"""
    def __init__(self):
        self.__sessions: list[Session] = []

    def create_session(self, user_id: str) -> Session:
        # ลบ Session เก่าของ User คนนี้ก่อน (ถ้ามี) เพื่อให้ Login ได้ที่เดียว
        self.revoke_staff_sessions(user_id)
        
        new_session = Session(user_id)
        self.__sessions.append(new_session)
        return new_session

    def get_session(self, token: str) -> Optional[Session]:
        return next((s for s in self.__sessions if s.check_token(token) and s.is_active), None)

    def revoke_staff_sessions(self, user_id: str):
        for s in self.__sessions:
            if s.user_id == user_id:
                s.invalidate()
