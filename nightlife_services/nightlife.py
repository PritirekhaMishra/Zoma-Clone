"""
Nightlife Booking Blueprint
=========================
Complete nightlife booking system with:
- OTP verification
- Real-time availability
- Transaction handling
- Email notifications
- Closed dates
"""

from flask import Blueprint, request, jsonify
import psycopg2
import random
import string
from datetime import datetime, timedelta
from functools import wraps

nightlife_bp = Blueprint('nightlife', __name__)

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': '5432',
    'database': 'zoma_nightlife',
    'user': 'postgres',
    'password': 'password'
}

# Config
OTP_EXPIRE_MINUTES = 10
MAX_BOOKINGS_PER_USER_PER_DAY = 3


def get_db_connection():
    """Get PostgreSQL database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None


def generate_booking_id(vendor_id):
    """Generate unique booking ID: NL-20260304-0001"""
    conn = get_db_connection()
    if not conn:
        return None
    
    cur = conn.cursor()
    today = datetime.now().strftime('%Y%m%d')
    
    # Get count for today
    cur.execute("""
        SELECT COUNT(*) FROM nightlife_bookings 
        WHERE booking_id LIKE %s
    """, (f'NL-{today}-%',))
    count = cur.fetchone()[0] + 1
    
    cur.close()
    conn.close()
    
    return f"NL-{today}-{count:04d}"


def generate_otp():
    """Generate 6-digit OTP"""
    return ''.join([str(random.randint(0, 9)) for _ in range(6)])


def log_history(booking_id, action, old_status=None, new_status=None, notes=None):
    """Log booking history"""
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO nightlife_booking_history (booking_id, action, old_status, new_status, notes)
            VALUES (%s, %s, %s, %s, %s)
        """, (booking_id, action, old_status, new_status, notes))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"History log error: {e}")


def send_otp_email(user_email, otp_code, booking_data):
    """Send OTP via email (simplified)"""
    print(f"📧 OTP Email: {user_email}, Code: {otp_code}")
    # In production, use email_service
    return True


# ==================== VENDOR ROUTES ====================

@nightlife_bp.route('/vendor/by_email', methods=['POST'])
def vendor_by_email():
    """Get or create vendor by email"""
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    name = data.get('restaurant_name', '').strip()
    
    if not email:
        return jsonify({'success': False, 'message': 'Email required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database unavailable'}), 500
    
    try:
        cur = conn.cursor()
        
        # Check vendor exists
        cur.execute("SELECT id FROM vendors WHERE email = %s", (email,))
        row = cur.fetchone()
        
        if not row:
            # Create vendor
            cur.execute("""
                INSERT INTO vendors (email, name) VALUES (%s, %s) RETURNING id
            """, (email, name or email.split('@')[0]))
            vendor_id = cur.fetchone()[0]
            
            # Create default settings
            cur.execute("""
                INSERT INTO nightlife_settings (vendor_id, max_advance_days, require_otp)
                VALUES (%s, 30, true)
            """, (vendor_id,))
            
            conn.commit()
        
        cur.execute("SELECT id, name, upi_id, banner FROM vendors WHERE email = %s", (email,))
        row = cur.fetchone()
        
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'vendor': {'id': row[0], 'email': email, 'name': row[1], 'upi_id': row[2] or '', 'banner': row[3] or ''}
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@nightlife_bp.route('/vendor/me', methods=['GET'])
def vendor_me():
    """Get vendor info with all data"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database unavailable'}), 500
    
    try:
        cur = conn.cursor()
        
        # Vendor info
        cur.execute("SELECT id, email, name, description, upi_id, banner FROM vendors WHERE id = %s", (vendor_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'Vendor not found'}), 404
        
        vendor = {
            'id': row[0], 'email': row[1], 'restaurant_name': row[2] or '',
            'description': row[3] or '', 'upi_id': row[4] or '', 'banner': row[5] or ''
        }
        
        # Settings
        cur.execute("SELECT max_advance_days, cancel_before_hours, require_otp FROM nightlife_settings WHERE vendor_id = %s", (vendor_id,))
        srow = cur.fetchone()
        settings = {
            'maxAdvanceDays': srow[0] if srow else 30,
            'cancelBeforeHrs': srow[1] if srow else 2,
            'requireOtp': srow[2] if srow else True
        }
        
        # Location
        cur.execute("SELECT address_line1, address_line2, city, state, pincode FROM nightlife_location WHERE vendor_id = %s", (vendor_id,))
        lrow = cur.fetchone()
        location = {
            'addr1': lrow[0] or '', 'addr2': lrow[1] or '', 'city': lrow[2] or '',
            'state': lrow[3] or '', 'pincode': lrow[4] or ''
        } if lrow else {}
        
        # Stats
        cur.execute("SELECT COUNT(*) FROM nightlife_table_types WHERE vendor_id = %s", (vendor_id,))
        total_types = cur.fetchone()[0]
        
        cur.execute("SELECT COALESCE(SUM(total_tables), 0) FROM nightlife_table_types WHERE vendor_id = %s", (vendor_id,))
        total_tables = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM nightlife_bookings WHERE vendor_id = %s", (vendor_id,))
        total_bookings = cur.fetchone()[0]
        
        cur.execute("""
            SELECT COUNT(*) FROM nightlife_bookings 
            WHERE vendor_id = %s AND status = 'confirmed' AND date >= %s
        """, (vendor_id, datetime.now().strftime('%Y-%m-%d')))
        upcoming = cur.fetchone()[0]
        
        stats = {'totalTypes': total_types, 'totalTables': total_tables, 'totalBookings': total_bookings, 'upcomingBookings': upcoming}
        
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'vendor': vendor, 'settings': settings, 'location': location, 'stats': stats})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@nightlife_bp.route('/vendor/<int:vid>/upi', methods=['PUT'])
def vendor_update_upi(vid):
    """Update vendor UPI"""
    data = request.get_json()
    upi_id = data.get('upi_id', '')
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database unavailable'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute("UPDATE vendors SET upi_id = %s, updated_at = %s WHERE id = %s", (upi_id, datetime.now(), vid))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True, 'message': 'UPI updated'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================== TABLE TYPES ====================

@nightlife_bp.route('/types', methods=['POST'])
def create_type():
    """Create/update table type"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    data = request.get_json()
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database unavailable'}), 500
    
    try:
        cur = conn.cursor()
        type_id = data.get('id')
        
        if type_id:
            cur.execute("""
                UPDATE nightlife_table_types 
                SET name = %s, seats = %s, total_tables = %s, price = %s, 
                    cancel_hours = %s, time_start = %s, time_end = %s
                WHERE id = %s AND vendor_id = %s
            """, (data.get('name'), data.get('seats', 2), data.get('total', 1), 
                  data.get('price', 0), data.get('cancel', 2), 
                  data.get('timeStart', '18:00'), data.get('timeEnd', '23:00'),
                  type_id, vendor_id))
        else:
            cur.execute("""
                INSERT INTO nightlife_table_types (vendor_id, name, seats, total_tables, price, cancel_hours, time_start, time_end)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """, (vendor_id, data.get('name'), data.get('seats', 2), data.get('total', 1),
                  data.get('price', 0), data.get('cancel', 2), 
                  data.get('timeStart', '18:00'), data.get('timeEnd', '23:00')))
            type_id = cur.fetchone()[0]
        
        # Update tables
        free_tables = data.get('freeTables', data.get('total', 1))
        
        # Delete existing tables and recreate
        cur.execute("DELETE FROM nightlife_tables WHERE vendor_id = %s AND type_id = %s", (vendor_id, type_id))
        
        for i in range(1, data.get('total', 1) + 1):
            status = 'free' if i <= free_tables else 'reserved'
            cur.execute("""
                INSERT INTO nightlife_tables (vendor_id, type_id, table_number, status)
                VALUES (%s, %s, %s, %s)
            """, (vendor_id, type_id, i, status))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'type': {'id': type_id, 'name': data.get('name')}})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@nightlife_bp.route('/types', methods=['GET'])
def get_types():
    """Get all table types"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database unavailable'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, name, seats, total_tables, price, cancel_hours, time_start, time_end
            FROM nightlife_table_types WHERE vendor_id = %s ORDER BY price
        """, (vendor_id,))
        rows = cur.fetchall()
        
        result = []
        for row in rows:
            cur.execute("""
                SELECT COUNT(*) FROM nightlife_tables 
                WHERE vendor_id = %s AND type_id = %s AND status = 'free'
            """, (vendor_id, row[0]))
            free = cur.fetchone()[0]
            
            cur.execute("""
                SELECT COUNT(*) FROM nightlife_tables 
                WHERE vendor_id = %s AND type_id = %s AND status = 'reserved'
            """, (vendor_id, row[0]))
            reserved = cur.fetchone()[0]
            
            result.append({
                'id': row[0], 'name': row[1], 'seats': row[2], 'total': row[3],
                'freeCount': free, 'reservedCount': reserved, 'price': row[4],
                'cancel': row[5], 'timeStart': row[6], 'timeEnd': row[7],
                'displayTime': f"{row[6]} - {row[7]}"
            })
        
        cur.close()
        conn.close()
        return jsonify({'success': True, 'types': result})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@nightlife_bp.route('/types/<int:type_id>', methods=['DELETE'])
def delete_type(type_id):
    """Delete table type"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database unavailable'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM nightlife_table_types WHERE id = %s AND vendor_id = %s", (type_id, vendor_id))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True, 'message': 'Type deleted'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@nightlife_bp.route('/types/<int:type_id>/tables', methods=['GET'])
def get_type_tables(type_id):
    """Get tables for type"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database unavailable'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, table_number, status FROM nightlife_tables 
            WHERE vendor_id = %s AND type_id = %s ORDER BY table_number
        """, (vendor_id, type_id))
        rows = cur.fetchall()
        
        result = [{'id': r[0], 'num': r[1], 'status': r[2]} for r in rows]
        
        cur.close()
        conn.close()
        return jsonify({'success': True, 'tables': result})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@nightlife_bp.route('/tables/<int:table_id>/toggle', methods=['POST'])
def toggle_table(table_id):
    """Toggle table status"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database unavailable'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT status FROM nightlife_tables WHERE id = %s AND vendor_id = %s", (table_id, vendor_id))
        row = cur.fetchone()
        
        if not row:
            return jsonify({'success': False, 'message': 'Table not found'}), 404
        
        if row[0] == 'reserved':
            return jsonify({'success': False, 'message': 'Cannot change reserved table'}), 400
        
        new_status = 'unavailable' if row[0] == 'free' else 'free'
        cur.execute("UPDATE nightlife_tables SET status = %s WHERE id = %s", (new_status, table_id))
        conn.commit()
        
        cur.close()
        conn.close()
        return jsonify({'success': True, 'status': new_status})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@nightlife_bp.route('/tables/mark_all_free', methods=['POST'])
def mark_all_free():
    """Mark all tables free"""
    vendor_id = request.args.get('vendor_id')
    type_id = request.json.get('typeId') if request.json else None
    
    if not vendor_id or not type_id:
        return jsonify({'success': False, 'message': 'vendor_id and typeId required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database unavailable'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE nightlife_tables SET status = 'free' 
            WHERE vendor_id = %s AND type_id = %s AND status != 'reserved'
        """, (vendor_id, type_id))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True, 'message': 'All tables marked as free'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================== SLOTS ====================

@nightlife_bp.route('/slots', methods=['POST'])
def create_slot():
    """Create slot"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    data = request.get_json()
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database unavailable'}), 500
    
    try:
        cur = conn.cursor()
        slot_id = data.get('id')
        
        if slot_id:
            cur.execute("""
                UPDATE nightlife_slots SET name = %s, start_time = %s, end_time = %s
                WHERE id = %s AND vendor_id = %s
            """, (data.get('name'), data.get('start'), data.get('end'), slot_id, vendor_id))
        else:
            cur.execute("""
                INSERT INTO nightlife_slots (vendor_id, name, start_time, end_time) 
                VALUES (%s, %s, %s, %s) RETURNING id
            """, (vendor_id, data.get('name'), data.get('start'), data.get('end')))
            slot_id = cur.fetchone()[0]
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'slot': {'id': slot_id, 'name': data.get('name')}})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@nightlife_bp.route('/slots', methods=['GET'])
def get_slots():
    """Get all slots"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database unavailable'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, name, start_time, end_time FROM nightlife_slots 
            WHERE vendor_id = %s ORDER BY start_time
        """, (vendor_id,))
        rows = cur.fetchall()
        
        result = [{'id': r[0], 'name': r[1], 'start': r[2], 'end': r[3]} for r in rows]
        
        cur.close()
        conn.close()
        return jsonify({'success': True, 'slots': result})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@nightlife_bp.route('/slots/<int:slot_id>', methods=['DELETE'])
def delete_slot(slot_id):
    """Delete slot"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database unavailable'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM nightlife_slots WHERE id = %s AND vendor_id = %s", (slot_id, vendor_id))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True, 'message': 'Slot deleted'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================== REAL-TIME AVAILABILITY ====================

@nightlife_bp.route('/availability', methods=['GET'])
def get_availability():
    """Get real-time availability for date/slot/type"""
    vendor_id = request.args.get('vendor_id')
    date = request.args.get('date')
    slot_id = request.args.get('slot_id')
    
    if not vendor_id or not date:
        return jsonify({'success': False, 'message': 'vendor_id and date required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database unavailable'}), 500
    
    try:
        cur = conn.cursor()
        
        # Get all table types
        cur.execute("""
            SELECT id, name, seats, total_tables, price FROM nightlife_table_types 
            WHERE vendor_id = %s AND is_active = true
        """, (vendor_id,))
        types = cur.fetchall()
        
        availability = []
        for t in types:
            type_id, name, seats, total, price = t
            
            # Count reserved tables for this date/slot
            if slot_id:
                cur.execute("""
                    SELECT tables_reserved FROM nightlife_bookings 
                    WHERE vendor_id = %s AND date = %s AND slot_id = %s 
                    AND table_type_id = %s AND status IN ('pending_otp', 'confirmed')
                """, (vendor_id, date, slot_id, type_id))
            else:
                cur.execute("""
                    SELECT tables_reserved FROM nightlife_bookings 
                    WHERE vendor_id = %s AND date = %s AND table_type_id = %s 
                    AND status IN ('pending_otp', 'confirmed')
                """, (vendor_id, date, type_id))
            
            reserved_count = 0
            rows = cur.fetchall()
            for r in rows:
                if r[0]:
                    reserved_count += len(r[0])
            
            free = total - reserved_count
            
            if free > 0:
                availability.append({
                    'id': type_id, 'name': name, 'seats': seats,
                    'total': total, 'freeTables': free, 'price': price
                })
        
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'availability': availability})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================== CLOSED DATES ====================

@nightlife_bp.route('/closed_dates', methods=['POST'])
def add_closed_date():
    """Add closed date"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    data = request.get_json()
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database unavailable'}), 500
    
    try:
        cur = conn.cursor()
        
        closed_date = data.get('date')
        is_recurring = data.get('isRecurring', False)
        day_of_week = data.get('dayOfWeek')  # 0-6 for Sunday-Saturday
        reason = data.get('reason', '')
        
        cur.execute("""
            INSERT INTO nightlife_closed_dates (vendor_id, closed_date, is_recurring, day_of_week, reason)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (vendor_id, closed_date, is_recurring) DO NOTHING
        """, (vendor_id, closed_date, is_recurring, day_of_week, reason))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Closed date added'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@nightlife_bp.route('/closed_dates', methods=['GET'])
def get_closed_dates():
    """Get closed dates"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database unavailable'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, closed_date, is_recurring, day_of_week, reason 
            FROM nightlife_closed_dates WHERE vendor_id = %s ORDER BY closed_date
        """, (vendor_id,))
        rows = cur.fetchall()
        
        result = [{'id': r[0], 'date': str(r[1]), 'isRecurring': r[2], 'dayOfWeek': r[3], 'reason': r[4]} for r in rows]
        
        cur.close()
        conn.close()
        return jsonify({'success': True, 'closedDates': result})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@nightlife_bp.route('/closed_dates/<int:date_id>', methods=['DELETE'])
def delete_closed_date(date_id):
    """Delete closed date"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database unavailable'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM nightlife_closed_dates WHERE id = %s AND vendor_id = %s", (date_id, vendor_id))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True, 'message': 'Closed date removed'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================== BOOKINGS WITH OTP ====================

@nightlife_bp.route('/bookings', methods=['POST'])
def create_booking():
    """Create booking with OTP verification"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    data = request.get_json()
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database unavailable'}), 500
    
    try:
        cur = conn.cursor()
        
        # Check max bookings per user per day
        user_phone = data.get('user_phone')
        today = datetime.now().strftime('%Y-%m-%d')
        
        cur.execute("""
            SELECT COUNT(*) FROM nightlife_bookings 
            WHERE user_phone = %s AND date = %s AND created_at::date = %s
        """, (user_phone, today, today))
        
        if cur.fetchone()[0] >= MAX_BOOKINGS_PER_USER_PER_DAY:
            return jsonify({'success': False, 'message': f'Max {MAX_BOOKINGS_PER_USER_PER_DAY} bookings per day allowed'}), 400
        
        # Generate booking ID
        booking_id = generate_booking_id(vendor_id)
        
        # Generate OTP
        otp_code = generate_otp()
        otp_expires = datetime.now() + timedelta(minutes=OTP_EXPIRE_MINUTES)
        
        # Insert booking
        cur.execute("""
            INSERT INTO nightlife_bookings 
            (booking_id, vendor_id, user_name, user_email, user_phone, date, slot_id, 
             table_type_id, tables_reserved, price, status, otp_code, otp_created_at, otp_expires_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending_otp', %s, %s, %s)
            RETURNING id
        """, (booking_id, vendor_id, data.get('user_name'), data.get('user_email'),
              user_phone, data.get('date'), data.get('slot_id'), data.get('table_type_id'),
              [1], data.get('price', 0), otp_code, datetime.now(), otp_expires))
        
        booking_db_id = cur.fetchone()[0]
        
        # Log history
        log_history(booking_id, 'created', None, 'pending_otp', 'Booking created')
        
        # Log OTP
        cur.execute("""
            INSERT INTO nightlife_otp_verifications (booking_id, otp_code, user_email, user_phone, expires_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (booking_id, otp_code, data.get('user_email'), user_phone, otp_expires))
        
        conn.commit()
        
        # Send OTP email (simplified)
        send_otp_email(data.get('user_email'), otp_code, {
            'booking_id': booking_id,
            'user_name': data.get('user_name')
        })
        
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'booking': {'id': booking_db_id, 'booking_id': booking_id, 'otp_code': otp_code},
            'message': 'OTP sent to your email'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@nightlife_bp.route('/bookings/verify_otp', methods=['POST'])
def verify_otp():
    """Verify OTP and confirm booking"""
    data = request.get_json()
    booking_id = data.get('booking_id')
    otp_code = data.get('otp_code')
    
    if not booking_id or not otp_code:
        return jsonify({'success': False, 'message': 'booking_id and otp_code required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database unavailable'}), 500
    
    try:
        cur = conn.cursor()
        
        # Get booking
        cur.execute("""
            SELECT id, otp_code, otp_expires_at, status, user_name, user_email 
            FROM nightlife_bookings WHERE booking_id = %s
        """, (booking_id,))
        row = cur.fetchone()
        
        if not row:
            return jsonify({'success': False, 'message': 'Booking not found'}), 404
        
        booking_db_id, stored_otp, expires_at, status, user_name, user_email = row
        
        # Check if already verified
        if status == 'confirmed':
            return jsonify({'success': False, 'message': 'Booking already confirmed'}), 400
        
        # Check OTP expiry
        if datetime.now() > expires_at:
            # Auto-cancel expired OTP
            cur.execute("""
                UPDATE nightlife_bookings SET status = 'cancelled', updated_at = %s 
                WHERE booking_id = %s
            """, (datetime.now(), booking_id))
            log_history(booking_id, 'otp_expired', 'pending_otp', 'cancelled', 'OTP expired')
            conn.commit()
            return jsonify({'success': False, 'message': 'OTP expired. Booking cancelled.'}), 400
        
        # Verify OTP
        if stored_otp != otp_code:
            return jsonify({'success': False, 'message': 'Invalid OTP'}), 400
        
        # Update to confirmed
        cur.execute("""
            UPDATE nightlife_bookings 
            SET status = 'confirmed', otp_verified = true, updated_at = %s,
                otp_verified_at = %s
            WHERE booking_id = %s
        """, (datetime.now(), datetime.now(), booking_id))
        
        log_history(booking_id, 'otp_verified', 'pending_otp', 'confirmed', 'OTP verified successfully')
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Booking confirmed!', 'booking_id': booking_id})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@nightlife_bp.route('/bookings/resend_otp', methods=['POST'])
def resend_otp():
    """Resend OTP"""
    data = request.get_json()
    booking_id = data.get('booking_id')
    
    if not booking_id:
        return jsonify({'success': False, 'message': 'booking_id required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database unavailable'}), 500
    
    try:
        cur = conn.cursor()
        
        # Get booking
        cur.execute("SELECT id, status, user_email FROM nightlife_bookings WHERE booking_id = %s", (booking_id,))
        row = cur.fetchone()
        
        if not row:
            return jsonify({'success': False, 'message': 'Booking not found'}), 404
        
        if row[1] == 'confirmed':
            return jsonify({'success': False, 'message': 'Booking already confirmed'}), 400
        
        # Generate new OTP
        new_otp = generate_otp()
        new_expires = datetime.now() + timedelta(minutes=OTP_EXPIRE_MINUTES)
        
        cur.execute("""
            UPDATE nightlife_bookings 
            SET otp_code = %s, otp_created_at = %s, otp_expires_at = %s
            WHERE booking_id = %s
        """, (new_otp, datetime.now(), new_expires, booking_id))
        
        log_history(booking_id, 'otp_resent', row[1], row[1], 'OTP resent')
        
        conn.commit()
        
        # Send new OTP
        send_otp_email(row[2], new_otp, {'booking_id': booking_id})
        
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'OTP resent successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@nightlife_bp.route('/bookings', methods=['GET'])
def get_bookings():
    """Get all bookings"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database unavailable'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT b.id, b.booking_id, b.user_name, b.user_email, b.user_phone, b.date, 
                   b.tables_reserved, b.price, b.status, b.created_at,
                   s.name as slot_name, t.name as type_name
            FROM nightlife_bookings b
            LEFT JOIN nightlife_slots s ON b.slot_id = s.id
            LEFT JOIN nightlife_table_types t ON b.table_type_id = t.id
            WHERE b.vendor_id = %s
            ORDER BY b.created_at DESC LIMIT 100
        """, (vendor_id,))
        rows = cur.fetchall()
        
        result = []
        for r in rows:
            result.append({
                'id': r[0], 'booking_id': r[1], 'customer': r[2], 'email': r[3], 'phone': r[4],
                'date': str(r[5]), 'tables': r[6] or [], 'price': r[7], 'status': r[8],
                'createdAt': r[9].isoformat() if r[9] else '', 'slotName': r[10] or '', 'typeName': r[11] or ''
            })
        
        cur.close()
        conn.close()
        return jsonify({'success': True, 'bookings': result})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@nightlife_bp.route('/bookings/<int:booking_id>/toggle', methods=['POST'])
def toggle_booking(booking_id):
    """Toggle booking status"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database unavailable'}), 500
    
    try:
        cur = conn.cursor()
        
        cur.execute("SELECT status FROM nightlife_bookings WHERE id = %s AND vendor_id = %s", (booking_id, vendor_id))
        row = cur.fetchone()
        
        if not row:
            return jsonify({'success': False, 'message': 'Booking not found'}), 404
        
        old_status = row[0]
        new_status = 'cancelled' if old_status == 'confirmed' else 'confirmed'
        
        cur.execute("UPDATE nightlife_bookings SET status = %s, updated_at = %s WHERE id = %s", 
                   (new_status, datetime.now(), booking_id))
        
        log_history(f'BK{booking_id:04d}', 'status_changed', old_status, new_status, f'Status changed to {new_status}')
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'status': new_status})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================== ANALYTICS ====================

@nightlife_bp.route('/analytics', methods=['GET'])
def get_analytics():
    """Get analytics"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database unavailable'}), 500
    
    try:
        cur = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        month_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        # Revenue
        cur.execute("SELECT COALESCE(SUM(price), 0) FROM nightlife_bookings WHERE vendor_id = %s AND status = 'confirmed' AND date = %s", (vendor_id, today))
        today_rev = cur.fetchone()[0]
        
        cur.execute("SELECT COALESCE(SUM(price), 0) FROM nightlife_bookings WHERE vendor_id = %s AND status = 'confirmed' AND date >= %s", (vendor_id, week_ago))
        week_rev = cur.fetchone()[0]
        
        cur.execute("SELECT COALESCE(SUM(price), 0) FROM nightlife_bookings WHERE vendor_id = %s AND status = 'confirmed' AND date >= %s", (vendor_id, month_ago))
        month_rev = cur.fetchone()[0]
        
        cur.execute("SELECT COALESCE(SUM(price), 0) FROM nightlife_bookings WHERE vendor_id = %s AND status = 'confirmed'", (vendor_id,))
        total_rev = cur.fetchone()[0]
        
        # Upcoming
        cur.execute("SELECT COUNT(*) FROM nightlife_bookings WHERE vendor_id = %s AND status = 'confirmed' AND date >= %s", (vendor_id, today))
        upcoming = cur.fetchone()[0]
        
        # Chart data
        chart_data = []
        for i in range(29, -1, -1):
            day = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            cur.execute("SELECT COALESCE(SUM(price), 0) FROM nightlife_bookings WHERE vendor_id = %s AND status = 'confirmed' AND date = %s", (vendor_id, day))
            chart_data.append({'date': day, 'revenue': cur.fetchone()[0]})
        
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'analytics': {
            'todayRevenue': today_rev, 'weeklyRevenue': week_rev,
            'monthlyRevenue': month_rev, 'totalRevenue': total_rev,
            'upcomingBookings': upcoming, 'chartData': chart_data
        }})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================== SETTINGS & LOCATION ====================

@nightlife_bp.route('/settings', methods=['POST'])
def save_settings():
    """Save settings"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    data = request.get_json()
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database unavailable'}), 500
    
    try:
        cur = conn.cursor()
        
        cur.execute("SELECT id FROM nightlife_settings WHERE vendor_id = %s", (vendor_id,))
        exists = cur.fetchone()
        
        if exists:
            cur.execute("""
                UPDATE nightlife_settings SET max_advance_days = %s, cancel_before_hours = %s, require_otp = %s, updated_at = %s
                WHERE vendor_id = %s
            """, (data.get('maxAdvanceDays', 30), data.get('cancelBeforeHrs', 2), 
                  data.get('requireOtp', True), datetime.now(), vendor_id))
        else:
            cur.execute("""
                INSERT INTO nightlife_settings (vendor_id, max_advance_days, cancel_before_hours, require_otp)
                VALUES (%s, %s, %s, %s)
            """, (vendor_id, data.get('maxAdvanceDays', 30), data.get('cancelBeforeHrs', 2), data.get('requireOtp', True)))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Settings saved'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@nightlife_bp.route('/location', methods=['POST'])
def save_location():
    """Save location"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    data = request.get_json()
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database unavailable'}), 500
    
    try:
        cur = conn.cursor()
        
        cur.execute("SELECT id FROM nightlife_location WHERE vendor_id = %s", (vendor_id,))
        exists = cur.fetchone()
        
        if exists:
            cur.execute("""
                UPDATE nightlife_location SET address_line1 = %s, address_line2 = %s, city = %s, 
                state = %s, pincode = %s, updated_at = %s WHERE vendor_id = %s
            """, (data.get('addr1'), data.get('addr2'), data.get('city'), 
                  data.get('state'), data.get('pincode'), datetime.now(), vendor_id))
        else:
            cur.execute("""
                INSERT INTO nightlife_location (vendor_id, address_line1, address_line2, city, state, pincode)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (vendor_id, data.get('addr1'), data.get('addr2'), data.get('city'), 
                  data.get('state'), data.get('pincode')))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Location saved'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@nightlife_bp.route('/location/auto', methods=['POST'])
def auto_location():
    """Auto detect location"""
    vendor_id = request.args.get('vendor_id')
    data = request.get_json()
    
    lat = data.get('latitude')
    lng = data.get('longitude')
    
    if not lat or not lng:
        return jsonify({'success': False, 'message': 'latitude and longitude required'}), 400
    
    # Return mock data (in production, use Nominatim)
    return jsonify({'success': True, 'city': 'Mumbai', 'state': 'Maharashtra', 'pincode': '400001'})


# ==================== BANNER & GALLERY ====================

@nightlife_bp.route('/banner', methods=['POST'])
def upload_banner():
    """Upload banner"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    if 'banner' not in request.files:
        return jsonify({'success': False, 'message': 'No file provided'}), 400
    
    file = request.files['banner']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400
    
    # Save file (simplified - in production use proper storage)
    import os
    from werkzeug.utils import secure_filename
    
    upload_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'uploads', 'nightlife_banners')
    os.makedirs(upload_dir, exist_ok=True)
    
    ext = os.path.splitext(secure_filename(file.filename))[1]
    filename = f"banner_{vendor_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
    filepath = os.path.join(upload_dir, filename)
    file.save(filepath)
    
    banner_url = f"/uploads/nightlife_banners/{filename}"
    
    # Update vendor
    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        cur.execute("UPDATE vendors SET banner = %s WHERE id = %s", (banner_url, vendor_id))
        conn.commit()
        cur.close()
        conn.close()
    
    return jsonify({'success': True, 'bannerUrl': banner_url})


@nightlife_bp.route('/banner', methods=['DELETE'])
def delete_banner():
    """Delete banner"""
    vendor_id = request.args.get('vendor_id')
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database unavailable'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute("UPDATE vendors SET banner = NULL WHERE id = %s", (vendor_id,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True, 'message': 'Banner deleted'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================== USER FACING ====================

@nightlife_bp.route('/clubs', methods=['GET'])
def get_clubs():
    """Get all clubs"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database unavailable'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT v.id, v.name, v.banner, v.rating, l.city, l.state
            FROM vendors v
            LEFT JOIN nightlife_location l ON v.id = l.vendor_id
            WHERE v.is_active = true AND v.is_freeze = false
            ORDER BY v.name
        """)
        rows = cur.fetchall()
        
        clubs = [{'id': r[0], 'name': r[1], 'banner': r[2] or '', 'rating': float(r[3]) if r[3] else 0, 
                 'city': r[4] or '', 'state': r[5] or ''} for r in rows]
        
        cur.close()
        conn.close()
        return jsonify({'success': True, 'clubs': clubs})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@nightlife_bp.route('/clubs/<int:vendor_id>/details', methods=['GET'])
def get_club_details(vendor_id):
    """Get club details"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database unavailable'}), 500
    
    try:
        cur = conn.cursor()
        
        # Vendor
        cur.execute("""
            SELECT v.id, v.name, v.banner, v.description, v.rating, v.upi_id,
                   l.address_line1, l.city, l.state, l.pincode, s.max_advance_days
            FROM vendors v
            LEFT JOIN nightlife_location l ON v.id = l.vendor_id
            LEFT JOIN nightlife_settings s ON v.id = s.vendor_id
            WHERE v.id = %s AND v.is_active = true
        """, (vendor_id,))
        row = cur.fetchone()
        
        if not row:
            return jsonify({'success': False, 'message': 'Club not found'}), 404
        
        vendor = {
            'id': row[0], 'name': row[1], 'banner': row[2] or '', 'description': row[3] or '',
            'rating': float(row[4]) if row[4] else 0, 'upi_id': row[5] or '',
            'address': f"{row[6] or ''}", 'city': row[7] or '', 'state': row[8] or '',
            'pincode': row[9] or '', 'maxAdvanceDays': row[10] or 30
        }
        
        # Table types
        cur.execute("""
            SELECT id, name, seats, price, time_start, time_end FROM nightlife_table_types 
            WHERE vendor_id = %s AND is_active = true ORDER BY price
        """, (vendor_id,))
        type_rows = cur.fetchall()
        
        table_types = []
        for tr in type_rows:
            cur.execute("""
                SELECT COUNT(*) FROM nightlife_tables 
                WHERE vendor_id = %s AND type_id = %s AND status = 'free'
            """, (vendor_id, tr[0]))
            free = cur.fetchone()[0]
            
            table_types.append({
                'id': tr[0], 'name': tr[1], 'seats': tr[2], 'price': tr[3],
                'timeStart': tr[4], 'timeEnd': tr[5], 'freeTables': free
            })
        
        # Slots
        cur.execute("SELECT id, name, start_time, end_time FROM nightlife_slots WHERE vendor_id = %s", (vendor_id,))
        slot_rows = cur.fetchall()
        slots = [{'id': r[0], 'name': r[1], 'start': r[2], 'end': r[3]} for r in slot_rows]
        
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'vendor': vendor, 'tableTypes': table_types, 'slots': slots})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@nightlife_bp.route('/health', methods=['GET'])
def health_check():
    """Health check"""
    return jsonify({'success': True, 'message': 'Nightlife API running'})
