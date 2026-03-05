import random
import uuid
import uvicorn
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from abc import ABC, abstractmethod
from fastapi import Body, FastAPI, HTTPException, Query, status
from fastmcp import FastMCP
from datetime import datetime, timedelta
from actor.customer import Member
from shared.utils.simulate import SimulationClock
from main_system.enum import CouponStatus, MemberTier
from main_system.restaurant import Restaurant, restaurant_system
from main_system.log.receipt import Receipt
from main_system.external_platform.payment_method import PaymentMethod
from main_system.external_platform.delivery_provider import DeliveryProvider


