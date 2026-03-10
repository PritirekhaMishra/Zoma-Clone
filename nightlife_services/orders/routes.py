"""
Nightlife Order Service Routes
===========================
API endpoints for: Orders, Order Items, Delivery Tracking
"""

from flask import Blueprint, request, jsonify
from . import db
from .models import Order, OrderItem, OrderStatus, OrderDelivery
from datetime import datetime, timedelta
import json
import random
import string

orders_bp = Blueprint('orders', __name__)

def generate_order_ref():
    """Generate unique order reference"""
    prefix = "NLO"
    year = datetime.now().year
    random_num = ''.join(random.choices(string.digits, k=4))
    return f"{prefix}-{year}-{random_num}"

def add_status_history(order_id, status, notes=None):
    """Add status history entry"""
    status_entry = OrderStatus(
        order_id=order_id,
        status=status,
        notes=notes
    )
    db.session.add(status_entry)

# ==================== ORDERS ====================

@orders_bp.route('/orders', methods=['POST'])
def create_order():
    """Create a new order"""
    try:
        data = request.get_json()
        
        # Generate order reference
        order_ref = generate_order_ref()
        
        # Calculate totals
        items_data = data.get('items', [])
        subtotal = sum(item.get('quantity', 1) * item.get('unit_price', 0) for item in items_data)
        tax_amount = subtotal * 0.18  # 18% tax
        delivery_fee = data.get('delivery_fee', 0)
        discount_amount = data.get('discount_amount', 0)
        total_amount = subtotal + tax_amount + delivery_fee - discount_amount
        
        order = Order(
            order_ref=order_ref,
            vendor_id=data.get('vendor_id'),
            club_id=data.get('club_id'),
            club_name=data.get('club_name'),
            booking_id=data.get('booking_id'),
            user_id=data.get('user_id'),
            user_name=data.get('user_name'),
            user_phone=data.get('user_phone'),
            user_email=data.get('user_email'),
            order_type=data.get('order_type', 'dine_in'),
            table_number=data.get('table_number'),
            subtotal=subtotal,
            tax_amount=tax_amount,
            delivery_fee=delivery_fee,
            discount_amount=discount_amount,
            total_amount=total_amount,
            delivery_address=data.get('delivery_address'),
            delivery_lat=data.get('delivery_lat'),
            delivery_lon=data.get('delivery_lon'),
            instructions=data.get('instructions'),
            status='pending',
            payment_status='pending'
        )
        
        db.session.add(order)
        db.session.flush()  # Get order ID
        
        # Add order items
        for item_data in items_data:
            item = OrderItem(
                order_id=order.id,
                item_id=item_data.get('item_id'),
                item_name=item_data.get('item_name'),
                item_category=item_data.get('item_category'),
                quantity=item_data.get('quantity', 1),
                unit_price=item_data.get('unit_price'),
                total_price=item_data.get('quantity', 1) * item_data.get('unit_price', 0),
                special_instructions=item_data.get('special_instructions')
            )
            db.session.add(item)
        
        # Add status history
        add_status_history(order.id, 'pending', 'Order placed')
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': order.to_dict(),
            'items': [i.to_dict() for i in order.items],
            'message': 'Order created successfully'
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@orders_bp.route('/orders/<int:order_id>', methods=['GET'])
def get_order(order_id):
    """Get single order details"""
    try:
        order = Order.query.get(order_id)
        if not order:
            return jsonify({
                'success': False,
                'message': 'Order not found'
            }), 404
        
        result = order.to_dict()
        result['items'] = [i.to_dict() for i in order.items]
        
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@orders_bp.route('/orders/ref/<order_ref>', methods=['GET'])
def get_order_by_ref(order_ref):
    """Get order by reference number"""
    try:
        order = Order.query.filter_by(order_ref=order_ref).first()
        if not order:
            return jsonify({
                'success': False,
                'message': 'Order not found'
            }), 404
        
        result = order.to_dict()
        result['items'] = [i.to_dict() for i in order.items]
        
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@orders_bp.route('/orders/user/<int:user_id>', methods=['GET'])
def get_user_orders(user_id):
    """Get all orders for a user"""
    try:
        orders = Order.query.filter_by(user_id=user_id).order_by(Order.created_at.desc()).all()
        result = []
        for o in orders:
            order_data = o.to_dict()
            order_data['items'] = [i.to_dict() for i in o.items]
            result.append(order_data)
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@orders_bp.route('/orders/vendor/<int:vendor_id>', methods=['GET'])
def get_vendor_orders(vendor_id):
    """Get all orders for a vendor"""
    try:
        status = request.args.get('status')
        query = Order.query.filter_by(vendor_id=vendor_id)
        
        if status:
            query = query.filter_by(status=status)
        
        orders = query.order_by(Order.created_at.desc()).all()
        result = []
        for o in orders:
            order_data = o.to_dict()
            order_data['items'] = [i.to_dict() for i in o.items]
            result.append(order_data)
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@orders_bp.route('/orders/<int:order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    """Update order status"""
    try:
        order = Order.query.get(order_id)
        if not order:
            return jsonify({
                'success': False,
                'message': 'Order not found'
            }), 404
        
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({
                'success': False,
                'message': 'Status is required'
            }), 400
        
        old_status = order.status
        order.status = new_status
        
        # Update timestamps based on status
        if new_status == 'confirmed' and not order.confirmed_at:
            order.confirmed_at = datetime.utcnow()
        elif new_status == 'preparing' and not order.preparing_at:
            order.preparing_at = datetime.utcnow()
        elif new_status == 'ready' and not order.ready_at:
            order.ready_at = datetime.utcnow()
        elif new_status == 'delivered' and not order.delivered_at:
            order.delivered_at = datetime.utcnow()
        elif new_status == 'cancelled' and not order.cancelled_at:
            order.cancelled_at = datetime.utcnow()
        
        # Add status history
        add_status_history(order.id, new_status, data.get('notes'))
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': order.to_dict(),
            'message': f'Order status updated to {new_status}'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@orders_bp.route('/orders/<int:order_id>/cancel', methods=['POST'])
def cancel_order(order_id):
    """Cancel an order"""
    try:
        order = Order.query.get(order_id)
        if not order:
            return jsonify({
                'success': False,
                'message': 'Order not found'
            }), 404
        
        # Only allow cancellation of pending orders
        if order.status not in ['pending', 'confirmed']:
            return jsonify({
                'success': False,
                'message': 'Cannot cancel order in current status'
            }), 400
        
        data = request.get_json() or {}
        
        order.status = 'cancelled'
        order.cancelled_at = datetime.utcnow()
        
        add_status_history(order.id, 'cancelled', data.get('reason', 'User requested'))
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': order.to_dict(),
            'message': 'Order cancelled successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ==================== ORDER ITEMS ====================

@orders_bp.route('/orders/<int:order_id>/items', methods=['GET'])
def get_order_items(order_id):
    """Get all items for an order"""
    try:
        order = Order.query.get(order_id)
        if not order:
            return jsonify({
                'success': False,
                'message': 'Order not found'
            }), 404
        
        items = OrderItem.query.filter_by(order_id=order_id).all()
        
        return jsonify({
            'success': True,
            'data': [i.to_dict() for i in items]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ==================== DELIVERY ====================

@orders_bp.route('/orders/<int:order_id>/delivery', methods=['POST'])
def assign_delivery(order_id):
    """Assign delivery partner to order"""
    try:
        order = Order.query.get(order_id)
        if not order:
            return jsonify({
                'success': False,
                'message': 'Order not found'
            }), 404
        
        data = request.get_json()
        
        delivery = OrderDelivery(
            order_id=order_id,
            delivery_partner_name=data.get('delivery_partner_name'),
            delivery_partner_phone=data.get('delivery_partner_phone'),
            estimated_delivery_time=datetime.utcnow() + timedelta(minutes=data.get('eta_minutes', 30)),
            delivery_status='assigned'
        )
        
        db.session.add(delivery)
        
        order.status = 'out_for_delivery'
        add_status_history(order.id, 'out_for_delivery', 'Delivery partner assigned')
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': delivery.to_dict(),
            'message': 'Delivery assigned successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@orders_bp.route('/orders/<int:order_id>/delivery', methods=['GET'])
def get_delivery_status(order_id):
    """Get delivery status for an order"""
    try:
        delivery = OrderDelivery.query.filter_by(order_id=order_id).first()
        if not delivery:
            return jsonify({
                'success': False,
                'message': 'Delivery not found'
            }), 404
        
        return jsonify({
            'success': True,
            'data': delivery.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@orders_bp.route('/orders/<int:order_id>/delivery/update', methods=['PUT'])
def update_delivery_status(order_id):
    """Update delivery status"""
    try:
        delivery = OrderDelivery.query.filter_by(order_id=order_id).first()
        if not delivery:
            return jsonify({
                'success': False,
                'message': 'Delivery not found'
            }), 404
        
        data = request.get_json()
        
        if 'current_lat' in data:
            delivery.current_lat = data['current_lat']
        if 'current_lon' in data:
            delivery.current_lon = data['current_lon']
        if 'delivery_status' in data:
            delivery.delivery_status = data['delivery_status']
            
            if data['delivery_status'] == 'delivered':
                delivery.actual_delivery_time = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': delivery.to_dict(),
            'message': 'Delivery status updated'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ==================== STATUS HISTORY ====================

@orders_bp.route('/orders/<int:order_id>/history', methods=['GET'])
def get_order_history(order_id):
    """Get order status history"""
    try:
        history = OrderStatus.query.filter_by(order_id=order_id).order_by(OrderStatus.created_at.asc()).all()
        return jsonify({
            'success': True,
            'data': [h.to_dict() for h in history]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ==================== HEALTH CHECK ====================

@orders_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'success': True,
        'message': 'Nightlife Order Service is running',
        'service': 'orders'
    })
