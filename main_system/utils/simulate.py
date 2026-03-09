from datetime import datetime,timedelta
import main_system.restaurant


class SimulationClock:
    """Control Over System Time for Testing Purposes"""
    _current_time = datetime.now()

    @classmethod
    def set_time(cls, new_time: datetime):
        from main_system.restaurant import restaurant
        cls._current_time = new_time
        # Trigger time-dependent checks
        restaurant.auto_check_no_show()

    @classmethod
    def get_time(cls):
        return cls._current_time