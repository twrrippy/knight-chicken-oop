from abc import ABC
from actor.user import User
from main_system.enum import StaffRole

class Staff(User):
    def __init__(self, id: str, name: str, role: StaffRole):
        super().__init__(id, name)
        self.__role = role
    @property
    def role(self): return self.__role
