"""
Nightlife Order Service Models
============================
Database models for: Order, OrderItem, OrderStatus, OrderDelivery
"""

from . import db
from datetime import datetime

class Order(db.Model):
    """Food/Drink order model"""
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    order_ref = db.Column(db.String(20), unique=True, nullable=False)  # e.g., NLO-2025-001
    vendor_id = db.Column(db.Integer, nullable=False)
    club_id = db.Column(db.Integer)  # Link to club if ordering from table
    club_name = db.Column(db.String(200))
    booking_id = db.Column(db.Integer)  # Link to table booking if applicable
    
    # User info
    user_id = db.Column(db.Integer, nullable=False)
    user_name = db.Column(db.String(100))
    user_phone = db.Column(db.String(20))
    user_email = db.Column(db.String(200))
    
    # Order type
    order_type = db.Column(db.String(20), default='dine_in')  # dine_in, delivery, pickup
    
    # Table info (for dine-in)
    table_number = db.Column(db.String(20))
    
    # Pricing
    subtotal = db.Column(db.Float, default=0)
    tax_amount = db.Column(db.Float, default=0)
    delivery_fee = db.Column(db.Float, default=0)
    discount_amount = db.Column(db.Float, default=0)
    total_amount = db.Column(db.Float, default=0)
    
    # Status: pending, confirmed, preparing, ready, out_for_delivery, delivered, cancelled
    status = db.Column(db.String(20), default='pending')
    
    # Payment status: pending, paid, failed, refunded
    payment_status = db.Column(db.String(20), default='pending')
    payment_method = db.Column(db.String(50))  # upi, card, cash
    payment_ref = db.Column(db.String(100))
    payment_time = db.Column(db.DateTime)
    
    # Delivery address (for delivery orders)
    delivery_address = db.Column(db.Text)
    delivery_lat = db.Column(db.Float)
    delivery_lon = db.Column(db.Float)
    
    # Special instructions
    instructions = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime)
    preparing_at = db.Column(db.DateTime)
    ready_at = db.Column(db.DateTime)
    delivered_at = db.Column(db.DateTime)
    cancelled_at = db.Column(db.DateTime)
    
    # Relationships
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    status_history = db.relationship('OrderStatus', backref='order', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_ref': self.order_ref,
            'vendor_id': self.vendor_id,
            'club_id': self.club_id,
            'club_name': self.club_name,
            'booking_id': self.booking_id,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'user_phone': self.user_phone,
            'user_email': self.user_email,
            'order_type': self.order_type,
            'table_number': self.table_number,
            'subtotal': self.subtotal,
            'tax_amount': self.tax_amount,
            'delivery_fee': self.delivery_fee,
            'discount_amount': self.discount_amount,
            'total_amount': self.total_amount,
            'status': self.status,
            'payment_status': self.payment_status,
            'payment_method': self.payment_method,
            'delivery_address': self.delivery_address,
            'instructions': self.instructions,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class OrderItem(db.Model):
    """Individual items in an order"""
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    item_id = db.Column(db.Integer)  # Reference to NightlifeItem
    item_name = db.Column(db.String(200), nullable=False)
    item_category = db.Column(db.String(100))
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Float, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    special_instructions = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'item_id': self.item_id,
            'item_name': self.item_name,
            'item_category': self.item_category,
            'quantity': self.quantity,
            'unit_price': self.unit_price,
            'total_price': self.total_price,
            'special_instructions': self.special_instructions
        }


class OrderStatus(db.Model):
    """Status history for orders"""
    __tablename__ = 'order_status_history'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'status': self.status,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class OrderDelivery(db.Model):
    """Delivery tracking for orders"""
    __tablename__ = 'order_delivery'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False, unique=True)
    delivery_partner_name = db.Column(db.String(100))
    delivery_partner_phone = db.Column(db.String(20))
    current_lat = db.Column(db.Float)
    current_lon = db.Column(db.Float)
    estimated_delivery_time = db.Column(db.DateTime)
    actual_delivery_time = db.Column(db.DateTime)
    delivery_status = db.Column(db.String(20), default='assigned')  # assigned, picked_up, in_transit, delivered
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'delivery_partner_name': self.delivery_partner_name,
            'delivery_partner_phone': self.delivery_partner_phone,
            'estimated_delivery_time': self.estimated_delivery_time.isoformat() if self.estimated_delivery_time else None,
            'delivery_status': self.delivery_status
        }
