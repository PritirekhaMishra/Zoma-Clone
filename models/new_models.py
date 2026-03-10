"""
New Database Models for ZomaClone
================================
Refactored database schema with unified accounts, role-based access control,
and proper relationships for scalability and privacy.

Tables:
- accounts (unified authentication)
- users, vendors, delivery_partners, admins (role profiles)
- restaurants, menus (business entities)
- food_orders, nightlife_orders (order systems)
- table_bookings (reservations)
- delivery_orders (delivery tracking)
- reviews (ratings)
- platform_logs (admin audit)
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import enum

db = SQLAlchemy()

class UserRole(enum.Enum):
    """User roles for the platform"""
    USER = "USER"
    VENDOR = "VENDOR"
    DELIVERY = "DELIVERY"
    ADMIN = "ADMIN"


class AccountStatus(enum.Enum):
    """Account status"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


# ============================================================
# UNIFIED ACCOUNT SYSTEM
# ============================================================

class Account(db.Model):
    """
    Unified Account System
    =====================
    All users (customers, vendors, delivery partners, admins) share this table.
    Each account has exactly one role.
    """
    __tablename__ = "accounts"
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.USER)
    status = db.Column(db.String(20), default="active")  # active, suspended, deleted
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships - One-to-One with role-specific profiles
    user_profile = db.relationship('UserProfile', backref='account', uselist=False, lazy=True)
    vendor_profile = db.relationship('VendorProfile', backref='account', uselist=False, lazy=True)
    delivery_profile = db.relationship('DeliveryPartner', backref='account', uselist=False, lazy=True)
    admin_profile = db.relationship('Admin', backref='account', uselist=False, lazy=True)
    
    def to_dict(self, include_sensitive=False):
        """Convert to dictionary"""
        data = {
            'id': self.id,
            'email': self.email,
            'role': self.role.value if isinstance(self.role, UserRole) else self.role,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        if include_sensitive:
            data['password_hash'] = self.password_hash
        return data


# ============================================================
# USER PROFILES
# ============================================================

class UserProfile(db.Model):
    """
    User Profile
    ===========
    Extended profile for customers who place orders and bookings.
    """
    __tablename__ = "users"
    
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), nullable=False, index=True)
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    food_orders = db.relationship('FoodOrder', backref='user', lazy=True)
    nightlife_orders = db.relationship('NightlifeOrder', backref='user', lazy=True)
    table_bookings = db.relationship('TableBooking', backref='user', lazy=True)
    reviews = db.relationship('Review', backref='user', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'account_id': self.account_id,
            'name': self.name,
            'phone': self.phone,
            'address': self.address,
            'city': self.city,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# ============================================================
# VENDOR PROFILES
# ============================================================

class VendorProfile(db.Model):
    """
    Vendor Profile
    =============
    Business profile for restaurants/nightlife venues.
    """
    __tablename__ = "vendors"
    
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), unique=True, nullable=False)
    business_name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20))
    city = db.Column(db.String(100))
    verification_status = db.Column(db.String(20), default="pending")  # pending, verified, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    restaurants = db.relationship('Restaurant', backref='vendor', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'account_id': self.account_id,
            'business_name': self.business_name,
            'phone': self.phone,
            'city': self.city,
            'verification_status': self.verification_status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# ============================================================
# DELIVERY PARTNERS
# ============================================================

class DeliveryPartner(db.Model):
    """
    Delivery Partner
    ================
    Profile for delivery executives.
    """
    __tablename__ = "delivery_partners"
    
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    vehicle_type = db.Column(db.String(50))  # bike, car, scooter
    availability_status = db.Column(db.String(20), default="available")  # available, busy, offline
    current_location = db.Column(db.String(100))  # lat,lng format
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    deliveries = db.relationship('DeliveryOrder', backref='delivery_partner', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'account_id': self.account_id,
            'name': self.name,
            'phone': self.phone,
            'vehicle_type': self.vehicle_type,
            'availability_status': self.availability_status,
            'current_location': self.current_location,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# ============================================================
# ADMIN
# ============================================================

class Admin(db.Model):
    """
    Admin Profile
    =============
    Platform administrators with role levels.
    """
    __tablename__ = "admins"
    
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), unique=True, nullable=False)
    role_level = db.Column(db.Integer, default=1)  # 1=super_admin, 2=manager, 3=support
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    logs = db.relationship('PlatformLog', backref='admin', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'account_id': self.account_id,
            'role_level': self.role_level,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# ============================================================
# RESTAURANTS
# ============================================================

class Restaurant(db.Model):
    """
    Restaurant/Venue
    ================
    Can be of type 'food' or 'nightlife'.
    """
    __tablename__ = "restaurants"
    
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.id'), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(20), default="food")  # food, nightlife
    city = db.Column(db.String(100))
    address = db.Column(db.String(300))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    banner_image = db.Column(db.String(300))
    rating = db.Column(db.Float, default=0.0)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    menus = db.relationship('MenuItem', backref='restaurant', lazy=True, cascade='all, delete-orphan')
    food_orders = db.relationship('FoodOrder', backref='restaurant', lazy=True)
    nightlife_orders = db.relationship('NightlifeOrder', backref='restaurant', lazy=True)
    table_bookings = db.relationship('TableBooking', backref='restaurant', lazy=True)
    reviews = db.relationship('Review', backref='restaurant', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'vendor_id': self.vendor_id,
            'name': self.name,
            'category': self.category,
            'city': self.city,
            'address': self.address,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'banner_image': self.banner_image,
            'rating': self.rating,
            'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# ============================================================
# MENU ITEMS
# ============================================================

class MenuItem(db.Model):
    """
    Menu Item
    =========
    Menu items for restaurants.
    """
    __tablename__ = "menus"
    
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(1000))
    price = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(100))  # appetizer, main, drinks, etc.
    image = db.Column(db.String(300))
    available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    food_order_items = db.relationship('FoodOrderItem', backref='menu_item', lazy=True)
    nightlife_order_items = db.relationship('NightlifeOrderItem', backref='menu_item', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'restaurant_id': self.restaurant_id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'category': self.category,
            'image': self.image,
            'available': self.available,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# ============================================================
# FOOD ORDERS
# ============================================================

class FoodOrder(db.Model):
    """
    Food Order
    =========
    Order for food delivery.
    """
    __tablename__ = "food_orders"
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    total_price = db.Column(db.Integer, nullable=False)
    order_status = db.Column(db.String(30), default="PENDING")  # PENDING, ACCEPTED, PREPARING, READY, OUT_FOR_DELIVERY, DELIVERED, CANCELLED
    payment_status = db.Column(db.String(20), default="PENDING")  # PENDING, PAID, FAILED
    payment_method = db.Column(db.String(20), default="COD")  # COD, UPI
    delivery_address = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    items = db.relationship('FoodOrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    delivery = db.relationship('DeliveryOrder', backref='food_order', uselist=False, lazy=True)
    
    def to_dict(self, include_items=False):
        data = {
            'id': self.id,
            'order_id': self.order_id,
            'restaurant_id': self.restaurant_id,
            'user_id': self.user_id,
            'total_price': self.total_price,
            'order_status': self.order_status,
            'payment_status': self.payment_status,
            'payment_method': self.payment_method,
            'delivery_address': self.delivery_address,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        if include_items:
            data['items'] = [item.to_dict() for item in self.items]
        return data


class FoodOrderItem(db.Model):
    """
    Food Order Item
    ==============
    Individual items in a food order.
    """
    __tablename__ = "food_order_items"
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('food_orders.id'), nullable=False, index=True)
    menu_id = db.Column(db.Integer, db.ForeignKey('menus.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    price = db.Column(db.Integer, nullable=False)  # price at time of order
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'menu_id': self.menu_id,
            'quantity': self.quantity,
            'price': self.price
        }


# ============================================================
# NIGHTLIFE ORDERS
# ============================================================

class NightlifeOrder(db.Model):
    """
    Nightlife Order
    ==============
    Order for nightlife venues (drinks, food, etc.).
    """
    __tablename__ = "nightlife_orders"
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    total_price = db.Column(db.Integer, nullable=False)
    order_status = db.Column(db.String(30), default="PENDING")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    items = db.relationship('NightlifeOrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self, include_items=False):
        data = {
            'id': self.id,
            'order_id': self.order_id,
            'restaurant_id': self.restaurant_id,
            'user_id': self.user_id,
            'total_price': self.total_price,
            'order_status': self.order_status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        if include_items:
            data['items'] = [item.to_dict() for item in self.items]
        return data


class NightlifeOrderItem(db.Model):
    """
    Nightlife Order Item
    ===================
    Individual items in a nightlife order.
    """
    __tablename__ = "nightlife_order_items"
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('nightlife_orders.id'), nullable=False, index=True)
    menu_id = db.Column(db.Integer, db.ForeignKey('menus.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    price = db.Column(db.Integer, nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'menu_id': self.menu_id,
            'quantity': self.quantity,
            'price': self.price
        }


# ============================================================
# TABLE BOOKINGS
# ============================================================

class TableBooking(db.Model):
    """
    Table Booking
    =============
    Reservations for restaurants and nightlife venues.
    """
    __tablename__ = "table_bookings"
    
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    booking_type = db.Column(db.String(20), default="food")  # food, nightlife
    table_type = db.Column(db.String(50))
    booking_time = db.Column(db.String(10))  # HH:MM format
    booking_date = db.Column(db.String(10))  # YYYY-MM-DD format
    guest_count = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default="pending")  # pending, confirmed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'booking_id': self.booking_id,
            'restaurant_id': self.restaurant_id,
            'user_id': self.user_id,
            'booking_type': self.booking_type,
            'table_type': self.table_type,
            'booking_time': self.booking_time,
            'booking_date': self.booking_date,
            'guest_count': self.guest_count,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# ============================================================
# DELIVERY ORDERS
# ============================================================

class DeliveryOrder(db.Model):
    """
    Delivery Order
    ==============
    Links food orders to delivery partners.
    """
    __tablename__ = "delivery_orders"
    
    id = db.Column(db.Integer, primary_key=True)
    food_order_id = db.Column(db.Integer, db.ForeignKey('food_orders.id'), nullable=False, unique=True)
    delivery_partner_id = db.Column(db.Integer, db.ForeignKey('delivery_partners.id'), nullable=True)
    pickup_time = db.Column(db.DateTime)
    delivery_time = db.Column(db.DateTime)
    delivery_status = db.Column(db.String(30), default="ASSIGNED")  # ASSIGNED, PICKED_UP, IN_TRANSIT, DELIVERED
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'food_order_id': self.food_order_id,
            'delivery_partner_id': self.delivery_partner_id,
            'pickup_time': self.pickup_time.isoformat() if self.pickup_time else None,
            'delivery_time': self.delivery_time.isoformat() if self.delivery_time else None,
            'delivery_status': self.delivery_status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# ============================================================
# REVIEWS
# ============================================================

class Review(db.Model):
    """
    Review
    =====
    Ratings and reviews for restaurants.
    """
    __tablename__ = "reviews"
    
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'restaurant_id': self.restaurant_id,
            'user_id': self.user_id,
            'rating': self.rating,
            'comment': self.comment,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# ============================================================
# PLATFORM LOGS
# ============================================================

class PlatformLog(db.Model):
    """
    Platform Log
    ============
    Audit trail for admin actions.
    """
    __tablename__ = "platform_logs"
    
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admins.id'), nullable=False, index=True)
    action = db.Column(db.String(100), nullable=False)
    target_table = db.Column(db.String(50))
    target_id = db.Column(db.Integer)
    details = db.Column(db.Text)  # JSON with details
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'admin_id': self.admin_id,
            'action': self.action,
            'target_table': self.target_table,
            'target_id': self.target_id,
            'details': self.details,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def create_account(email, password_hash, role):
    """Create a new account with role"""
    account = Account(
        email=email,
        password_hash=password_hash,
        role=role if isinstance(role, UserRole) else UserRole[role]
    )
    db.session.add(account)
    db.session.commit()
    return account


def get_account_by_email(email):
    """Get account by email"""
    return Account.query.filter_by(email=email.lower()).first()


def get_user_by_phone(phone):
    """Get user profile by phone"""
    return UserProfile.query.filter_by(phone=phone).first()


def generate_order_id(prefix="ORD"):
    """Generate unique order ID"""
    import random
    import string
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    random_suffix = ''.join(random.choices(string.digits, k=4))
    return f"{prefix}-{timestamp}-{random_suffix}"


def generate_booking_id(prefix="BK"):
    """Generate unique booking ID"""
    import random
    import string
    timestamp = datetime.utcnow().strftime("%Y%m%d")
    random_suffix = ''.join(random.choices(string.digits, k=4))
    return f"{prefix}-{timestamp}-{random_suffix}"

