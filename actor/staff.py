from abc import ABC
from datetime import datetime, timedelta
from actor.user import User
from main import restaurant_system

class Staff(User):
    def check_room_avaliability(self, room: str, start: datetime, hours: int):
            return restaurant_system.is_slot_avaliable(room, start, hours)

    def check_in_booking():
        pass

    def check_out_booking():
        pass
