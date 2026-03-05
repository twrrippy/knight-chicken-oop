from typing import Optional
import uuid

from shared.utils.simulate import SimulationClock


class Session:
    def __init__(self, user_id):
        self.token = f"TK-{uuid.uuid4().hex[:8].upper()}"
        self.user_id = user_id
        self.login_time = SimulationClock.get_time()
        self._is_active = True

    def invalidate(self):
        self._is_active = False


class AuthManager:
    """Class สำหรับจัดการ Authentication โดยเฉพาะ (Repository Pattern)"""
    def __init__(self):
        self._sessions: list[Session] = []

    def create_session(self, user_id: str) -> Session:
        # ลบ Session เก่าของ User คนนี้ก่อน (ถ้ามี) เพื่อให้ Login ได้ที่เดียว
        self.revoke_staff_sessions(user_id)
        
        new_session = Session(user_id)
        self._sessions.append(new_session)
        return new_session

    def get_session(self, token: str) -> Optional[Session]:
        return next((s for s in self._sessions if s.token == token and s._is_active), None)

    def revoke_staff_sessions(self, user_id: str):
        for s in self._sessions:
            if s.user_id == user_id:
                s.invalidate()
