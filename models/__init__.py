"""
Models Package
=============
New database models for ZomaClone refactored platform.

Usage:
    from models import db, Account, UserProfile, VendorProfile, Restaurant, etc.
    
    # Initialize with existing SQLAlchemy instance
    from server import db
    from models.new_models import Account, UserProfile, VendorProfile, DeliveryPartner, Admin
    from models.new_models import Restaurant, MenuItem, FoodOrder, NightlifeOrder
    from models.new_models import TableBooking, DeliveryOrder, Review, PlatformLog
"""

from .new_models import (
    db,
    UserRole,
    AccountStatus,
    Account,
    UserProfile,
    VendorProfile,
    DeliveryPartner,
    Admin,
    Restaurant,
    MenuItem,
    FoodOrder,
    FoodOrderItem,
    NightlifeOrder,
    NightlifeOrderItem,
    TableBooking,
    DeliveryOrder,
    Review,
    PlatformLog,
    create_account,
    get_account_by_email,
    get_user_by_phone,
    generate_order_id,
    generate_booking_id
)

__all__ = [
    'db',
    'UserRole',
    'AccountStatus',
    'Account',
    'UserProfile',
    'VendorProfile',
    'DeliveryPartner',
    'Admin',
    'Restaurant',
    'MenuItem',
    'FoodOrder',
    'FoodOrderItem',
    'NightlifeOrder',
    'NightlifeOrderItem',
    'TableBooking',
    'DeliveryOrder',
    'Review',
    'PlatformLog',
    'create_account',
    'get_account_by_email',
    'get_user_by_phone',
    'generate_order_id',
    'generate_booking_id'
]

