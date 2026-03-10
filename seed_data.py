"""
Seed Data Module
================
Seeds demo data for the ZomaClone application.
This is called on server startup to populate the database with sample data.
"""

def seed_demo_data(db):
    """
    Seed demo data into the database.
    This function is called from server.py on startup.
    """
    from datetime import datetime
    import random
    
    print(" Seeding demo data...")
    
    # Import models from server
    from server import (
        Vendor, Restaurant, MenuItem, RestaurantConfig,
        NightlifeVendorConfig, NightlifeSlot, NightlifeTableType,
        Club, ClubImage, NightlifeItem, User
    )
    
    # Check if data already exists
    existing_vendors = Vendor.query.count()
    if existing_vendors > 0:
        print(f"️ Database already has {existing_vendors} vendors. Skipping seed.")
        return
    
    # Create demo users
    print(" Creating demo users...")
    users = [
        User(name="John Doe", email="john@example.com", phone="+919999999901"),
        User(name="Jane Smith", email="jane@example.com", phone="+919999999902"),
        User(name="Mike Johnson", email="mike@example.com", phone="+919999999903"),
    ]
    for u in users:
        db.session.add(u)
    db.session.commit()
    print(f"✅ Created {len(users)} users")
    
    # Create demo vendors (restaurants and nightlife)
    print(" Creating demo vendors...")
    vendors = [
        Vendor(
            restaurant_name="Urban Bites",
            owner_name="Rahul Kumar",
            email="urban@test.com",
            phone="+919876543210",
            address="123 Food Street, Mumbai",
            vendor_type="restaurant"
        ),
        Vendor(
            restaurant_name="Pizza Paradise",
            owner_name="Priya Sharma",
            email="pizza@test.com",
            phone="+919876543211",
            address="456 Pizza Lane, Delhi",
            vendor_type="restaurant"
        ),
        Vendor(
            restaurant_name="Club Havana",
            owner_name="Amit Patel",
            email="havana@test.com",
            phone="+919876543212",
            address="789 Night Blvd, Mumbai",
            vendor_type="nightlife"
        ),
        Vendor(
            restaurant_name="Skye Lounge",
            owner_name="Raj Mehta",
            email="skye@test.com",
            phone="+919876543213",
            address="321 Sky Ave, Bangalore",
            vendor_type="nightlife"
        ),
    ]
    for v in vendors:
        db.session.add(v)
    db.session.commit()
    print(f"✅ Created {len(vendors)} vendors")
    
    # Create restaurants for restaurant vendors
    print("️ Creating restaurants...")
    restaurants = [
        Restaurant(
            vendor_id=1,
            name="Urban Bites",
            address="123 Food Street, Mumbai",
            description="Best multi-cuisine restaurant in town",
            is_nightlife=False,
            banner_image="/Images/food.png"
        ),
        Restaurant(
            vendor_id=2,
            name="Pizza Paradise",
            address="456 Pizza Lane, Delhi",
            description="Authentic Italian pizzas and pasta",
            is_nightlife=False,
            banner_image="/Images/food.png"
        ),
    ]
    for r in restaurants:
        db.session.add(r)
    db.session.commit()
    
    # Create restaurant configs
    for r in restaurants:
        cfg = RestaurantConfig(
            restaurant_id=r.id,
            delivery_charge=30,
            packing_charge=20
        )
        db.session.add(cfg)
    db.session.commit()
    print(f"✅ Created {len(restaurants)} restaurants with configs")
    
    # Create menu items for restaurants
    print(" Creating menu items...")
    menu_items = [
        # Urban Bites menu
        MenuItem(restaurant_id=1, name="Chicken Biryani", description="Aromatic basmati rice with spiced chicken", price=350, category="Biryani", food_type="non-veg"),
        MenuItem(restaurant_id=1, name="Paneer Tikka", description="Grilled cottage cheese with spices", price=280, category="Vegetarian", food_type="veg"),
        MenuItem(restaurant_id=1, name="Butter Chicken", description="Creamy tomato gravy with chicken", price=400, category="Curry", food_type="non-veg"),
        MenuItem(restaurant_id=1, name="Dal Makhani", description="Slow cooked black lentils", price=250, category="Vegetarian", food_type="veg"),
        MenuItem(restaurant_id=1, name="Garlic Naan", description="Soft bread with garlic", price=60, category="Breads", food_type="veg"),
        # Pizza Paradise menu
        MenuItem(restaurant_id=2, name="Margherita Pizza", description="Classic tomato and mozzarella", price=450, category="Pizza", food_type="veg"),
        MenuItem(restaurant_id=2, name="Pepperoni Pizza", description="Loaded with pepperoni", price=550, category="Pizza", food_type="non-veg"),
        MenuItem(restaurant_id=2, name="Chicken Alfredo", description="Creamy pasta with chicken", price=400, category="Pasta", food_type="non-veg"),
        MenuItem(restaurant_id=2, name="Vegetable Lasagna", description="Layers of pasta and vegetables", price=380, category="Pasta", food_type="veg"),
    ]
    for item in menu_items:
        db.session.add(item)
    db.session.commit()
    print(f"✅ Created {len(menu_items)} menu items")
    
    # Create nightlife configs and table types
    print("🎉 Creating nightlife venues...")
    nightlife_configs = [
        NightlifeVendorConfig(
            vendor_id=3,
            venue_name="Club Havana",
            addr1="789 Night Blvd",
            city="Mumbai",
            state="Maharashtra",
            pincode="400001",
            banner_url="/Images/club.webp"
        ),
        NightlifeVendorConfig(
            vendor_id=4,
            venue_name="Skye Lounge",
            addr1="321 Sky Ave",
            city="Bangalore",
            state="Karnataka",
            pincode="560001",
            banner_url="/Images/club.webp"
        ),
    ]
    for cfg in nightlife_configs:
        db.session.add(cfg)
    db.session.commit()
    
    # Create nightlife slots
    for vendor_id in [3, 4]:
        slots = [
            NightlifeSlot(vendor_id=vendor_id, name="Early Bird", start_time="18:00", end_time="21:00"),
            NightlifeSlot(vendor_id=vendor_id, name="Prime Time", start_time="21:00", end_time="23:00"),
            NightlifeSlot(vendor_id=vendor_id, name="Late Night", start_time="23:00", end_time="02:00"),
        ]
        for s in slots:
            db.session.add(s)
    db.session.commit()
    
    # Create nightlife table types
    table_types = [
        # Club Havana
        NightlifeTableType(vendor_id=3, name="Standard Table", seats=4, total_tables=10, price=1500),
        NightlifeTableType(vendor_id=3, name="Premium Table", seats=6, total_tables=5, price=3000),
        NightlifeTableType(vendor_id=3, name="VIP Booth", seats=10, total_tables=2, price=8000),
        # Skye Lounge
        NightlifeTableType(vendor_id=4, name="Standard Table", seats=4, total_tables=8, price=1200),
        NightlifeTableType(vendor_id=4, name="Premium Table", seats=6, total_tables=4, price=2500),
        NightlifeTableType(vendor_id=4, name="VIP Booth", seats=12, total_tables=2, price=10000),
    ]
    for tt in table_types:
        db.session.add(tt)
    db.session.commit()
    print(f"✅ Created nightlife venues with {len(table_types)} table types")
    
    # Create nightlife menu items
    print(" Creating nightlife menu items...")
    nightlife_items = [
        # Club Havana
        NightlifeItem(vendor_id=3, item_name="Whisky Glass", description="Premium whisky served neat", price=450, category="Drinks"),
        NightlifeItem(vendor_id=3, item_name="Vodka Pitcher", description="Vodka with mixers", price=650, category="Drinks"),
        NightlifeItem(vendor_id=3, item_name="Cocktail Special", description="House special cocktail", price=350, category="Drinks"),
        NightlifeItem(vendor_id=3, item_name="Nachos", description="Crispy nachos with cheese", price=250, category="Snacks"),
        NightlifeItem(vendor_id=3, item_name="Chicken Wings", description="Spicy chicken wings", price=350, category="Snacks"),
        # Skye Lounge
        NightlifeItem(vendor_id=4, item_name="Beer Pitcher", description="Assorted beer pitcher", price=400, category="Drinks"),
        NightlifeItem(vendor_id=4, item_name="Rum Glass", description="Premium rum", price=400, category="Drinks"),
        NightlifeItem(vendor_id=4, item_name="Mocktail", description="Refreshing non-alcoholic drink", price=200, category="Drinks"),
        NightlifeItem(vendor_id=4, item_name="Fries", description="Crispy french fries", price=150, category="Snacks"),
    ]
    for item in nightlife_items:
        db.session.add(item)
    db.session.commit()
    print(f"✅ Created {len(nightlife_items)} nightlife menu items")
    
    print("🌱 Demo data seeding complete!")
    print("=" * 50)
    print(" Demo Credentials:")
    print("   User: john@example.com / +919999999901")
    print("   Vendor: urban@test.com / +919876543210")
    print("   Admin: admin@zoma.com / admin123")
    print("=" * 50)
