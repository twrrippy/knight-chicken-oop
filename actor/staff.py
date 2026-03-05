from abc import ABC
from datetime import datetime, timedelta
from actor.user import User
from main_system.restaurant import restaurant

class Staff(User):
    def __init__(self, id: str, name: str, phone_number: str, username: str="", password: str=""):
        super().__init__(id, name, phone_number, username, password)

    def check_room_availability(self, room, start_time: datetime, hours: int) -> bool:
        return restaurant.is_slot_available(room, start_time, hours)

