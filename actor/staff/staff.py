from abc import ABC
from actor.user import User

class Staff(ABC, User):
    pass

class FrontStaff(Staff):
    pass

class KitchenStaff(Staff):
    pass

class PartyStaff(Staff):
    pass

class Manager(FrontStaff, KitchenStaff, PartyStaff):
    pass