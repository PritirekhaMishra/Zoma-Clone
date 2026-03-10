"""
Restaurant API Routes
====================
All endpoints start with /api/rest
"""

from flask import Blueprint, request, jsonify
import psycopg2
import os
from datetime import datetime
import uuid

restaurant_bp = Blueprint('restaurant', __name__)

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'zoma_restaurant',
    'user': 'postgres',
    'password': 'password'
}

def get_db_connection():
    """Get database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def dict_from_row(row, columns):
    """Convert database row to dictionary"""
    return dict(zip(columns, row))

# ============================================================
# VENDOR ROUTES
# ============================================================

@restaurant_bp.route('/vendor/me', methods=['GET'])
def get_vendor():
    """Get vendor info"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database not available'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name, email, phone, address, rating FROM vendors WHERE id = %s", (vendor_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if not row:
            return jsonify({'success': False, 'message': 'Vendor not found'}), 404
        
        return jsonify({
            'success': True,
            'vendor': {
                'id': row[0],
                'name': row[1],
                'email': row[2],
                'phone': row[3],
                'address': row[4],
                'rating': row[5]
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@restaurant_bp.route('/vendor/by_email', methods=['POST'])
def get_vendor_by_email():
    """Get or create vendor by email"""
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    name = data.get('restaurant_name', '').strip()
    
    if not email:
        return jsonify({'success': False, 'message': 'Email required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database not available'}), 500
    
    try:
        cur = conn.cursor()
        
        # Check if vendor exists
        cur.execute("SELECT id, name, email FROM vendors WHERE email = %s", (email,))
        row = cur.fetchone()
        
        if not row:
            # Create new vendor
            vendor_id = cur.execute(
                "INSERT INTO vendors (name, email, created_at) VALUES (%s, %s, %s) RETURNING id",
                (name or email.split('@')[0], email, datetime.now())
            )
            conn.commit()
            cur.execute("SELECT id, name, email FROM vendors WHERE email = %s", (email,))
            row = cur.fetchone()
        
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'vendor': {
                'id': row[0],
                'name': row[1],
                'email': row[2]
            }
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# ============================================================
# MENU ROUTES
# ============================================================

@restaurant_bp.route('/menu', methods=['GET'])
@restaurant_bp.route('/vendor/<int:vendor_id>/menu', methods=['GET'])
def get_menu(vendor_id=None):
    """Get menu items for vendor"""
    if not vendor_id:
        vendor_id = request.args.get('vendor_id')
    
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database not available'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, name, description, price, category, image_url, available
            FROM menu_items 
            WHERE vendor_id = %s AND available = true
            ORDER BY category, name
        """, (vendor_id,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        menu = []
        for row in rows:
            menu.append({
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'price': row[3],
                'category': row[4],
                'image_url': row[5],
                'available': row[6]
            })
        
        return jsonify({'success': True, 'menu': menu})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@restaurant_bp.route('/menu', methods=['POST'])
def add_menu_item():
    """Add menu item"""
    data = request.get_json()
    vendor_id = data.get('vendor_id')
    
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database not available'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO menu_items (vendor_id, name, description, price, category, image_url, available)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            vendor_id,
            data.get('name', ''),
            data.get('description', ''),
            data.get('price', 0),
            data.get('category', 'main'),
            data.get('image_url', ''),
            data.get('available', True)
        ))
        item_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'item_id': item_id})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# ============================================================
# ORDER ROUTES
# ============================================================

@restaurant_bp.route('/orders', methods=['GET'])
def get_orders():
    """Get orders for vendor"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database not available'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, order_id, customer_name, items, total, status, created_at
            FROM orders 
            WHERE vendor_id = %s
            ORDER BY created_at DESC
            LIMIT 50
        """, (vendor_id,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        orders = []
        for row in rows:
            orders.append({
                'id': row[0],
                'order_id': row[1],
                'customer_name': row[2],
                'items': row[3],
                'total': row[4],
                'status': row[5],
                'created_at': row[6].isoformat() if row[6] else None
            })
        
        return jsonify({'success': True, 'orders': orders})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@restaurant_bp.route('/orders', methods=['POST'])
def create_order():
    """Create new order"""
    data = request.get_json()
    vendor_id = data.get('vendor_id')
    
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database not available'}), 500
    
    try:
        order_id = f"ORD{uuid.uuid4().hex[:8].upper()}"
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO orders (vendor_id, order_id, customer_name, customer_phone, items, total, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            vendor_id,
            order_id,
            data.get('customer_name', ''),
            data.get('customer_phone', ''),
            str(data.get('items', [])),
            data.get('total', 0),
            'pending'
        ))
        order_db_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'order_id': order_id,
            'id': order_db_id,
            'total': data.get('total', 0)
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@restaurant_bp.route('/orders/<int:order_id>/status', methods=['PUT'])
def update_order_status(order_id):
    """Update order status"""
    data = request.get_json()
    status = data.get('status')
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database not available'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute("UPDATE orders SET status = %s WHERE id = %s", (status, order_id))
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Status updated'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

# ============================================================
# TABLE BOOKING ROUTES
# ============================================================

@restaurant_bp.route('/tables', methods=['GET'])
def get_tables():
    """Get table types for vendor"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database not available'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, name, capacity, total_tables, price, available
            FROM table_types 
            WHERE vendor_id = %s
            ORDER BY capacity
        """, (vendor_id,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        tables = []
        for row in rows:
            tables.append({
                'id': row[0],
                'name': row[1],
                'capacity': row[2],
                'total_tables': row[3],
                'price': row[4],
                'available': row[5]
            })
        
        return jsonify({'success': True, 'tables': tables})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@restaurant_bp.route('/bookings', methods=['GET'])
def get_bookings():
    """Get table bookings for vendor"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database not available'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, customer_name, phone, date, time, table_type, guests, status, created_at
            FROM bookings 
            WHERE vendor_id = %s
            ORDER BY date DESC, time DESC
            LIMIT 50
        """, (vendor_id,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        bookings = []
        for row in rows:
            bookings.append({
                'id': row[0],
                'customer_name': row[1],
                'phone': row[2],
                'date': str(row[3]) if row[3] else None,
                'time': row[4],
                'table_type': row[5],
                'guests': row[6],
                'status': row[7],
                'created_at': row[8].isoformat() if row[8] else None
            })
        
        return jsonify({'success': True, 'bookings': bookings})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@restaurant_bp.route('/bookings', methods=['POST'])
def create_booking():
    """Create table booking"""
    data = request.get_json()
    vendor_id = data.get('vendor_id')
    
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database not available'}), 500
    
    try:
        booking_id = f"BK{uuid.uuid4().hex[:8].upper()}"
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO bookings (vendor_id, booking_id, customer_name, phone, date, time, table_type, guests, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            vendor_id,
            booking_id,
            data.get('customer_name', ''),
            data.get('phone', ''),
            data.get('date', ''),
            data.get('time', ''),
            data.get('table_type', ''),
            data.get('guests', 1),
            'confirmed'
        ))
        db_booking_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'booking_id': booking_id,
            'id': db_booking_id
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
