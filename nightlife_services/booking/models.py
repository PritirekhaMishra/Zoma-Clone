"""
Nightlife Booking Service Models
===============================
Database models for: Booking, BookingPayment, BookingTimeline
"""

from . import db
from datetime import datetime

class Booking(db.Model):
    """Table booking model"""
    __tablename__ = 'bookings'
    
    id = db.Column(db.Integer, primary_key=True)
    booking_ref = db.Column(db.String(20), unique=True, nullable=False)  # e.g., NLB-2025-001
    vendor_id = db.Column(db.Integer, nullable=False)
    club_name = db.Column(db.String(200))
    
    # User info
    user_id = db.Column(db.Integer, nullable=False)
    user_name = db.Column(db.String(100))
    user_phone = db.Column(db.String(20))
    user_email = db.Column(db.String(200))
    
    # Booking details
    table_type_id = db.Column(db.Integer)
    table_type_name = db.Column(db.String(100))
    table_number = db.Column(db.String(20))
    booking_date = db.Column(db.Date, nullable=False)
    booking_time = db.Column(db.String(10), nullable=False)  # HH:MM format
    duration = db.Column(db.Integer, default=2)  # hours
    
    # Guest count
    guest_count = db.Column(db.Integer, default=2)
    
    # Pricing
    base_amount = db.Column(db.Float, default=0)
    addon_amount = db.Column(db.Float, default=0)
    discount_amount = db.Column(db.Float, default=0)
    total_amount = db.Column(db.Float, default=0)
    
    # Status: pending, confirmed, cancelled, completed, no_show
    status = db.Column(db.String(20), default='pending')
    
    # Payment status: pending, paid, failed, refunded
    payment_status = db.Column(db.String(20), default='pending')
    payment_method = db.Column(db.String(50))  # upi, card, cash
    payment_ref = db.Column(db.String(100))
    payment_time = db.Column(db.DateTime)
    
    # Special requests
    special_requests = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime)
    cancelled_at = db.Column(db.DateTime)
    
    # Relationships
    timeline = db.relationship('BookingTimeline', backref='booking', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'booking_ref': self.booking_ref,
            'vendor_id': self.vendor_id,
            'club_name': self.club_name,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'user_phone': self.user_phone,
            'user_email': self.user_email,
            'table_type_id': self.table_type_id,
            'table_type_name': self.table_type_name,
            'table_number': self.table_number,
            'booking_date': self.booking_date.isoformat() if self.booking_date else None,
            'booking_time': self.booking_time,
            'duration': self.duration,
            'guest_count': self.guest_count,
            'base_amount': self.base_amount,
            'addon_amount': self.addon_amount,
            'discount_amount': self.discount_amount,
            'total_amount': self.total_amount,
            'status': self.status,
            'payment_status': self.payment_status,
            'payment_method': self.payment_method,
            'payment_ref': self.payment_ref,
            'special_requests': self.special_requests,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class BookingPayment(db.Model):
    """Payment records for bookings"""
    __tablename__ = 'booking_payments'
    
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='INR')
    payment_method = db.Column(db.String(50))
    payment_status = db.Column(db.String(20))  # pending, success, failed
    transaction_id = db.Column(db.String(100))
    razorpay_order_id = db.Column(db.String(100))
    razorpay_payment_id = db.Column(db.String(100))
    upi_transaction_id = db.Column(db.String(100))
    response_data = db.Column(db.Text)  # JSON string
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'booking_id': self.booking_id,
            'amount': self.amount,
            'currency': self.currency,
            'payment_method': self.payment_method,
            'payment_status': self.payment_status,
            'transaction_id': self.transaction_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class BookingTimeline(db.Model):
    """Timeline/events for booking (status changes, etc.)"""
    __tablename__ = 'booking_timeline'
    
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)  # created, confirmed, cancelled, etc.
    event_data = db.Column(db.Text)  # JSON string
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'booking_id': self.booking_id,
            'event_type': self.event_type,
            'event_data': self.event_data,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
