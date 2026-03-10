"""
Nightlife Vendor Service Models
=============================
Database models for: Vendor, TableType, Table, TimeSlot, VendorSettings
"""

from . import db
from datetime import datetime

class Vendor(db.Model):
    """Nightlife vendor/club owner model"""
    __tablename__ = 'vendors'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    club_name = db.Column(db.String(200), nullable=False)
    owner_name = db.Column(db.String(200))
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    upi_id = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    table_types = db.relationship('TableType', backref='vendor', lazy=True, cascade='all, delete-orphan')
    tables = db.relationship('Table', backref='vendor', lazy=True, cascade='all, delete-orphan')
    time_slots = db.relationship('TimeSlot', backref='vendor', lazy=True, cascade='all, delete-orphan')
    settings = db.relationship('VendorSettings', backref='vendor', uselist=False, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'phone': self.phone,
            'club_name': self.club_name,
            'owner_name': self.owner_name,
            'address': self.address,
            'city': self.city,
            'upi_id': self.upi_id,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class TableType(db.Model):
    """Table types (VIP, Regular, etc.)"""
    __tablename__ = 'table_types'
    
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # VIP, Premium, Regular
    description = db.Column(db.Text)
    min_capacity = db.Column(db.Integer, default=2)
    max_capacity = db.Column(db.Integer, default=6)
    base_price = db.Column(db.Float, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    tables = db.relationship('Table', backref='table_type', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'vendor_id': self.vendor_id,
            'name': self.name,
            'description': self.description,
            'min_capacity': self.min_capacity,
            'max_capacity': self.max_capacity,
            'base_price': self.base_price,
            'is_active': self.is_active
        }


class Table(db.Model):
    """Individual tables at a club"""
    __tablename__ = 'tables'
    
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.id'), nullable=False)
    type_id = db.Column(db.Integer, db.ForeignKey('table_types.id'), nullable=False)
    table_number = db.Column(db.String(20), nullable=False)
    capacity = db.Column(db.Integer)
    status = db.Column(db.String(20), default='free')  # free, reserved, occupied, maintenance
    position_x = db.Column(db.Integer)  # For visual layout
    position_y = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('vendor_id', 'table_number', name='unique_table_number'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'vendor_id': self.vendor_id,
            'type_id': self.type_id,
            'table_number': self.table_number,
            'capacity': self.capacity,
            'status': self.status,
            'position_x': self.position_x,
            'position_y': self.position_y
        }


class TimeSlot(db.Model):
    """Available time slots for booking"""
    __tablename__ = 'time_slots'
    
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.id'), nullable=False)
    day_of_week = db.Column(db.Integer)  # 0=Monday, 6=Sunday
    start_time = db.Column(db.String(10), nullable=False)  # HH:MM format
    end_time = db.Column(db.String(10), nullable=False)    # HH:MM format
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        return {
            'id': self.id,
            'vendor_id': self.vendor_id,
            'day_of_week': self.day_of_week,
            'day_name': days[self.day_of_week] if self.day_of_week is not None else 'All Days',
            'start_time': self.start_time,
            'end_time': self.end_time,
            'is_active': self.is_active
        }


class VendorSettings(db.Model):
    """Vendor-specific settings"""
    __tablename__ = 'vendor_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.id'), nullable=False, unique=True)
    advance_booking_hours = db.Column(db.Integer, default=24)
    min_booking_duration = db.Column(db.Integer, default=2)  # hours
    max_booking_duration = db.Column(db.Integer, default=6)
    cancellation_policy = db.Column(db.Text)
    terms_conditions = db.Column(db.Text)
    contact_phone = db.Column(db.String(20))
    contact_email = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'vendor_id': self.vendor_id,
            'advance_booking_hours': self.advance_booking_hours,
            'min_booking_duration': self.min_booking_duration,
            'max_booking_duration': self.max_booking_duration,
            'cancellation_policy': self.cancellation_policy,
            'terms_conditions': self.terms_conditions,
            'contact_phone': self.contact_phone,
            'contact_email': self.contact_email
        }
