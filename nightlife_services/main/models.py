"""
Nightlife Main Service Models
============================
Database models for: Club, NightlifeItem, Rating, NightlifeCoupon, NightlifeEvent
"""

from . import db
from datetime import datetime

class Club(db.Model):
    """Club/Venue model"""
    __tablename__ = 'clubs'
    
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, nullable=False)  # Reference to vendor service
    club_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(300))
    city = db.Column(db.String(100))
    image = db.Column(db.String(500))
    music = db.Column(db.String(200))
    status = db.Column(db.String(20), default='open')  # open, busy, closed
    rating_avg = db.Column(db.Float, default=0.0)
    rating_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    items = db.relationship('NightlifeItem', backref='club', lazy=True, cascade='all, delete-orphan')
    ratings = db.relationship('Rating', backref='club', lazy=True, cascade='all, delete-orphan')
    coupons = db.relationship('NightlifeCoupon', backref='club', lazy=True, cascade='all, delete-orphan')
    events = db.relationship('NightlifeEvent', backref='club', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'vendor_id': self.vendor_id,
            'club_name': self.club_name,
            'description': self.description,
            'location': self.location,
            'city': self.city,
            'image': self.image,
            'music': self.music,
            'status': self.status,
            'rating_avg': self.rating_avg,
            'rating_count': self.rating_count,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class NightlifeItem(db.Model):
    """Menu items for clubs (drinks, food, etc.)"""
    __tablename__ = 'nightlife_items'
    
    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, db.ForeignKey('clubs.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(100))  # drinks, food, shisha, snacks
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(500))
    is_available = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'club_id': self.club_id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'price': self.price,
            'image_url': self.image_url,
            'is_available': self.is_available
        }


class Rating(db.Model):
    """Club ratings and reviews"""
    __tablename__ = 'ratings'
    
    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, db.ForeignKey('clubs.id'), nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    user_name = db.Column(db.String(100))
    stars = db.Column(db.Integer, nullable=False)  # 1-5
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'club_id': self.club_id,
            'user_id': self.user_id,
            'user_name': self.user_name,
            'stars': self.stars,
            'comment': self.comment,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class NightlifeCoupon(db.Model):
    """Coupons for clubs"""
    __tablename__ = 'nightlife_coupons'
    
    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, db.ForeignKey('clubs.id'), nullable=False)
    code = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(200))
    discount_type = db.Column(db.String(20))  # percent, fixed
    discount_value = db.Column(db.Float, nullable=False)
    min_order = db.Column(db.Float, default=0)
    max_discount = db.Column(db.Float)
    valid_from = db.Column(db.DateTime)
    valid_until = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'club_id': self.club_id,
            'code': self.code,
            'description': self.description,
            'discount_type': self.discount_type,
            'discount_value': self.discount_value,
            'min_order': self.min_order,
            'max_discount': self.max_discount,
            'is_active': self.is_active
        }


class NightlifeEvent(db.Model):
    """Events at clubs"""
    __tablename__ = 'nightlife_events'
    
    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, db.ForeignKey('clubs.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    event_date = db.Column(db.DateTime, nullable=False)
    image_url = db.Column(db.String(500))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'club_id': self.club_id,
            'name': self.name,
            'description': self.description,
            'event_date': self.event_date.isoformat() if self.event_date else None,
            'image_url': self.image_url,
            'is_active': self.is_active
        }
