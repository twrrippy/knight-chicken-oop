from datetime import timedelta, datetime
from main_system.coupon import PercentCoupon, FixedAmountCoupon
from main_system.enum import MemberTier, OrderType, OrderStatus, RoomType, PlatformName, BookingStatus
from main_system.restaurant import Order, Staff, Member, SingleMenuItem
from main_system.external_platform.payment_method import Cash, QRCode
from main_system.booking import Room, TimeSlot, Booking
from main_system.external_platform.delivery_provider import Delivery, GrabDeliveryProvider, LineManDeliveryProvider, ShopeeFoodDeliveryProvider
from main_system.restaurant import restaurant
from shared.utils.simulate import SimulationClock

def initialize_mock_data():
    # 1. Staff
    mock_staff = Staff("S-001", "Alice Staff", "0801234567", "alice", "password")
    restaurant.add_staff(mock_staff)

    # 2. Member
    mock_member = Member("M-001", "Bob Customer", MemberTier.GOLD, "bob", "password", "0812345678")
    restaurant.add_member(mock_member)

    # 3. Menu Item
    mock_menu_1 = SingleMenuItem("Fried Chicken", 150.0, timedelta(minutes=15), [])
    mock_menu_2 = SingleMenuItem("French Fries", 80.0, timedelta(minutes=10), [])
    mock_menu_3 = SingleMenuItem("Cola", 40.0, timedelta(minutes=2), [])
    restaurant.add_menu(mock_menu_1)
    restaurant.add_menu(mock_menu_2)
    restaurant.add_menu(mock_menu_3)

    # 4. Coupons
    mock_coupon1 = PercentCoupon("CPN-01", "DISCOUNT20", 200.0, 20.0) # 20% off
    mock_coupon2 = FixedAmountCoupon("CPN-02", "MINUS50", 100.0, 50.0) # 50 THB off
    mock_member.add_coupon(mock_coupon1)
    mock_member.add_coupon(mock_coupon2)

    # 5. Payment Methods
    restaurant.add_payment_method(Cash("PAY-01", "cash"))
    restaurant.add_payment_method(QRCode("PAY-02", "qrcode"))

    # 6. Delivery Providers
    grab = GrabDeliveryProvider()
    lineman = LineManDeliveryProvider()
    shopee = ShopeeFoodDeliveryProvider()
    restaurant.add_delivery_provider(grab)
    restaurant.add_delivery_provider(lineman)
    restaurant.add_delivery_provider(shopee)

    # 7. Rooms
    room_vip = Room("R-VIP-01", RoomType.VIP)
    room_hall = Room("R-HALL-01", RoomType.HALL)
    restaurant.add_room(room_vip)
    restaurant.add_room(room_hall)

    # ==========================================
    # ORDER SCENARIO 1: General Order (Dine-in)
    # ==========================================
    order_1 = Order(OrderType.GENERAL, mock_member)
    if not hasattr(order_1, "_Order__order_item_list"):
        order_1._Order__order_item_list = []
    order_1.add_order_item(mock_menu_1, 2) # 300
    order_1.add_order_item(mock_menu_3, 2) # 80
    order_1.status = OrderStatus.PENDING
    restaurant.add_order(order_1)

    # ==========================================
    # ORDER SCENARIO 2: Delivery Order
    # ==========================================
    order_2 = Order(OrderType.DELIVERY, mock_member)
    if not hasattr(order_2, "_Order__order_item_list"):
        order_2._Order__order_item_list = []
    order_2.add_order_item(mock_menu_1, 1) # 150
    order_2.add_order_item(mock_menu_2, 1) # 80
    
    # Add Delivery
    delivery = Delivery("DEL-001", grab, 5.5) # distance 5.5 km
    delivery.request_rider()
    order_2.add_delivery(delivery)
    order_2.status = OrderStatus.PENDING
    restaurant.add_order(order_2)

    # ==========================================
    # ORDER SCENARIO 3: Booking Event Order
    # ==========================================
    # First, create and pay deposit for the booking
    start_time = SimulationClock.get_time() + timedelta(days=1)
    time_slot = TimeSlot(start_time, 3) # 3 hours
    booking = Booking("BK-100", mock_member, room_vip, time_slot)
    
    # Mocking that booking deposit was already paid
    booking._Booking__status = BookingStatus.DEPOSIT_PAID
    restaurant.add_booking(booking)

    # Now create the order associated with this booking
    order_3 = Order(OrderType.EVENT, mock_member)
    if not hasattr(order_3, "_Order__order_item_list"):
        order_3._Order__order_item_list = []
    order_3.add_order_item(mock_menu_1, 10) # 1500
    order_3.add_order_item(mock_menu_2, 5)  # 400
    order_3.add_order_item(mock_menu_3, 10) # 400
    
    order_3.add_booking(booking)
    order_3.status = OrderStatus.PENDING
    restaurant.add_order(order_3)

    return True