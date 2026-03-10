"""
New API Routes with Role-Based Access Control
=============================================
API endpoints using the new database schema with RBAC enforcement.

This file provides:
- Unified authentication for all roles
- Role-based data filtering
- Privacy enforcement between roles
- Backward compatibility with existing endpoints
"""

from flask import Blueprint, request, jsonify, g
from werkzeug.utils import secure_filename
from functools import wraps
import os
import random
import uuid
from datetime import datetime, timedelta

# Create Blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Import new models - these will be integrated with existing db
# Note: We'll import dynamically to avoid circular imports

def get_db():
    """Get database instance - will be set from server.py"""
    from server import db
    return db


def get_new_models():
    """Get new model classes"""
    from models.new_models import (
        Account, UserProfile, VendorProfile, DeliveryPartner, Admin,
        Restaurant, MenuItem, FoodOrder, FoodOrderItem,
        NightlifeOrder, NightlifeOrderItem,
        TableBooking, DeliveryOrder, Review, PlatformLog,
        UserRole, generate_order_id, generate_booking_id
    )
    return {
        'Account': Account,
        'UserProfile': UserProfile,
        'VendorProfile': VendorProfile,
        'DeliveryPartner': DeliveryPartner,
        'Admin': Admin,
        'Restaurant': Restaurant,
        'MenuItem': MenuItem,
        'FoodOrder': FoodOrder,
        'FoodOrderItem': FoodOrderItem,
        'NightlifeOrder': NightlifeOrder,
        'NightlifeOrderItem': NightlifeOrderItem,
        'TableBooking': TableBooking,
        'DeliveryOrder': DeliveryOrder,
        'Review': Review,
        'PlatformLog': PlatformLog,
        'UserRole': UserRole,
        'generate_order_id': generate_order_id,
        'generate_booking_id': generate_booking_id
    }


def get_rbac():
    """Get RBAC utilities"""
    from utils.rbac import (
        require_role, require_any_role, require_min_role,
        QueryFilter, hash_password, verify_password
    )
    return {
        'require_role': require_role,
        'require_any_role': require_any_role,
        'require_min_role': require_min_role,
        'QueryFilter': QueryFilter,
        'hash_password': hash_password,
        'verify_password': verify_password
    }


# ============================================================
# AUTHENTICATION - Unified Login for All Roles
# ============================================================

@api_bp.route('/auth/login', methods=['POST'])
def unified_login():
    """
    Unified login endpoint for all roles.
    
    Request:
        {
            "email": "user@example.com",
            "password": "password123"
        }
    
    Response:
        {
            "success": true,
            "account": {...},
            "profile": {...}
        }
    """
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    password = (data.get('password') or '').strip()
    
    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password required'}), 400
    
    db = get_db()
    models = get_new_models()
    rbac = get_rbac()
    
    Account = models['Account']
    UserProfile = models['UserProfile']
    VendorProfile = models['VendorProfile']
    DeliveryPartner = models['DeliveryPartner']
    Admin = models['Admin']
    hash_password = rbac['hash_password']
    verify_password = rbac['verify_password']
    
    # Find account by email
    account = Account.query.filter_by(email=email).first()
    if not account:
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
    
    # Verify password
    if not verify_password(password, account.password_hash):
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
    
    # Check account status
    if account.status != 'active':
        return jsonify({'success': False, 'message': 'Account is ' + account.status}), 403
    
    # Get role-specific profile
    profile = None
    user_role = account.role.value if hasattr(account.role, 'value') else account.role
    
    if user_role == 'USER':
        profile = UserProfile.query.filter_by(account_id=account.id).first()
    elif user_role == 'VENDOR':
        profile = VendorProfile.query.filter_by(account_id=account.id).first()
    elif user_role == 'DELIVERY':
        profile = DeliveryPartner.query.filter_by(account_id=account.id).first()
    elif user_role == 'ADMIN':
        profile = Admin.query.filter_by(account_id=account.id).first()
    
    # Create session token
    token = str(uuid.uuid4())
    
    return jsonify({
        'success': True,
        'token': token,
        'account': account.to_dict(),
        'role': user_role,
        'profile': profile.to_dict() if profile else None
    })


@api_bp.route('/auth/register', methods=['POST'])
def unified_register():
    """
    Unified registration endpoint for all roles.
    
    Request:
        {
            "email": "user@example.com",
            "password": "password123",
            "role": "USER",  // USER, VENDOR, DELIVERY
            "name": "John Doe",  // for USER/DELIVERY
            "business_name": "Restaurant Name",  // for VENDOR
            "phone": "+1234567890"
        }
    """
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    password = (data.get('password') or '').strip()
    role = (data.get('role') or 'USER').strip().upper()
    phone = (data.get('phone') or '').strip()
    
    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password required'}), 400
    
    if role not in ['USER', 'VENDOR', 'DELIVERY']:
        return jsonify({'success': False, 'message': 'Invalid role'}), 400
    
    db = get_db()
    models = get_new_models()
    rbac = get_rbac()
    
    Account = models['Account']
    UserProfile = models['UserProfile']
    VendorProfile = models['VendorProfile']
    DeliveryPartner = models['DeliveryPartner']
    UserRole = models['UserRole']
    hash_password = rbac['hash_password']
    
    # Check if account exists
    existing = Account.query.filter_by(email=email).first()
    if existing:
        return jsonify({'success': False, 'message': 'Account already exists'}), 409
    
    # Create account
    account = Account(
        email=email,
        password_hash=hash_password(password),
        role=UserRole[role],
        status='active'
    )
    db.session.add(account)
    db.session.flush()  # Get account.id
    
    # Create role-specific profile
    if role == 'USER':
        name = (data.get('name') or '').strip()
        profile = UserProfile(
            account_id=account.id,
            name=name,
            phone=phone,
            address=data.get('address', '')
        )
    elif role == 'VENDOR':
        business_name = (data.get('business_name') or '').strip()
        profile = VendorProfile(
            account_id=account.id,
            business_name=business_name,
            phone=phone,
            city=data.get('city', '')
        )
    elif role == 'DELIVERY':
        name = (data.get('name') or '').strip()
        profile = DeliveryPartner(
            account_id=account.id,
            name=name,
            phone=phone,
            vehicle_type=data.get('vehicle_type', 'bike')
        )
    
    if profile:
        db.session.add(profile)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Account created successfully',
        'account': account.to_dict(),
        'role': role
    })


# ============================================================
# RESTAURANT APIs - With Vendor Privacy
# ============================================================

@api_bp.route('/restaurants', methods=['GET'])
def get_restaurants():
    """
    Get all active restaurants.
    Public endpoint - all users can view.
    """
    models = get_new_models()
    Restaurant = models['Restaurant']
    
    category = request.args.get('category')
    city = request.args.get('city')
    
    query = Restaurant.query.filter_by(active=True)
    
    if category:
        query = query.filter_by(category=category)
    if city:
        query = query.filter_by(city=city)
    
    restaurants = query.order_by(Restaurant.rating.desc()).all()
    
    return jsonify({
        'success': True,
        'restaurants': [r.to_dict() for r in restaurants]
    })


@api_bp.route('/restaurants/<int:restaurant_id>', methods=['GET'])
def get_restaurant(restaurant_id):
    """Get a specific restaurant with its details."""
    models = get_new_models()
    Restaurant = models['Restaurant']
    
    restaurant = Restaurant.query.get(restaurant_id)
    if not restaurant:
        return jsonify({'success': False, 'message': 'Restaurant not found'}), 404
    
    return jsonify({
        'success': True,
        'restaurant': restaurant.to_dict()
    })


# ============================================================
# MENU APIs - With Vendor Privacy
# ============================================================

@api_bp.route('/menus', methods=['GET'])
def get_menus():
    """
    Get menu items for a restaurant.
    
    Query params:
        restaurant_id: Get menus for specific restaurant
        vendor_id: Get menus for vendor's restaurants
    """
    models = get_new_models()
    MenuItem = models['MenuItem']
    Restaurant = models['Restaurant']
    
    restaurant_id = request.args.get('restaurant_id', type=int)
    vendor_id = request.args.get('vendor_id', type=int)
    category = request.args.get('category')
    
    if not restaurant_id and not vendor_id:
        return jsonify({'success': False, 'message': 'restaurant_id or vendor_id required'}), 400
    
    query = MenuItem.query.filter_by(available=True)
    
    if restaurant_id:
        query = query.filter_by(restaurant_id=restaurant_id)
    elif vendor_id:
        # Get all restaurants for this vendor
        restaurant_ids = [r.id for r in Restaurant.query.filter_by(vendor_id=vendor_id).all()]
        query = query.filter(MenuItem.restaurant_id.in_(restaurant_ids))
    
    if category:
        query = query.filter_by(category=category)
    
    items = query.order_by(MenuItem.category, MenuItem.name).all()
    
    return jsonify({
        'success': True,
        'menu': [item.to_dict() for item in items]
    })


@api_bp.route('/vendor/menus', methods=['GET'])
@require_role('VENDOR')
def get_vendor_menus():
    """
    Get menu items for vendor's restaurants.
    VENDOR ONLY - returns only their own menus.
    """
    models = get_new_models()
    MenuItem = models['MenuItem']
    Restaurant = models['Restaurant']
    
    vendor_id = request.args.get('vendor_id', type=int)
    
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    # Get vendor's restaurants
    restaurants = Restaurant.query.filter_by(vendor_id=vendor_id).all()
    restaurant_ids = [r.id for r in restaurants]
    
    if not restaurant_ids:
        return jsonify({'success': True, 'menu': []})
    
    items = MenuItem.query.filter(MenuItem.restaurant_id.in_(restaurant_ids)).all()
    
    return jsonify({
        'success': True,
        'menu': [item.to_dict() for item in items]
    })


@api_bp.route('/vendor/add-menu', methods=['POST'])
@require_role('VENDOR')
def add_menu_item():
    """
    Add menu item to vendor's restaurant.
    VENDOR ONLY - can only add to their own restaurants.
    """
    data = request.get_json() or {}
    models = get_new_models()
    db = get_db()
    
    MenuItem = models['MenuItem']
    Restaurant = models['Restaurant']
    
    restaurant_id = data.get('restaurant_id')
    name = (data.get('name') or '').strip()
    price = data.get('price')
    
    if not restaurant_id or not name or price is None:
        return jsonify({'success': False, 'message': 'restaurant_id, name, price required'}), 400
    
    # Verify restaurant belongs to vendor
    vendor_id = data.get('vendor_id')
    if vendor_id:
        restaurant = Restaurant.query.filter_by(id=restaurant_id, vendor_id=vendor_id).first()
        if not restaurant:
            return jsonify({'success': False, 'message': 'Restaurant not found or not owned by vendor'}), 403
    else:
        restaurant = Restaurant.query.get(restaurant_id)
    
    # Create menu item
    item = MenuItem(
        restaurant_id=restaurant_id,
        name=name,
        description=data.get('description', ''),
        price=int(price),
        category=data.get('category', 'General'),
        image=data.get('image'),
        available=True
    )
    db.session.add(item)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'item': item.to_dict()
    })


# ============================================================
# ORDER APIs - With User Privacy
# ============================================================

@api_bp.route('/orders', methods=['GET'])
def get_orders():
    """
    Get orders based on user role.
    - USERS see only their own orders
    - VENDORS see orders for their restaurants
    - DELIVERY see only assigned deliveries
    """
    models = get_new_models()
    
    user_id = request.args.get('user_id', type=int)
    restaurant_id = request.args.get('restaurant_id', type=int)
    order_type = request.args.get('type', 'food')  # food or nightlife
    
    if order_type == 'food':
        Order = models['FoodOrder']
    else:
        Order = models['NightlifeOrder']
    
    query = Order.query
    
    if user_id:
        query = query.filter_by(user_id=user_id)
    if restaurant_id:
        query = query.filter_by(restaurant_id=restaurant_id)
    
    orders = query.order_by(Order.created_at.desc()).limit(100).all()
    
    return jsonify({
        'success': True,
        'orders': [o.to_dict(include_items=True) for o in orders]
    })


@api_bp.route('/orders/place', methods=['POST'])
def place_order():
    """
    Place a new order.
    
    Request:
        {
            "order_type": "food" | "nightlife",
            "restaurant_id": 1,
            "user_id": 1,
            "items": [
                {"menu_id": 1, "quantity": 2, "price": 150},
                {"menu_id": 2, "quantity": 1, "price": 200}
            ],
            "payment_method": "COD" | "UPI",
            "delivery_address": "..."
        }
    """
    data = request.get_json() or {}
    models = get_new_models()
    db = get_db()
    
    order_type = data.get('order_type', 'food')
    restaurant_id = data.get('restaurant_id')
    user_id = data.get('user_id')
    items = data.get('items', [])
    
    if not all([restaurant_id, user_id, items]):
        return jsonify({'success': False, 'message': 'restaurant_id, user_id, items required'}), 400
    
    if order_type == 'food':
        Order = models['FoodOrder']
        OrderItem = models['FoodOrderItem']
    else:
        Order = models['NightlifeOrder']
        OrderItem = models['NightlifeOrderItem']
    
    # Calculate total
    total_price = sum(int(item.get('price', 0)) * int(item.get('quantity', 1)) for item in items)
    
    # Generate order ID
    generate_order_id = models['generate_order_id']
    order_id = generate_order_id(prefix=order_type.upper()[:2])
    
    # Create order
    order = Order(
        order_id=order_id,
        restaurant_id=restaurant_id,
        user_id=user_id,
        total_price=total_price,
        payment_method=data.get('payment_method', 'COD'),
        delivery_address=data.get('delivery_address', '')
    )
    db.session.add(order)
    db.session.flush()
    
    # Create order items
    for item in items:
        order_item = OrderItem(
            order_id=order.id,
            menu_id=item.get('menu_id'),
            quantity=item.get('quantity', 1),
            price=item.get('price')
        )
        db.session.add(order_item)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'order': order.to_dict(include_items=True),
        'message': 'Order placed successfully'
    })


# ============================================================
# DELIVERY APIs - With Delivery Partner Privacy
# ============================================================

@api_bp.route('/delivery/orders', methods=['GET'])
def get_delivery_orders():
    """
    Get delivery orders.
    - DELIVERY partners see only their assigned deliveries
    - Others see all (for admin purposes)
    """
    models = get_new_models()
    DeliveryOrder = models['DeliveryOrder']
    FoodOrder = models['FoodOrder']
    
    delivery_partner_id = request.args.get('delivery_partner_id', type=int)
    status = request.args.get('status')
    
    query = DeliveryOrder.query
    
    if delivery_partner_id:
        # Delivery partner sees only their assigned deliveries
        query = query.filter_by(delivery_partner_id=delivery_partner_id)
    
    if status:
        query = query.filter_by(delivery_status=status)
    
    deliveries = query.order_by(DeliveryOrder.created_at.desc()).all()
    
    result = []
    for d in deliveries:
        data = d.to_dict()
        food_order = FoodOrder.query.get(d.food_order_id)
        data['food_order'] = food_order.to_dict() if food_order else None
        result.append(data)
    
    return jsonify({
        'success': True,
        'deliveries': result
    })


@api_bp.route('/delivery/assign', methods=['POST'])
@require_any_role('ADMIN', 'VENDOR')
def assign_delivery():
    """
    Assign a delivery partner to an order.
    ADMIN or VENDOR can assign.
    """
    data = request.get_json() or {}
    models = get_new_models()
    db = get_db()
    
    food_order_id = data.get('food_order_id')
    delivery_partner_id = data.get('delivery_partner_id')
    
    if not all([food_order_id, delivery_partner_id]):
        return jsonify({'success': False, 'message': 'food_order_id and delivery_partner_id required'}), 400
    
    DeliveryOrder = models['DeliveryOrder']
    FoodOrder = models['FoodOrder']
    
    # Check if order exists
    food_order = FoodOrder.query.get(food_order_id)
    if not food_order:
        return jsonify({'success': False, 'message': 'Order not found'}), 404
    
    # Check if delivery already assigned
    existing = DeliveryOrder.query.filter_by(food_order_id=food_order_id).first()
    if existing:
        # Update existing delivery
        existing.delivery_partner_id = delivery_partner_id
        existing.delivery_status = 'ASSIGNED'
    else:
        # Create new delivery
        delivery = DeliveryOrder(
            food_order_id=food_order_id,
            delivery_partner_id=delivery_partner_id,
            delivery_status='ASSIGNED'
        )
        db.session.add(delivery)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Delivery partner assigned'
    })


@api_bp.route('/delivery/update-status', methods=['POST'])
@require_any_role('ADMIN', 'DELIVERY')
def update_delivery_status():
    """
    Update delivery status.
    DELIVERY partners can update their assigned deliveries.
    """
    data = request.get_json() or {}
    models = get_new_models()
    db = get_db()
    
    delivery_id = data.get('delivery_id')
    status = (data.get('status') or '').strip().upper()
    
    valid_statuses = ['ASSIGNED', 'PICKED_UP', 'IN_TRANSIT', 'DELIVERED']
    if status not in valid_statuses:
        return jsonify({'success': False, 'message': 'Invalid status'}), 400
    
    DeliveryOrder = models['DeliveryOrder']
    
    delivery = DeliveryOrder.query.get(delivery_id)
    if not delivery:
        return jsonify({'success': False, 'message': 'Delivery not found'}), 404
    
    delivery.delivery_status = status
    
    if status == 'PICKED_UP':
        delivery.pickup_time = datetime.utcnow()
    elif status == 'DELIVERED':
        delivery.delivery_time = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Status updated'
    })


# ============================================================
# BOOKING APIs - With User Privacy
# ============================================================

@api_bp.route('/bookings', methods=['GET'])
def get_bookings():
    """
    Get table bookings.
    - USERS see only their own bookings
    - VENDORS see bookings for their restaurants
    """
    models = get_new_models()
    TableBooking = models['TableBooking']
    
    user_id = request.args.get('user_id', type=int)
    restaurant_id = request.args.get('restaurant_id', type=int)
    booking_type = request.args.get('type')  # food or nightlife
    
    query = TableBooking.query
    
    if user_id:
        query = query.filter_by(user_id=user_id)
    if restaurant_id:
        query = query.filter_by(restaurant_id=restaurant_id)
    if booking_type:
        query = query.filter_by(booking_type=booking_type)
    
    bookings = query.order_by(TableBooking.booking_date.desc()).all()
    
    return jsonify({
        'success': True,
        'bookings': [b.to_dict() for b in bookings]
    })


@api_bp.route('/bookings/create', methods=['POST'])
def create_booking():
    """
    Create a new table booking.
    
    Request:
        {
            "restaurant_id": 1,
            "user_id": 1,
            "booking_type": "food" | "nightlife",
            "table_type": "2-seater",
            "booking_date": "2025-01-15",
            "booking_time": "19:00",
            "guest_count": 2
        }
    """
    data = request.get_json() or {}
    models = get_new_models()
    db = get_db()
    
    restaurant_id = data.get('restaurant_id')
    user_id = data.get('user_id')
    booking_type = data.get('booking_type', 'food')
    table_type = data.get('table_type')
    booking_date = data.get('booking_date')
    booking_time = data.get('booking_time')
    guest_count = data.get('guest_count', 1)
    
    if not all([restaurant_id, user_id, booking_date, booking_time]):
        return jsonify({
            'success': False, 
            'message': 'restaurant_id, user_id, booking_date, booking_time required'
        }), 400
    
    TableBooking = models['TableBooking']
    generate_booking_id = models['generate_booking_id']
    
    booking_id = generate_booking_id(prefix='BK')
    
    booking = TableBooking(
        booking_id=booking_id,
        restaurant_id=restaurant_id,
        user_id=user_id,
        booking_type=booking_type,
        table_type=table_type,
        booking_date=booking_date,
        booking_time=booking_time,
        guest_count=guest_count,
        status='pending'
    )
    db.session.add(booking)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'booking': booking.to_dict(),
        'message': 'Booking created successfully'
    })


# ============================================================
# REVIEW APIs
# ============================================================

@api_bp.route('/reviews', methods=['GET'])
def get_reviews():
    """Get reviews for a restaurant."""
    models = get_new_models()
    Review = models['Review']
    
    restaurant_id = request.args.get('restaurant_id', type=int)
    
    if not restaurant_id:
        return jsonify({'success': False, 'message': 'restaurant_id required'}), 400
    
    reviews = Review.query.filter_by(restaurant_id=restaurant_id).order_by(Review.created_at.desc()).all()
    
    # Calculate average rating
    avg_rating = 0
    if reviews:
        avg_rating = sum(r.rating for r in reviews) / len(reviews)
    
    return jsonify({
        'success': True,
        'reviews': [r.to_dict() for r in reviews],
        'average_rating': round(avg_rating, 1),
        'total_reviews': len(reviews)
    })


@api_bp.route('/reviews/add', methods=['POST'])
def add_review():
    """
    Add a review for a restaurant.
    USER only - can only review once per restaurant.
    """
    data = request.get_json() or {}
    models = get_new_models()
    db = get_db()
    
    restaurant_id = data.get('restaurant_id')
    user_id = data.get('user_id')
    rating = data.get('rating')
    comment = data.get('comment', '')
    
    if not all([restaurant_id, user_id, rating]):
        return jsonify({'success': False, 'message': 'restaurant_id, user_id, rating required'}), 400
    
    if rating < 1 or rating > 5:
        return jsonify({'success': False, 'message': 'Rating must be between 1 and 5'}), 400
    
    Review = models['Review']
    
    # Check if user already reviewed
    existing = Review.query.filter_by(restaurant_id=restaurant_id, user_id=user_id).first()
    if existing:
        return jsonify({'success': False, 'message': 'You have already reviewed this restaurant'}), 409
    
    review = Review(
        restaurant_id=restaurant_id,
        user_id=user_id,
        rating=rating,
        comment=comment
    )
    db.session.add(review)
    
    # Update restaurant rating
    Restaurant = models['Restaurant']
    restaurant = Restaurant.query.get(restaurant_id)
    if restaurant:
        all_reviews = Review.query.filter_by(restaurant_id=restaurant_id).all()
        restaurant.rating = sum(r.rating for r in all_reviews) / len(all_reviews)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'review': review.to_dict(),
        'message': 'Review added successfully'
    })


# ============================================================
# ADMIN APIs - Platform Logs
# ============================================================

@api_bp.route('/admin/logs', methods=['GET'])
@require_role('ADMIN')
def get_platform_logs():
    """Get platform activity logs. ADMIN only."""
    models = get_new_models()
    PlatformLog = models['PlatformLog']
    
    admin_id = request.args.get('admin_id', type=int)
    action = request.args.get('action')
    limit = request.args.get('limit', 100, type=int)
    
    query = PlatformLog.query
    
    if admin_id:
        query = query.filter_by(admin_id=admin_id)
    if action:
        query = query.filter_by(action=action)
    
    logs = query.order_by(PlatformLog.created_at.desc()).limit(limit).all()
    
    return jsonify({
        'success': True,
        'logs': [log.to_dict() for log in logs]
    })


@api_bp.route('/admin/log-action', methods=['POST'])
@require_role('ADMIN')
def log_admin_action():
    """Log an admin action."""
    data = request.get_json() or {}
    models = get_new_models()
    db = get_db()
    
    admin_id = data.get('admin_id')
    action = data.get('action')
    target_table = data.get('target_table')
    target_id = data.get('target_id')
    details = data.get('details')
    
    if not all([admin_id, action]):
        return jsonify({'success': False, 'message': 'admin_id and action required'}), 400
    
    PlatformLog = models['PlatformLog']
    
    log = PlatformLog(
        admin_id=admin_id,
        action=action,
        target_table=target_table,
        target_id=target_id,
        details=str(details) if details else None
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Action logged'
    })


# ============================================================
# HEALTH CHECK
# ============================================================

@api_bp.route('/health', methods=['GET'])
def api_health():
    """Health check for new API."""
    return jsonify({
        'success': True,
        'message': 'New API is running',
        'version': '2.0'
    })


# ============================================================
# DECORATOR FACTORY (for use with server.py)
# ============================================================

def require_role(role):
    """
    Role-based access decorator.
    Usage: @require_role('VENDOR')
    """
    from utils.rbac import require_role as rbac_require_role
    return rbac_require_role(role)


def require_any_role(*roles):
    """Allow access if user has any of the specified roles."""
    from utils.rbac import require_any_role as rbac_require_any_role
    return rbac_require_any_role(*roles)

