from typing import Optional
import uuid

from shared.utils.simulate import SimulationClock


class Session:
    def __init__(self, staff_id: str):
        self.token = f"TK-{uuid.uuid4().hex[:8].upper()}"
        self.staff_id = staff_id
        self.login_time = SimulationClock.get_time()
        self._is_active = True

    def invalidate(self):
        self._is_active = False


class AuthManager:
    """Class สำหรับจัดการ Authentication โดยเฉพาะ (Repository Pattern)"""
    def __init__(self):
        self._sessions: list[Session] = []

    def create_session(self, staff_id: str) -> Session:
        # ลบ Session เก่าของ Staff คนนี้ก่อน (ถ้ามี) เพื่อให้ Login ได้ที่เดียว
        self.revoke_staff_sessions(staff_id)
        
        new_session = Session(staff_id)
        self._sessions.append(new_session)
        return new_session

    def get_session(self, token: str) -> Optional[Session]:
        return next((s for s in self._sessions if s.token == token and s._is_active), None)

    def revoke_staff_sessions(self, staff_id: str):
        for s in self._sessions:
            if s.staff_id == staff_id:
                s.invalidate()
