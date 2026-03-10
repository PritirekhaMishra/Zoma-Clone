"""
Role-Based Access Control (RBAC) Utilities
==========================================
Implements privacy enforcement between different user roles.

Privacy Rules:
- USER: Can view restaurants, view/create their own orders, create bookings
- VENDOR: Can view/manage only their restaurants, manage menus, view orders for their restaurants
- DELIVERY: Can view only assigned deliveries, update delivery status
- ADMIN: Full access to all tables, manage users/vendors/restaurants
"""

from functools import wraps
from flask import request, jsonify, g
import hashlib

# Role constants for bitwise operations (if needed)
ROLES = {
    'USER': 1,
    'VENDOR': 2,
    'DELIVERY': 4,
    'ADMIN': 8
}

# Role hierarchy - higher number = more privileges
ROLE_HIERARCHY = {
    'USER': 1,
    'VENDOR': 2,
    'DELIVERY': 3,
    'ADMIN': 4
}


def hash_password(password):
    """Hash a password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password, password_hash):
    """Verify password against hash"""
    return hash_password(password) == password_hash


def require_role(required_role):
    """
    Decorator to enforce role-based access control.
    
    Usage:
        @require_role('VENDOR')
        def my_view():
            # Only vendors can access
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if user is authenticated and has correct role
            current_user = getattr(g, 'current_user', None)
            current_account = getattr(g, 'current_account', None)
            
            if not current_account:
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            
            user_role = current_account.role
            if isinstance(user_role, str):
                user_role = user_role.upper()
            else:
                user_role = user_role.value if hasattr(user_role, 'value') else str(user_role)
            
            if user_role != required_role.upper():
                return jsonify({
                    'success': False, 
                    'error': f'Access denied. Required role: {required_role}'
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_any_role(*roles):
    """
    Decorator to allow access if user has any of the specified roles.
    
    Usage:
        @require_any_role('ADMIN', 'VENDOR')
        def my_view():
            # Admins or vendors can access
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            current_account = getattr(g, 'current_account', None)
            
            if not current_account:
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            
            user_role = current_account.role
            if isinstance(user_role, str):
                user_role = user_role.upper()
            else:
                user_role = user_role.value if hasattr(user_role, 'value') else str(user_role)
            
            allowed_roles = [r.upper() for r in roles]
            if user_role not in allowed_roles:
                return jsonify({
                    'success': False, 
                    'error': f'Access denied. Required roles: {", ".join(allowed_roles)}'
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_min_role(min_role):
    """
    Decorator to enforce minimum role level.
    
    Usage:
        @require_min_role('VENDOR')
        def my_view():
            # Vendors and admins can access
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            current_account = getattr(g, 'current_account', None)
            
            if not current_account:
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            
            user_role = current_account.role
            if isinstance(user_role, str):
                user_role = user_role.upper()
            else:
                user_role = user_role.value if hasattr(user_role, 'value') else str(user_role)
            
            user_level = ROLE_HIERARCHY.get(user_role, 0)
            required_level = ROLE_HIERARCHY.get(min_role.upper(), 99)
            
            if user_level < required_level:
                return jsonify({
                    'success': False, 
                    'error': f'Access denied. Minimum role required: {min_role}'
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ============================================================
# QUERY FILTERS - Enforce data privacy in database queries
# ============================================================

class QueryFilter:
    """
    Helper class to filter queries based on user role and identity.
    """
    
    @staticmethod
    def vendor_filter(query, model, account):
        """
        Filter query to return only vendor's own data.
        
        Usage:
            restaurants = QueryFilter.vendor_filter(
                Restaurant.query, 
                Restaurant, 
                current_account
            ).all()
        """
        if not account or not account.vendor_profile:
            return query.filter_by(id=0)  # Return empty
        
        vendor_id = account.vendor_profile.id
        return query.filter_by(vendor_id=vendor_id)
    
    @staticmethod
    def user_filter(query, model, account):
        """
        Filter query to return only user's own data.
        """
        if not account or not account.user_profile:
            return query.filter_by(id=0)  # Return empty
        
        user_id = account.user_profile.id
        return query.filter_by(user_id=user_id)
    
    @staticmethod
    def delivery_filter(query, model, account):
        """
        Filter query to return only delivery partner's assigned deliveries.
        """
        if not account or not account.delivery_profile:
            return query.filter_by(id=0)  # Return empty
        
        delivery_id = account.delivery_profile.id
        return query.filter_by(delivery_partner_id=delivery_id)


def filter_by_role(query, model, account):
    """
    Automatically filter query based on account role.
    
    Usage:
        # In a view function
        orders = filter_by_role(FoodOrder.query, FoodOrder, current_account).all()
    """
    if not account:
        return query.filter_by(id=0)  # Return empty
    
    user_role = account.role
    if isinstance(user_role, str):
        user_role = user_role.upper()
    else:
        user_role = user_role.value if hasattr(user_role, 'value') else str(user_role)
    
    # Import models here to avoid circular imports
    from models.new_models import (
        Restaurant, MenuItem, FoodOrder, NightlifeOrder, 
        TableBooking, DeliveryOrder, Review
    )
    
    # Apply role-specific filters
    if user_role == 'VENDOR':
        if model in [Restaurant, MenuItem]:
            return QueryFilter.vendor_filter(query, model, account)
        elif model in [FoodOrder, NightlifeOrder]:
            # Vendors see orders for their restaurants
            vendor_id = account.vendor_profile.id if account.vendor_profile else 0
            restaurant_ids = [r.id for r in account.vendor_profile.restaurants] if account.vendor_profile else []
            return query.filter(Restaurant.vendor_id == vendor_id)
    
    elif user_role == 'USER':
        if model in [FoodOrder, NightlifeOrder, TableBooking, Review]:
            return QueryFilter.user_filter(query, model, account)
    
    elif user_role == 'DELIVERY':
        if model == DeliveryOrder:
            return QueryFilter.delivery_filter(query, model, account)
    
    # Admin gets all data - no filter
    return query


# ============================================================
# AUTHORIZATION HELPERS
# ============================================================

def can_access_resource(account, resource_type, resource_owner_id=None):
    """
    Check if account can access a specific resource.
    
    Args:
        account: The Account object
        resource_type: Type of resource (restaurant, order, etc.)
        resource_owner_id: ID of the resource owner (for ownership checks)
    
    Returns:
        bool: True if access is allowed
    """
    if not account:
        return False
    
    user_role = account.role
    if isinstance(user_role, str):
        user_role = user_role.upper()
    else:
        user_role = user_role.value if hasattr(user_role, 'value') else str(user_role)
    
    # Admin has full access
    if user_role == 'ADMIN':
        return True
    
    # Check based on resource type
    if resource_type in ['restaurant', 'menu']:
        if user_role == 'VENDOR' and account.vendor_profile:
            # Vendor can only access their own restaurants
            return resource_owner_id == account.vendor_profile.id
        return False
    
    elif resource_type in ['order', 'booking', 'review']:
        if user_role == 'USER' and account.user_profile:
            # User can only access their own orders/bookings/reviews
            return resource_owner_id == account.user_profile.id
        elif user_role == 'VENDOR':
            # Vendor can access orders for their restaurants
            return True  # Additional check needed in actual implementation
        return False
    
    elif resource_type == 'delivery':
        if user_role == 'DELIVERY' and account.delivery_profile:
            # Delivery partner can only access assigned deliveries
            return True  # Additional check needed
        return False
    
    return False


def get_accessible_restaurants(account):
    """
    Get restaurants accessible to the account based on role.
    """
    from models.new_models import Restaurant
    
    if not account:
        return []
    
    user_role = account.role
    if isinstance(user_role, str):
        user_role = user_role.upper()
    else:
        user_role = user_role.value if hasattr(user_role, 'value') else str(user_role)
    
    if user_role == 'ADMIN':
        return Restaurant.query.all()
    elif user_role == 'VENDOR' and account.vendor_profile:
        return Restaurant.query.filter_by(vendor_id=account.vendor_profile.id).all()
    else:
        # Users and delivery can see all active restaurants
        return Restaurant.query.filter_by(active=True).all()


# ============================================================
# EXAMPLE USAGE
# ============================================================

"""
Example 1: Vendor-only endpoint
==============================
@app.route('/api/vendor/restaurants')
@require_role('VENDOR')
def get_vendor_restaurants():
    from models.new_models import Restaurant
    from flask import g
    
    account = g.current_account
    restaurants = QueryFilter.vendor_filter(
        Restaurant.query, 
        Restaurant, 
        account
    ).all()
    
    return jsonify({
        'success': True,
        'restaurants': [r.to_dict() for r in restaurants]
    })


Example 2: User's own orders
=============================
@app.route('/api/orders')
@require_role('USER')
def get_user_orders():
    from models.new_models import FoodOrder
    from flask import g
    
    account = g.current_account
    orders = QueryFilter.user_filter(
        FoodOrder.query, 
        FoodOrder, 
        account
    ).all()
    
    return jsonify({
        'success': True,
        'orders': [o.to_dict() for o in orders]
    })


Example 3: Delivery partner's assigned orders
============================================
@app.route('/api/delivery/orders')
@require_role('DELIVERY')
def get_delivery_orders():
    from models.new_models import DeliveryOrder
    from flask import g
    
    account = g.current_account
    deliveries = QueryFilter.delivery_filter(
        DeliveryOrder.query, 
        DeliveryOrder, 
        account
    ).all()
    
    return jsonify({
        'success': True,
        'deliveries': [d.to_dict() for d in deliveries]
    })
"""

