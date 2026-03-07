from datetime import datetime, timedelta
from fastapi import HTTPException
from typing import Dict, Any
from main_system.enum import RoomStatus, RoomType, BookingStatus

from shared.utils.simulate import SimulationClock
from main_system.external_platform.payment_method import PaymentMethod
from main_system.enum import MemberTier
