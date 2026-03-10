"""
Nightlife Vendor Service Routes
===========================
API endpoints for: Vendors, Tables, Slots, Settings
"""

from flask import Blueprint, request, jsonify
from . import db
from .models import Vendor, TableType, Table, TimeSlot, VendorSettings
from datetime import datetime
import json

vendor_bp = Blueprint('vendor', __name__)

# ==================== VENDORS ====================

@vendor_bp.route('/vendors', methods=['GET'])
def get_vendors():
    """Get all vendors"""
    try:
        vendors = Vendor.query.filter_by(is_active=True).all()
        return jsonify({
            'success': True,
            'data': [v.to_dict() for v in vendors]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@vendor_bp.route('/vendors/<int:vendor_id>', methods=['GET'])
def get_vendor(vendor_id):
    """Get single vendor details"""
    try:
        vendor = Vendor.query.get(vendor_id)
        if not vendor:
            return jsonify({
                'success': False,
                'message': 'Vendor not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': vendor.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@vendor_bp.route('/vendors', methods=['POST'])
def create_vendor():
    """Create a new vendor"""
    try:
        data = request.get_json()
        
        # Check if email already exists
        existing = Vendor.query.filter_by(email=data.get('email')).first()
        if existing:
            return jsonify({
                'success': False,
                'message': 'Email already registered'
            }), 400
        
        vendor = Vendor(
            email=data.get('email'),
            phone=data.get('phone'),
            club_name=data.get('club_name'),
            owner_name=data.get('owner_name'),
            address=data.get('address'),
            city=data.get('city'),
            upi_id=data.get('upi_id')
        )
        
        db.session.add(vendor)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': vendor.to_dict(),
            'message': 'Vendor created successfully'
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@vendor_bp.route('/vendors/<int:vendor_id>', methods=['PUT'])
def update_vendor(vendor_id):
    """Update vendor details"""
    try:
        vendor = Vendor.query.get(vendor_id)
        if not vendor:
            return jsonify({
                'success': False,
                'message': 'Vendor not found'
            }), 404
        
        data = request.get_json()
        
        if 'club_name' in data:
            vendor.club_name = data['club_name']
        if 'owner_name' in data:
            vendor.owner_name = data['owner_name']
        if 'phone' in data:
            vendor.phone = data['phone']
        if 'address' in data:
            vendor.address = data['address']
        if 'city' in data:
            vendor.city = data['city']
        if 'upi_id' in data:
            vendor.upi_id = data['upi_id']
        if 'is_active' in data:
            vendor.is_active = data['is_active']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': vendor.to_dict(),
            'message': 'Vendor updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ==================== TABLE TYPES ====================

@vendor_bp.route('/vendors/<int:vendor_id>/table-types', methods=['GET'])
def get_table_types(vendor_id):
    """Get all table types for a vendor"""
    try:
        types = TableType.query.filter_by(vendor_id=vendor_id, is_active=True).all()
        return jsonify({
            'success': True,
            'data': [t.to_dict() for t in types]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@vendor_bp.route('/table-types', methods=['POST'])
def create_table_type():
    """Create a new table type"""
    try:
        data = request.get_json()
        
        table_type = TableType(
            vendor_id=data.get('vendor_id'),
            name=data.get('name'),
            description=data.get('description'),
            min_capacity=data.get('min_capacity', 2),
            max_capacity=data.get('max_capacity', 6),
            base_price=data.get('base_price'),
            is_active=data.get('is_active', True)
        )
        
        db.session.add(table_type)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': table_type.to_dict(),
            'message': 'Table type created successfully'
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@vendor_bp.route('/table-types/<int:type_id>', methods=['PUT'])
def update_table_type(type_id):
    """Update table type"""
    try:
        table_type = TableType.query.get(type_id)
        if not table_type:
            return jsonify({
                'success': False,
                'message': 'Table type not found'
            }), 404
        
        data = request.get_json()
        
        if 'name' in data:
            table_type.name = data['name']
        if 'description' in data:
            table_type.description = data['description']
        if 'min_capacity' in data:
            table_type.min_capacity = data['min_capacity']
        if 'max_capacity' in data:
            table_type.max_capacity = data['max_capacity']
        if 'base_price' in data:
            table_type.base_price = data['base_price']
        if 'is_active' in data:
            table_type.is_active = data['is_active']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': table_type.to_dict(),
            'message': 'Table type updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ==================== TABLES ====================

@vendor_bp.route('/vendors/<int:vendor_id>/tables', methods=['GET'])
def get_tables(vendor_id):
    """Get all tables for a vendor"""
    try:
        tables = Table.query.filter_by(vendor_id=vendor_id).all()
        result = []
        for t in tables:
            data = t.to_dict()
            data['type_name'] = t.table_type.name if t.table_type else None
            result.append(data)
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@vendor_bp.route('/vendors/<int:vendor_id>/tables/available', methods=['GET'])
def get_available_tables(vendor_id):
    """Get available tables for booking"""
    try:
        date = request.args.get('date')
        time = request.args.get('time')
        
        tables = Table.query.filter_by(vendor_id=vendor_id, status='free').all()
        result = []
        for t in tables:
            data = t.to_dict()
            data['type_name'] = t.table_type.name if t.table_type else None
            data['type_price'] = t.table_type.base_price if t.table_type else None
            result.append(data)
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@vendor_bp.route('/tables', methods=['POST'])
def create_table():
    """Create a new table"""
    try:
        data = request.get_json()
        
        table = Table(
            vendor_id=data.get('vendor_id'),
            type_id=data.get('type_id'),
            table_number=data.get('table_number'),
            capacity=data.get('capacity'),
            status=data.get('status', 'free'),
            position_x=data.get('position_x'),
            position_y=data.get('position_y')
        )
        
        db.session.add(table)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': table.to_dict(),
            'message': 'Table created successfully'
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@vendor_bp.route('/tables/<int:table_id>', methods=['PUT'])
def update_table(table_id):
    """Update table"""
    try:
        table = Table.query.get(table_id)
        if not table:
            return jsonify({
                'success': False,
                'message': 'Table not found'
            }), 404
        
        data = request.get_json()
        
        if 'table_number' in data:
            table.table_number = data['table_number']
        if 'capacity' in data:
            table.capacity = data['capacity']
        if 'status' in data:
            table.status = data['status']
        if 'position_x' in data:
            table.position_x = data['position_x']
        if 'position_y' in data:
            table.position_y = data['position_y']
        if 'type_id' in data:
            table.type_id = data['type_id']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': table.to_dict(),
            'message': 'Table updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ==================== TIME SLOTS ====================

@vendor_bp.route('/vendors/<int:vendor_id>/slots', methods=['GET'])
def get_time_slots(vendor_id):
    """Get all time slots for a vendor"""
    try:
        slots = TimeSlot.query.filter_by(vendor_id=vendor_id, is_active=True).all()
        return jsonify({
            'success': True,
            'data': [s.to_dict() for s in slots]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@vendor_bp.route('/slots', methods=['POST'])
def create_time_slot():
    """Create a new time slot"""
    try:
        data = request.get_json()
        
        slot = TimeSlot(
            vendor_id=data.get('vendor_id'),
            day_of_week=data.get('day_of_week'),
            start_time=data.get('start_time'),
            end_time=data.get('end_time'),
            is_active=data.get('is_active', True)
        )
        
        db.session.add(slot)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': slot.to_dict(),
            'message': 'Time slot created successfully'
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@vendor_bp.route('/slots/<int:slot_id>', methods=['PUT'])
def update_time_slot(slot_id):
    """Update time slot"""
    try:
        slot = TimeSlot.query.get(slot_id)
        if not slot:
            return jsonify({
                'success': False,
                'message': 'Time slot not found'
            }), 404
        
        data = request.get_json()
        
        if 'day_of_week' in data:
            slot.day_of_week = data['day_of_week']
        if 'start_time' in data:
            slot.start_time = data['start_time']
        if 'end_time' in data:
            slot.end_time = data['end_time']
        if 'is_active' in data:
            slot.is_active = data['is_active']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': slot.to_dict(),
            'message': 'Time slot updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ==================== VENDOR SETTINGS ====================

@vendor_bp.route('/vendors/<int:vendor_id>/settings', methods=['GET'])
def get_vendor_settings(vendor_id):
    """Get vendor settings"""
    try:
        settings = VendorSettings.query.filter_by(vendor_id=vendor_id).first()
        if not settings:
            # Create default settings
            settings = VendorSettings(vendor_id=vendor_id)
            db.session.add(settings)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'data': settings.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@vendor_bp.route('/vendors/<int:vendor_id>/settings', methods=['PUT'])
def update_vendor_settings(vendor_id):
    """Update vendor settings"""
    try:
        settings = VendorSettings.query.filter_by(vendor_id=vendor_id).first()
        if not settings:
            settings = VendorSettings(vendor_id=vendor_id)
            db.session.add(settings)
        
        data = request.get_json()
        
        if 'advance_booking_hours' in data:
            settings.advance_booking_hours = data['advance_booking_hours']
        if 'min_booking_duration' in data:
            settings.min_booking_duration = data['min_booking_duration']
        if 'max_booking_duration' in data:
            settings.max_booking_duration = data['max_booking_duration']
        if 'cancellation_policy' in data:
            settings.cancellation_policy = data['cancellation_policy']
        if 'terms_conditions' in data:
            settings.terms_conditions = data['terms_conditions']
        if 'contact_phone' in data:
            settings.contact_phone = data['contact_phone']
        if 'contact_email' in data:
            settings.contact_email = data['contact_email']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': settings.to_dict(),
            'message': 'Settings updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ==================== HEALTH CHECK ====================

@vendor_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'success': True,
        'message': 'Nightlife Vendor Service is running',
        'service': 'vendor'
    })
