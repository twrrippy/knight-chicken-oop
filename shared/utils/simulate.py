from datetime import datetime
import main_system.restaurant


class SimulationClock:
    """Control Over System Time for Testing Purposes"""
    _current_time = datetime.now()

    @classmethod
    def set_time(cls, new_time: datetime):
        cls._current_time = new_time
        # Trigger time-dependent checks
        main_system.restaurant.Restaurant.auto_check_no_show()

    @classmethod
    def get_time(cls):
        return cls._current_time
    
class TimeSlot:
    def __init__(self, start_time: datetime, hours: int):
        self.__start_time = start_time
        self.__end_time = start_time + timedelta(hours=hours)
        self.__hours = hours

    @property
    def start_time(self): return self.__start_time
    @property
    def end_time(self): return self.__end_time
    @property
    def hours(self): return self.__hours