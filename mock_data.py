from datetime import timedelta, datetime
from main_system.coupon import PercentCoupon, FixedAmountCoupon
from main_system.enum import MemberTier, OrderType, OrderStatus, RoomType, PlatformName, BookingStatus, IngredientType
from main_system.restaurant import Order, Staff, Member, Food, Ingredient, Item
from main_system.restaurant import SingleMenuItem, SetMenuItem
from main_system.external_platform.payment_method import Cash, QRCode
from main_system.booking import Room, TimeSlot, Booking
from main_system.external_platform.delivery_provider import Delivery, GrabDeliveryProvider, LineManDeliveryProvider, ShopeeFoodDeliveryProvider
from main_system.restaurant import restaurant
from shared.utils.simulate import SimulationClock

def initialize_mock_data():
    # 1. Staff
    admin1 = Staff("A-001", "Kwang Admin", "0801111111", "Kwang", "password", True)
    staff1 = Staff("S-001", "Alice Manager", "0801111111", "alice", "password")
    staff2 = Staff("S-002", "Bob Cashier", "0802222222", "bob", "password")
    staff3 = Staff("S-003", "Charlie Kitchen", "0803333333", "charlie", "password")
    restaurant.add_staff(admin1)
    restaurant.add_staff(staff1)
    restaurant.add_staff(staff2)
    restaurant.add_staff(staff3)

    # 2. Member & Guest
    member_general = Member("M-001", "Dave Gen", MemberTier.GENERAL, "dave", "password", "0811111111")
    member_bronze = Member("M-002", "Eve Bronze", MemberTier.BRONZE, "eve", "password", "0812222222")
    member_silver = Member("M-003", "Frank Silver", MemberTier.SILVER, "frank", "password", "0813333333")
    member_gold = Member("M-004", "Grace Gold", MemberTier.GOLD, "grace", "password", "0814444444")
    restaurant.add_member(member_general)
    restaurant.add_member(member_bronze)
    restaurant.add_member(member_silver)
    restaurant.add_member(member_gold)

    # Guest isn't added to a specific list in restaurant normally, but we can use guest for orders
    # We will just instantiate it when needed.

    # 3. Inventory Stock
    chicken = Item("Chicken", 30)
    bread = Item("Bread", 5)
    cheese = Item("Cheese", 20)
    beef = Item("Beef", 40)
    lettuce = Item("Lettuce", 10)
    tomato = Item("Tomato", 10)
    potato = Item("Potato", 15)
    oil = Item("Oil", 5)
    soda_syrup = Item("Soda Syrup", 10)

    restaurant.add_stock(chicken, 100)
    restaurant.add_stock(bread, 50)
    restaurant.add_stock(cheese, 50)
    restaurant.add_stock(beef, 50)
    restaurant.add_stock(lettuce, 50)
    restaurant.add_stock(tomato, 50)
    restaurant.add_stock(potato, 100)
    restaurant.add_stock(oil, 50)
    restaurant.add_stock(soda_syrup, 100)

    # 4. Single Menu Items
    # Fried Chicken
    fk_recipe = [Ingredient(chicken, 1, IngredientType.STRICT), Ingredient(oil, 1, IngredientType.STRICT)]
    fried_chicken = SingleMenuItem("Fried Chicken", 45, timedelta(minutes=10), fk_recipe)
    restaurant.add_menu(fried_chicken)

    # Hamburger (Chicken)
    chk_burger_recipe = [
        Ingredient(bread, 1, IngredientType.STRICT),
        Ingredient(chicken, 1, IngredientType.STRICT),
        Ingredient(cheese, 1, IngredientType.CUSTOMIZABLE),
        Ingredient(lettuce, 1, IngredientType.CUSTOMIZABLE)
    ]
    chk_burger = SingleMenuItem("Chicken Burger", 80, timedelta(minutes=15), chk_burger_recipe)
    restaurant.add_menu(chk_burger)

    # Hamburger (Beef)
    beef_burger_recipe = [
        Ingredient(bread, 1, IngredientType.STRICT),
        Ingredient(beef, 1, IngredientType.STRICT),
        Ingredient(cheese, 1, IngredientType.CUSTOMIZABLE),
        Ingredient(tomato, 1, IngredientType.CUSTOMIZABLE)
    ]
    beef_burger = SingleMenuItem("Beef Burger", 100, timedelta(minutes=15), beef_burger_recipe)
    restaurant.add_menu(beef_burger)

    # French Fries
    fries_recipe = [Ingredient(potato, 1, IngredientType.STRICT), Ingredient(oil, 1, IngredientType.STRICT)]
    fries = SingleMenuItem("French Fries", 40, timedelta(minutes=8), fries_recipe)
    restaurant.add_menu(fries)

    # Cola
    cola_recipe = [Ingredient(soda_syrup, 1, IngredientType.STRICT)]
    cola = SingleMenuItem("Cola", 25, timedelta(minutes=2), cola_recipe)
    restaurant.add_menu(cola)

    # 5. Set Menu Items
    party_set_recipe = [Food(fried_chicken, 5), Food(fries, 2), Food(cola, 2)]
    party_set = SetMenuItem("Party Set", 280, party_set_recipe) # Discounted from 5*45+2*40+2*25 = 355
    restaurant.add_menu(party_set)

    burger_set_recipe = [Food(beef_burger, 1), Food(fries, 1), Food(cola, 1)]
    burger_set = SetMenuItem("Beef Burger Combo", 150, burger_set_recipe) # Discounted from 100+40+25 = 165
    restaurant.add_menu(burger_set)


    # 6. Coupons
    coupon_20pct = PercentCoupon("CPN-PCT-20", "DISCOUNT20", 200.0, 20.0)
    coupon_minus50 = FixedAmountCoupon("CPN-FIX-50", "MINUS50", 150.0, 50.0)
    member_gold.add_coupon(coupon_20pct)
    member_silver.add_coupon(coupon_minus50)

    # 7. Payment Methods
    cash = Cash("PAY-CASH-01", "cash")
    qrcode = QRCode("PAY-QR-01", "qrcode")
    restaurant.add_payment_method(cash)
    restaurant.add_payment_method(qrcode)

    # 8. Delivery Providers
    grab = GrabDeliveryProvider()
    lineman = LineManDeliveryProvider()
    shopee = ShopeeFoodDeliveryProvider()
    restaurant.add_delivery_provider(grab)
    restaurant.add_delivery_provider(lineman)
    restaurant.add_delivery_provider(shopee)

    # 9. Rooms
    room_vip1 = Room("R-VIP-01", RoomType.VIP)
    room_vip2 = Room("R-VIP-02", RoomType.VIP)
    room_standard1 = Room("R-STD-01", RoomType.STANDARD)
    room_hall1 = Room("R-HALL-01", RoomType.HALL)
    restaurant.add_room(room_vip1)
    restaurant.add_room(room_vip2)
    restaurant.add_room(room_standard1)
    restaurant.add_room(room_hall1)


    # ==========================================
    # ORDERS
    # ==========================================

    # O-01: General Order, PENDING (Guest)
    order_1 = Order(OrderType.GENERAL, member_general)
    if not hasattr(order_1, "_Order__order_item_list"): order_1._Order__order_item_list = []
    order_1.add_order_item(chk_burger, 2)
    order_1.add_order_item(cola, 2)
    order_1.status = OrderStatus.PENDING
    restaurant.add_order(order_1)

    # O-02: General Order, COOKING (Gold Member)
    order_2 = Order(OrderType.GENERAL, member_gold)
    if not hasattr(order_2, "_Order__order_item_list"): order_2._Order__order_item_list = []
    order_2.add_order_item(party_set, 1)
    order_2.add_order_item(beef_burger, 1)
    order_2.status = OrderStatus.COOKING
    restaurant.add_order(order_2)

    # O-03: General Order, READY (Bronze Member)
    order_3 = Order(OrderType.GENERAL, member_bronze)
    if not hasattr(order_3, "_Order__order_item_list"): order_3._Order__order_item_list = []
    order_3.add_order_item(fried_chicken, 3)
    order_3.status = OrderStatus.READY
    restaurant.add_order(order_3)

    # O-04: Delivery Order (ShopeeFood), PENDING (Silver Member)
    order_4 = Order(OrderType.DELIVERY, member_silver)
    if not hasattr(order_4, "_Order__order_item_list"): order_4._Order__order_item_list = []
    order_4.add_order_item(burger_set, 1)
    order_4.add_order_item(fried_chicken, 2)
    deliv_shopee = Delivery("DEL-SHP-01", shopee, 3.0) 
    deliv_shopee.request_rider()
    order_4.add_delivery(deliv_shopee)
    order_4.status = OrderStatus.PENDING
    restaurant.add_order(order_4)

    # O-05: Delivery Order (Grab), PAIDED (General Member)
    order_5 = Order(OrderType.DELIVERY, member_general)
    if not hasattr(order_5, "_Order__order_item_list"): order_5._Order__order_item_list = []
    order_5.add_order_item(party_set, 2)
    deliv_grab = Delivery("DEL-GRB-01", grab, 8.5) 
    deliv_grab.request_rider()
    order_5.add_delivery(deliv_grab)
    order_5.status = OrderStatus.PAID
    restaurant.add_order(order_5)

    # O-06: Event Order (VIP Room) - Deposit Paid, PENDING
    start_time_evt = SimulationClock.get_time() + timedelta(days=2)
    time_slot_evt = TimeSlot(start_time_evt, 4)
    booking_evt = Booking("BK-001", member_gold, room_vip1, time_slot_evt)
    booking_evt.status = BookingStatus.DEPOSIT_PAID
    restaurant.add_booking(booking_evt)

    order_6 = Order(OrderType.EVENT, member_gold)
    if not hasattr(order_6, "_Order__order_item_list"): order_6._Order__order_item_list = []
    order_6.add_order_item(party_set, 3)
    order_6.add_order_item(burger_set, 5)
    order_6.add_booking(booking_evt)
    order_6.status = OrderStatus.PENDING
    restaurant.add_order(order_6)
    
    # O-07: Event Order (HALL Room) - Checked In, COOKING
    start_time_hall = SimulationClock.get_time() - timedelta(hours=1)
    time_slot_hall = TimeSlot(start_time_hall, 5)
    booking_hall = Booking("BK-002", member_silver, room_hall1, time_slot_hall)
    booking_hall.status = BookingStatus.CHECKED_IN
    restaurant.add_booking(booking_hall)
    room_hall1.mark_room_in_use()

    order_7 = Order(OrderType.EVENT, member_silver)
    if not hasattr(order_7, "_Order__order_item_list"): order_7._Order__order_item_list = []
    order_7.add_order_item(fried_chicken, 20)
    order_7.add_order_item(fries, 10)
    order_7.add_order_item(cola, 10)
    order_7.add_booking(booking_hall)
    order_7.status = OrderStatus.COOKING
    restaurant.add_order(order_7)

    # O-08: General Order, CANCELED
    order_8 = Order(OrderType.GENERAL, member_general)
    if not hasattr(order_8, "_Order__order_item_list"): order_8._Order__order_item_list = []
    order_8.add_order_item(beef_burger, 1)
    order_8.status = OrderStatus.CANCELED
    restaurant.add_order(order_8)

    return True