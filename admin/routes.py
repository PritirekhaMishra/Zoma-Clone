"""
Admin API Routes
===============
All endpoints start with /api/admin
"""

from flask import Blueprint, request, jsonify
import psycopg2
from datetime import datetime

admin_bp = Blueprint('admin', __name__)

# Database configurations
RESTAURANT_DB = {
    'host': 'localhost',
    'port': 5432,
    'database': 'zoma_restaurant',
    'user': 'postgres',
    'password': 'password'
}

NIGHTLIFE_DB = {
    'host': 'localhost',
    'port': 5432,
    'database': 'zoma_nightlife',
    'user': 'postgres',
    'password': 'password'
}

def get_db_connection(db='restaurant'):
    """Get database connection"""
    config = RESTAURANT_DB if db == 'restaurant' else NIGHTLIFE_DB
    try:
        conn = psycopg2.connect(**config)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

# ============================================================
# ADMIN ROUTES
# ============================================================

@admin_bp.route('/stats', methods=['GET'])
def get_stats():
    """Get overall system statistics"""
    stats = {
        'restaurant': {},
        'nightlife': {},
        'total': {}
    }
    
    # Restaurant stats
    conn = get_db_connection('restaurant')
    if conn:
        try:
            cur = conn.cursor()
            
            # Vendor count
            cur.execute("SELECT COUNT(*) FROM vendors")
            stats['restaurant']['vendors'] = cur.fetchone()[0] or 0
            
            # Order count
            cur.execute("SELECT COUNT(*) FROM orders")
            stats['restaurant']['orders'] = cur.fetchone()[0] or 0
            
            # Menu items count
            cur.execute("SELECT COUNT(*) FROM menu_items")
            stats['restaurant']['menu_items'] = cur.fetchone()[0] or 0
            
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Restaurant stats error: {e}")
    
    # Nightlife stats
    conn = get_db_connection('nightlife')
    if conn:
        try:
            cur = conn.cursor()
            
            # Vendor count
            cur.execute("SELECT COUNT(*) FROM vendors")
            stats['nightlife']['vendors'] = cur.fetchone()[0] or 0
            
            # Booking count
            cur.execute("SELECT COUNT(*) FROM nightlife_bookings")
            stats['nightlife']['bookings'] = cur.fetchone()[0] or 0
            
            # Table types count
            cur.execute("SELECT COUNT(*) FROM nightlife_table_types")
            stats['nightlife']['table_types'] = cur.fetchone()[0] or 0
            
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Nightlife stats error: {e}")
    
    return jsonify({
        'success': True,
        'stats': stats
    })

@admin_bp.route('/vendors', methods=['GET'])
def get_all_vendors():
    """Get all vendors from both systems"""
    vendors = []
    
    # Restaurant vendors
    conn = get_db_connection('restaurant')
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, name, email, phone, created_at, 'restaurant' as system
                FROM vendors ORDER BY created_at DESC LIMIT 50
            """)
            for row in cur.fetchall():
                vendors.append({
                    'id': row[0],
                    'name': row[1],
                    'email': row[2],
                    'phone': row[3],
                    'created_at': row[4].isoformat() if row[4] else None,
                    'system': row[5]
                })
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Restaurant vendors error: {e}")
    
    # Nightlife vendors
    conn = get_db_connection('nightlife')
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, name, email, created_at, 'nightlife' as system
                FROM vendors ORDER BY created_at DESC LIMIT 50
            """)
            for row in cur.fetchall():
                vendors.append({
                    'id': row[0],
                    'name': row[1],
                    'email': row[2],
                    'phone': None,
                    'created_at': row[3].isoformat() if row[3] else None,
                    'system': row[4]
                })
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Nightlife vendors error: {e}")
    
    return jsonify({
        'success': True,
        'vendors': vendors
    })

@admin_bp.route('/vendors/<system>/<int:vendor_id>', methods=['DELETE'])
def delete_vendor(system, vendor_id):
    """Delete a vendor from a system"""
    if system not in ['restaurant', 'nightlife']:
        return jsonify({'success': False, 'message': 'Invalid system'}), 400
    
    conn = get_db_connection(system)
    if not conn:
        return jsonify({'success': False, 'message': 'Database not available'}), 500
    
    try:
        cur = conn.cursor()
        
        if system == 'restaurant':
            cur.execute("DELETE FROM vendors WHERE id = %s", (vendor_id,))
        else:
            cur.execute("DELETE FROM vendors WHERE id = %s", (vendor_id,))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'message': f'Vendor {vendor_id} deleted from {system}'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/orders', methods=['GET'])
def get_all_orders():
    """Get all orders from restaurant system"""
    system = request.args.get('system', 'restaurant')
    
    conn = get_db_connection(system)
    if not conn:
        return jsonify({'success': False, 'message': 'Database not available'}), 500
    
    try:
        cur = conn.cursor()
        
        if system == 'restaurant':
            cur.execute("""
                SELECT o.id, o.order_id, o.customer_name, o.items, o.total, o.status, o.created_at,
                       v.name as vendor_name
                FROM orders o
                LEFT JOIN vendors v ON o.vendor_id = v.id
                ORDER BY o.created_at DESC
                LIMIT 100
            """)
        else:
            cur.execute("""
                SELECT b.id, b.booking_id, b.customer, b.phone, b.date, b.price, b.status, b.created_at,
                       v.name as vendor_name
                FROM nightlife_bookings b
                LEFT JOIN vendors v ON b.vendor_id = v.id
                ORDER BY b.created_at DESC
                LIMIT 100
            """)
        
        orders = []
        for row in cur.fetchall():
            if system == 'restaurant':
                orders.append({
                    'id': row[0],
                    'order_id': row[1],
                    'customer': row[2],
                    'items': row[3],
                    'total': row[4],
                    'status': row[5],
                    'created_at': row[6].isoformat() if row[6] else None,
                    'vendor': row[7]
                })
            else:
                orders.append({
                    'id': row[0],
                    'order_id': row[1],
                    'customer': row[2],
                    'phone': row[3],
                    'date': str(row[4]) if row[4] else None,
                    'total': row[5],
                    'status': row[6],
                    'created_at': row[7].isoformat() if row[7] else None,
                    'vendor': row[8]
                })
        
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'orders': orders,
            'system': system
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ============================================================
# HEALTH CHECK
# ============================================================

@admin_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'success': True,
        'message': 'Admin API is running'
    })
