from datetime import timedelta, datetime
from main_system.coupon import PercentCoupon, FixedAmountCoupon
from main_system.utils.enum import MemberTier, OrderType, OrderStatus, RoomType, PlatformName, BookingStatus, IngredientType, DeliveryStatus
from main_system.restaurant import Order, Staff, Member, Food, Ingredient, Item, Guest
from main_system.restaurant import SingleMenuItem, SetMenuItem
from main_system.external_platform.payment_method import Cash, QRCode, CreditCard
from main_system.booking import Room, TimeSlot, Booking
from main_system.external_platform.delivery_provider import Delivery, GrabDeliveryProvider, LineManDeliveryProvider, ShopeeFoodDeliveryProvider
from main_system.restaurant import restaurant
from main_system.utils.simulate import SimulationClock

def initialize_mock_data():
    # 1. Staff
    staff1 = Staff("S-101", "Alice Staff", "0801234567", "alice", "password")
    staff2 = Staff("S-102", "Bob Waiter", "0801234568", "bob", "password")
    staff3 = Staff("S-103", "Charlie Chef", "0801234569", "charlie", "password")
    admin1 = Staff("A-101", "Admin User", "0807654321", "admin", "admin", is_admin=True)
    admin2 = Staff("A-102", "Super Admin", "0807654322", "super", "admin", is_admin=True)
    
    for s in [staff1, staff2, staff3, admin1, admin2]:
        restaurant.add_staff(s)

    # 2. Members
    mem1 = Member("M-101", "David Silver", MemberTier.SILVER, "david", "password", "0812345678")
    mem2 = Member("M-102", "Eve Gold", MemberTier.GOLD, "eve", "password", "0812345679")
    mem3 = Member("M-103", "Frank Plat", MemberTier.GENERAL, "frank", "password", "0812345670")
    mem4 = Member("M-104", "Grace New", MemberTier.SILVER, "grace", "password", "0812345671")
    
    for m in [mem1, mem2, mem3, mem4]:
        restaurant.add_member(m)

    # 3. Stock Items (Ingredients)
    chicken = Item("Chicken", 30)
    beef = Item("Beef", 50)
    pork = Item("Pork", 40)
    fish = Item("Fish", 45)
    bread = Item("Bread", 5)
    cheese = Item("Cheese", 20)
    lettuce = Item("Lettuce", 10)
    tomato = Item("Tomato", 10)
    potato = Item("Potato", 15)
    rice = Item("Rice", 10)
    cola_syrup = Item("Cola Syrup", 5)
    water = Item("Water", 2)
    ketchup = Item("Ketchup", 2)
    bun = Item("Burger Bun", 10)

    for item, qty in [
        (chicken, 100), (beef, 50), (pork, 80), (fish, 40),
        (bread, 100), (cheese, 50), (lettuce, 50), (tomato, 50),
        (potato, 200), (rice, 100), (cola_syrup, 100), (water, 500),
        (ketchup, 100), (bun, 100)
    ]:
        restaurant.add_stock(item, qty)

    # 4. Menu Items
    # Recipes
    french_fries_recipe = [Ingredient(potato, 2, IngredientType.STRICT)]
    cola_recipe = [Ingredient(cola_syrup, 1, IngredientType.STRICT), Ingredient(water, 1, IngredientType.STRICT)]
    fried_chicken_recipe = [Ingredient(chicken, 1, IngredientType.STRICT)]
    burger_recipe = [
        Ingredient(bun, 1, IngredientType.STRICT),
        Ingredient(beef, 1, IngredientType.STRICT),
        Ingredient(cheese, 1, IngredientType.CUSTOMIZABLE),
        Ingredient(lettuce, 1, IngredientType.CUSTOMIZABLE),
        Ingredient(tomato, 1, IngredientType.CUSTOMIZABLE)
    ]
    chicken_burger_recipe = [
        Ingredient(bun, 1, IngredientType.STRICT),
        Ingredient(chicken, 1, IngredientType.STRICT),
        Ingredient(lettuce, 1, IngredientType.CUSTOMIZABLE)
    ]
    steak_recipe = [Ingredient(beef, 2, IngredientType.STRICT), Ingredient(potato, 1, IngredientType.CUSTOMIZABLE)]
    fish_chips_recipe = [Ingredient(fish, 1, IngredientType.STRICT), Ingredient(potato, 1, IngredientType.STRICT)]

    # Single Items
    french_fries = SingleMenuItem("French Fries", 80.0, timedelta(minutes=10), french_fries_recipe)
    cola = SingleMenuItem("Cola", 40.0, timedelta(minutes=2), cola_recipe)
    water_drink = SingleMenuItem("Mineral Water", 20.0, timedelta(minutes=1), [Ingredient(water, 1, IngredientType.STRICT)])
    fried_chicken = SingleMenuItem("Fried Chicken", 120.0, timedelta(minutes=15), fried_chicken_recipe)
    burger = SingleMenuItem("Beef Burger", 150.0, timedelta(minutes=15), burger_recipe)
    chicken_burger = SingleMenuItem("Chicken Burger", 130.0, timedelta(minutes=15), chicken_burger_recipe)
    steak = SingleMenuItem("Beef Steak", 350.0, timedelta(minutes=25), steak_recipe)
    fish_chips = SingleMenuItem("Fish and Chips", 200.0, timedelta(minutes=20), fish_chips_recipe)

    for menu in [french_fries, cola, water_drink, fried_chicken, burger, chicken_burger, steak, fish_chips]:
        restaurant.add_menu(menu)

    # Set Items
    party_chicken_set = SetMenuItem("Party Chicken Set", 500.0, [Food(fried_chicken, 4), Food(french_fries, 2), Food(cola, 4)])
    burger_combo = SetMenuItem("Burger Combo", 250.0, [Food(burger, 1), Food(french_fries, 1), Food(cola, 1)])
    couple_steak_set = SetMenuItem("Couple Steak Set", 800.0, [Food(steak, 2), Food(fish_chips, 1), Food(cola, 2)])
    family_feast = SetMenuItem("Family Feast", 1200.0, [Food(fried_chicken, 5), Food(burger, 2), Food(chicken_burger, 2), Food(french_fries, 3), Food(cola, 5)])

    for set_menu in [party_chicken_set, burger_combo, couple_steak_set, family_feast]:
        restaurant.add_menu(set_menu)

    # 5. Coupons
    cpn_20pct = PercentCoupon("CPN-01", "DISCOUNT20", 200.0, 20.0, max_usage=2)
    cpn_10pct = PercentCoupon("CPN-02", "SAVE10", 100.0, 10.0, max_usage=3)
    cpn_50thb = FixedAmountCoupon("CPN-03", "MINUS50", 150.0, 50.0, max_usage=1)
    cpn_100thb = FixedAmountCoupon("CPN-04", "MINUS100", 300.0, 100.0, max_usage=4)
    
    mem1.add_coupon(cpn_20pct)
    mem2.add_coupon(cpn_50thb)
    mem3.add_coupon(cpn_100thb)
    mem3.add_coupon(cpn_20pct)
    mem4.add_coupon(cpn_10pct)

    # 6. Payment Methods
    restaurant.add_payment_method(Cash("PAY-01", "cash"))
    restaurant.add_payment_method(QRCode("PAY-02", "qrcode"))
    restaurant.add_payment_method(CreditCard("PAY-03", "creditcard"))

    # 7. Delivery Providers
    grab = GrabDeliveryProvider()
    lineman = LineManDeliveryProvider()
    shopee = ShopeeFoodDeliveryProvider()
    for dp in [grab, lineman, shopee]:
        restaurant.add_delivery_provider(dp)

    # 8. Rooms
    rooms = [
        Room("R-VIP-01", RoomType.VIP), Room("R-VIP-02", RoomType.VIP), Room("R-VIP-03", RoomType.VIP),
        Room("R-HALL-01", RoomType.HALL), Room("R-HALL-02", RoomType.HALL), Room("R-HALL-03", RoomType.HALL)
    ]
    for r in rooms:
        restaurant.add_room(r)

    # 9. Orders Formulation
    
    # ORDER 1: General Order (Dine-in) - M-001 - COMPLETED
    order_1 = Order(mem1)
    if not hasattr(order_1, "_Order__order_item_list"): order_1._Order__order_item_list = []
    order_1.add_order_item(burger, 2)
    order_1.add_order_item(cola, 2)
    order_1.status = OrderStatus.CONFIRMED
    restaurant.add_order(order_1)

    # ORDER 2: General Order (Walk-in / Guest) - PENDING
    order_2 = Order(Guest())
    if not hasattr(order_2, "_Order__order_item_list"): order_2._Order__order_item_list = []
    order_2.add_order_item(chicken_burger, 1)
    order_2.add_order_item(french_fries, 1)
    order_2.add_order_item(water_drink, 1)
    order_2.status = OrderStatus.PENDING
    restaurant.add_order(order_2)

    # ORDER 3: Delivery Order (Grab) - M-002 - PENDING
    order_3 = Order(mem2)
    if not hasattr(order_3, "_Order__order_item_list"): order_3._Order__order_item_list = []
    order_3.add_order_item(family_feast, 1)
    
    del3 = Delivery("DEL-001", grab, 4.2)
    del3.request_rider()
    order_3.add_delivery(del3)
    order_3.status = OrderStatus.PENDING
    restaurant.add_order(order_3)

    # ORDER 4: Delivery Order (LineMan) - Guest - IN TRANSIT
    order_4 = Order(Guest())
    if not hasattr(order_4, "_Order__order_item_list"): order_4._Order__order_item_list = []
    order_4.add_order_item(couple_steak_set, 1)
    
    del4 = Delivery("DEL-002", lineman, 2.5)
    del4.request_rider()
    del4._Delivery__status = DeliveryStatus.IN_TRANSIT
    order_4.add_delivery(del4)
    order_4.status = OrderStatus.SERVED
    restaurant.add_order(order_4)

    # ORDER 5: Booking Event Order (VIP) - M-003 - COOKING
    start_time_5 = SimulationClock.get_time() + timedelta(days=2)
    time_slot_5 = TimeSlot(start_time_5, 4)
    booking_5 = Booking("BK-100", mem3, rooms[0], time_slot_5)
    booking_5._Booking__status = BookingStatus.DEPOSIT_PAID
    restaurant.add_booking(booking_5)

    order_5 = Order(mem3)
    if not hasattr(order_5, "_Order__order_item_list"): order_5._Order__order_item_list = []
    order_5.add_order_item(party_chicken_set, 3)
    order_5.add_order_item(burger_combo, 2)
    order_5.add_booking(booking_5)
    order_5.status = OrderStatus.COOKING
    restaurant.add_order(order_5)

    # ORDER 6: General Order (Dine-in) - M-004 - COOKING
    order_6 = Order(mem4)
    if not hasattr(order_6, "_Order__order_item_list"): order_6._Order__order_item_list = []
    order_6.add_order_item(burger, 1)
    order_6.add_order_item(cola, 1)
    order_6.status = OrderStatus.COOKING
    restaurant.add_order(order_6)

    # ORDER 7: General Order (Dine-in) - Guest - SERVED
    order_7 = Order(Guest())
    if not hasattr(order_7, "_Order__order_item_list"): order_7._Order__order_item_list = []
    order_7.add_order_item(steak, 2)
    order_7.add_order_item(water_drink, 2)
    order_7.status = OrderStatus.SERVED
    restaurant.add_order(order_7)

    # ORDER 8: Delivery Order (ShopeeFood) - M-001 - CANCELLED
    order_8 = Order(mem1)
    if not hasattr(order_8, "_Order__order_item_list"): order_8._Order__order_item_list = []
    order_8.add_order_item(french_fries, 2)
    order_8.status = OrderStatus.CANCELED
    restaurant.add_order(order_8)

    # ORDER 9: Booking Event Order (HALL) - M-002 - PENDING
    start_time_9 = SimulationClock.get_time() + timedelta(days=5)
    time_slot_9 = TimeSlot(start_time_9, 2)
    booking_9 = Booking("BK-101", mem2, rooms[3], time_slot_9)
    booking_9._Booking__status = BookingStatus.DEPOSIT_PAID
    restaurant.add_booking(booking_9)

    order_9 = Order(mem2)
    if not hasattr(order_9, "_Order__order_item_list"): order_9._Order__order_item_list = []
    order_9.add_order_item(family_feast, 2)
    order_9.add_booking(booking_9)
    order_9.status = OrderStatus.PENDING
    restaurant.add_order(order_9)
    
    return True