"""
Nightlife Booking Service Routes
===========================
API endpoints for: Bookings, Reservations, Payments
"""

from flask import Blueprint, request, jsonify
from . import db
from .models import Booking, BookingPayment, BookingTimeline
from datetime import datetime, date
import json
import random
import string

booking_bp = Blueprint('booking', __name__)

def generate_booking_ref():
    """Generate unique booking reference"""
    prefix = "NLB"
    year = datetime.now().year
    random_num = ''.join(random.choices(string.digits, k=4))
    return f"{prefix}-{year}-{random_num}"

def add_timeline(booking_id, event_type, event_data=None):
    """Add timeline event"""
    timeline = BookingTimeline(
        booking_id=booking_id,
        event_type=event_type,
        event_data=json.dumps(event_data) if event_data else None
    )
    db.session.add(timeline)

# ==================== BOOKINGS ====================

@booking_bp.route('/bookings', methods=['POST'])
def create_booking():
    """Create a new table booking"""
    try:
        data = request.get_json()
        
        # Generate booking reference
        booking_ref = generate_booking_ref()
        
        booking = Booking(
            booking_ref=booking_ref,
            vendor_id=data.get('vendor_id'),
            club_name=data.get('club_name'),
            user_id=data.get('user_id'),
            user_name=data.get('user_name'),
            user_phone=data.get('user_phone'),
            user_email=data.get('user_email'),
            table_type_id=data.get('table_type_id'),
            table_type_name=data.get('table_type_name'),
            table_number=data.get('table_number'),
            booking_date=datetime.strptime(data.get('booking_date'), '%Y-%m-%d').date(),
            booking_time=data.get('booking_time'),
            duration=data.get('duration', 2),
            guest_count=data.get('guest_count', 2),
            base_amount=data.get('base_amount', 0),
            addon_amount=data.get('addon_amount', 0),
            discount_amount=data.get('discount_amount', 0),
            total_amount=data.get('total_amount', 0),
            special_requests=data.get('special_requests'),
            status='pending',
            payment_status='pending'
        )
        
        db.session.add(booking)
        db.session.flush()  # Get booking ID
        
        # Add timeline
        add_timeline(booking.id, 'created', {'total_amount': booking.total_amount})
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': booking.to_dict(),
            'message': 'Booking created successfully'
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@booking_bp.route('/bookings/<int:booking_id>', methods=['GET'])
def get_booking(booking_id):
    """Get single booking details"""
    try:
        booking = Booking.query.get(booking_id)
        if not booking:
            return jsonify({
                'success': False,
                'message': 'Booking not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': booking.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@booking_bp.route('/bookings/ref/<booking_ref>', methods=['GET'])
def get_booking_by_ref(booking_ref):
    """Get booking by reference number"""
    try:
        booking = Booking.query.filter_by(booking_ref=booking_ref).first()
        if not booking:
            return jsonify({
                'success': False,
                'message': 'Booking not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': booking.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@booking_bp.route('/bookings/user/<int:user_id>', methods=['GET'])
def get_user_bookings(user_id):
    """Get all bookings for a user"""
    try:
        bookings = Booking.query.filter_by(user_id=user_id).order_by(Booking.created_at.desc()).all()
        return jsonify({
            'success': True,
            'data': [b.to_dict() for b in bookings]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@booking_bp.route('/bookings/vendor/<int:vendor_id>', methods=['GET'])
def get_vendor_bookings(vendor_id):
    """Get all bookings for a vendor"""
    try:
        status = request.args.get('status')
        query = Booking.query.filter_by(vendor_id=vendor_id)
        
        if status:
            query = query.filter_by(status=status)
        
        bookings = query.order_by(Booking.booking_date.desc(), Booking.booking_time.desc()).all()
        return jsonify({
            'success': True,
            'data': [b.to_dict() for b in bookings]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@booking_bp.route('/bookings/<int:booking_id>', methods=['PUT'])
def update_booking(booking_id):
    """Update booking details"""
    try:
        booking = Booking.query.get(booking_id)
        if not booking:
            return jsonify({
                'success': False,
                'message': 'Booking not found'
            }), 404
        
        data = request.get_json()
        
        if 'table_number' in data:
            booking.table_number = data['table_number']
        if 'booking_time' in data:
            booking.booking_time = data['booking_time']
        if 'duration' in data:
            booking.duration = data['duration']
        if 'guest_count' in data:
            booking.guest_count = data['guest_count']
        if 'special_requests' in data:
            booking.special_requests = data['special_requests']
        
        add_timeline(booking.id, 'updated', data)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': booking.to_dict(),
            'message': 'Booking updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@booking_bp.route('/bookings/<int:booking_id>/confirm', methods=['POST'])
def confirm_booking(booking_id):
    """Confirm a booking"""
    try:
        booking = Booking.query.get(booking_id)
        if not booking:
            return jsonify({
                'success': False,
                'message': 'Booking not found'
            }), 404
        
        booking.status = 'confirmed'
        booking.confirmed_at = datetime.utcnow()
        
        add_timeline(booking.id, 'confirmed', {'by': 'vendor'})
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': booking.to_dict(),
            'message': 'Booking confirmed successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@booking_bp.route('/bookings/<int:booking_id>/cancel', methods=['POST'])
def cancel_booking(booking_id):
    """Cancel a booking"""
    try:
        booking = Booking.query.get(booking_id)
        if not booking:
            return jsonify({
                'success': False,
                'message': 'Booking not found'
            }), 404
        
        data = request.get_json() or {}
        
        booking.status = 'cancelled'
        booking.cancelled_at = datetime.utcnow()
        
        # If payment was made, mark for refund
        if booking.payment_status == 'paid':
            booking.payment_status = 'refund_initiated'
        
        add_timeline(booking.id, 'cancelled', {'reason': data.get('reason', 'User requested')})
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': booking.to_dict(),
            'message': 'Booking cancelled successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@booking_bp.route('/bookings/<int:booking_id>/complete', methods=['POST'])
def complete_booking(booking_id):
    """Mark booking as completed"""
    try:
        booking = Booking.query.get(booking_id)
        if not booking:
            return jsonify({
                'success': False,
                'message': 'Booking not found'
            }), 404
        
        booking.status = 'completed'
        
        add_timeline(booking.id, 'completed', {'by': 'vendor'})
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': booking.to_dict(),
            'message': 'Booking completed successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ==================== PAYMENTS ====================

@booking_bp.route('/bookings/<int:booking_id>/payment', methods=['POST'])
def update_payment(booking_id):
    """Update payment details for a booking"""
    try:
        booking = Booking.query.get(booking_id)
        if not booking:
            return jsonify({
                'success': False,
                'message': 'Booking not found'
            }), 404
        
        data = request.get_json()
        
        booking.payment_method = data.get('payment_method')
        booking.payment_ref = data.get('payment_ref')
        booking.payment_status = data.get('payment_status', 'paid')
        
        if booking.payment_status == 'paid':
            booking.payment_time = datetime.utcnow()
        
        # Create payment record
        payment = BookingPayment(
            booking_id=booking_id,
            amount=booking.total_amount,
            payment_method=data.get('payment_method'),
            payment_status=booking.payment_status,
            transaction_id=data.get('payment_ref'),
            razorpay_order_id=data.get('razorpay_order_id'),
            razorpay_payment_id=data.get('razorpay_payment_id'),
            upi_transaction_id=data.get('upi_transaction_id'),
            response_data=json.dumps(data.get('response_data', {}))
        )
        
        db.session.add(payment)
        add_timeline(booking.id, 'payment_updated', {
            'status': booking.payment_status,
            'method': booking.payment_method
        })
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': booking.to_dict(),
            'message': 'Payment updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ==================== TIMELINE ====================

@booking_bp.route('/bookings/<int:booking_id>/timeline', methods=['GET'])
def get_booking_timeline(booking_id):
    """Get booking timeline"""
    try:
        timeline = BookingTimeline.query.filter_by(booking_id=booking_id).order_by(BookingTimeline.created_at.asc()).all()
        return jsonify({
            'success': True,
            'data': [t.to_dict() for t in timeline]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ==================== HEALTH CHECK ====================

@booking_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'success': True,
        'message': 'Nightlife Booking Service is running',
        'service': 'booking'
    })
