"""
Nightlife API Routes
===================
All endpoints start with /api/nightlife
Fixed: Banner URLs, OTP, Email, Availability
"""

from flask import Blueprint, request, jsonify
import sqlite3
import os
import smtplib
import random
import string
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import uuid

nightlife_bp = Blueprint('nightlife', __name__)

# Database configuration - SQLite
DB_FILE = os.path.join(os.path.dirname(__file__), '..', 'zoma.db')

# Email configuration
EMAIL_CONFIG = {
    'server': 'smtp.gmail.com',
    'port': 587,
    'username': os.environ.get('EMAIL_USER', ''),
    'password': os.environ.get('EMAIL_PASSWORD', ''),
    'use_tls': True,
    'sender': 'ZomaClone <noreply@zomaclonemail.com>'
}

def get_db_connection():
    """Get database connection"""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def generate_booking_id():
    """Generate unique booking ID: NL-20260304-0001"""
    today = datetime.now().strftime('%Y%m%d')
    conn = get_db_connection()
    if conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM nightlife_bookings 
            WHERE booking_id LIKE ?
        """, (f'NL-{today}-%',))
        count = cur.fetchone()[0] + 1
        conn.close()
        return f"NL-{today}-{count:04d}"
    return f"NL-{today}-{random.randint(1,9999):04d}"

def generate_otp():
    """Generate 6-digit OTP"""
    return ''.join([str(random.randint(0, 9)) for _ in range(6)])

def send_email(to_email, subject, body, html_body=None):
    """Send email via SMTP"""
    try:
        if not EMAIL_CONFIG['username'] or not EMAIL_CONFIG['password']:
            print(f"📧 Email (simulated): {to_email} - {subject}")
            print(f"   Body: {body[:100]}...")
            return True
        
        msg = MIMEMultipart('alternative')
        msg['From'] = EMAIL_CONFIG['sender']
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        if html_body:
            msg.attach(MIMEText(html_body, 'html'))
        
        server = smtplib.SMTP(EMAIL_CONFIG['server'], EMAIL_CONFIG['port'])
        if EMAIL_CONFIG['use_tls']:
            server.starttls()
        server.login(EMAIL_CONFIG['username'], EMAIL_CONFIG['password'])
        server.send_message(msg)
        server.quit()
        
        print(f"✅ Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False

def get_banner_url(banner_path):
    """Convert banner path to full URL"""
    if not banner_path:
        return ''
    if banner_path.startswith('http'):
        return banner_path
    # Return relative path that Flask serves
    return banner_path

# ============================================================
# VENDOR ROUTES
# ============================================================

@nightlife_bp.route('/vendor/by_email', methods=['POST'])
def get_vendor_by_email():
    """Get or create vendor by email"""
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    restaurant_name = data.get('restaurant_name', '').strip()
    
    if not email:
        return jsonify({'success': False, 'message': 'Email required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database not available'}), 500
    
    try:
        cur = conn.cursor()
        
        # Check if vendor exists
        cur.execute("SELECT id, email, name, upi_id, banner FROM vendors WHERE email = ?", (email,))
        row = cur.fetchone()
        
        if not row:
            # Create new vendor
            cur.execute("""
                INSERT INTO vendors (email, name, created_at) 
                VALUES (?, ?, ?) 
            """, (email, restaurant_name or email.split('@')[0], datetime.now().isoformat()))
            vendor_id = cur.lastrowid
            
            # Create default settings
            cur.execute("""
                INSERT INTO nightlife_settings (vendor_id, max_advance_days, cancel_before_hours)
                VALUES (?, ?, ?)
            """, (vendor_id, 365, 2))
            
            conn.commit()
            cur.execute("SELECT id, email, name, upi_id, banner FROM vendors WHERE id = ?", (vendor_id,))
            row = cur.fetchone()
        
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'vendor': {
                'id': row['id'],
                'email': row['email'],
                'name': row['name'],
                'upi_id': row['upi_id'] or '',
                'banner': get_banner_url(row['banner'])
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@nightlife_bp.route('/vendor/me', methods=['GET'])
def get_vendor_me():
    """Get current vendor info with settings, location, stats"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database not available'}), 500
    
    try:
        cur = conn.cursor()
        
        # Get vendor
        cur.execute("SELECT id, email, name, upi_id, banner FROM vendors WHERE id = ?", (vendor_id,))
        row = cur.fetchone()
        
        if not row:
            return jsonify({'success': False, 'message': 'Vendor not found'}), 404
        
        vendor = {
            'id': row['id'],
            'email': row['email'],
            'restaurant_name': row['name'],
            'upi_id': row['upi_id'] or '',
            'banner': get_banner_url(row['banner'])
        }
        
        # Get settings
        cur.execute("SELECT max_advance_days, cancel_before_hours FROM nightlife_settings WHERE vendor_id = ?", (vendor_id,))
        srow = cur.fetchone()
        settings = {
            'maxAdvanceDays': srow['max_advance_days'] if srow else 365,
            'cancelBeforeHrs': srow['cancel_before_hours'] if srow else 2
        }
        
        # Get location
        cur.execute("SELECT address_line1, address_line2, city, state, pincode FROM nightlife_location WHERE vendor_id = ?", (vendor_id,))
        lrow = cur.fetchone()
        location = {
            'addr1': lrow['address_line1'] if lrow else '',
            'addr2': lrow['address_line2'] if lrow else '',
            'city': lrow['city'] if lrow else '',
            'state': lrow['state'] if lrow else '',
            'pincode': lrow['pincode'] if lrow else ''
        } if lrow else {}
        
        # Get stats
        cur.execute("SELECT COUNT(*) FROM nightlife_table_types WHERE vendor_id = ?", (vendor_id,))
        total_types = cur.fetchone()[0] or 0
        
        cur.execute("SELECT COALESCE(SUM(total), 0) FROM nightlife_table_types WHERE vendor_id = ?", (vendor_id,))
        total_tables = cur.fetchone()[0] or 0
        
        cur.execute("SELECT COUNT(*) FROM nightlife_bookings WHERE vendor_id = ?", (vendor_id,))
        total_bookings = cur.fetchone()[0] or 0
        
        cur.execute("""
            SELECT COUNT(*) FROM nightlife_bookings 
            WHERE vendor_id = ? AND status = 'confirmed' AND date >= ?
        """, (vendor_id, datetime.now().strftime('%Y-%m-%d')))
        upcoming_bookings = cur.fetchone()[0] or 0
        
        stats = {
            'totalTypes': total_types,
            'totalTables': total_tables,
            'totalBookings': total_bookings,
            'upcomingBookings': upcoming_bookings
        }
        
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'vendor': vendor,
            'settings': settings,
            'location': location,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@nightlife_bp.route('/vendor/<int:vid>/upi', methods=['PUT'])
def update_vendor_upi(vid):
    """Update vendor UPI ID"""
    data = request.get_json()
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database not available'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute("UPDATE vendors SET upi_id = ? WHERE id = ?", (data.get('upi_id', ''), vid))
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'UPI updated'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ============================================================
# TABLE TYPES ROUTES
# ============================================================

@nightlife_bp.route('/types', methods=['POST'])
def create_table_type():
    """Create or update table type"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    data = request.get_json()
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database not available'}), 500
    
    try:
        cur = conn.cursor()
        
        type_id = data.get('id')
        if type_id:
            cur.execute("""
                UPDATE nightlife_table_types 
                SET name = ?, seats = ?, total = ?, price = ?, 
                    cancel_hours = ?, time_start = ?, time_end = ?
                WHERE id = ? AND vendor_id = ?
            """, (
                data.get('name'),
                data.get('seats', 2),
                data.get('total', 1),
                data.get('price', 0),
                data.get('cancel', 2),
                data.get('timeStart', '18:00'),
                data.get('timeEnd', '23:00'),
                type_id,
                vendor_id
            ))
        else:
            cur.execute("""
                INSERT INTO nightlife_table_types 
                (vendor_id, name, seats, total, price, cancel_hours, time_start, time_end)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                vendor_id,
                data.get('name'),
                data.get('seats', 2),
                data.get('total', 1),
                data.get('price', 0),
                data.get('cancel', 2),
                data.get('timeStart', '18:00'),
                data.get('timeEnd', '23:00')
            ))
            type_id = cur.lastrowid
        
        # Create/update tables
        free_tables = data.get('freeTables', data.get('total', 1))
        
        cur.execute("SELECT COUNT(*) FROM nightlife_tables WHERE vendor_id = ? AND type_id = ?", 
                   (vendor_id, type_id))
        existing_count = cur.fetchone()[0]
        
        if existing_count < data.get('total', 1):
            for i in range(existing_count + 1, data.get('total', 1) + 1):
                status = 'free' if i <= free_tables else 'reserved'
                cur.execute("""
                    INSERT INTO nightlife_tables (vendor_id, type_id, table_number, status)
                    VALUES (?, ?, ?, ?)
                """, (vendor_id, type_id, i, status))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'type': {'id': type_id, 'name': data.get('name')}})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@nightlife_bp.route('/types', methods=['GET'])
def get_table_types():
    """Get all table types for vendor"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database not available'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, name, seats, total, price, cancel_hours, time_start, time_end
            FROM nightlife_table_types 
            WHERE vendor_id = ?
            ORDER BY name
        """, (vendor_id,))
        rows = cur.fetchall()
        
        result = []
        for row in rows:
            cur.execute("""
                SELECT status, COUNT(*) FROM nightlife_tables 
                WHERE vendor_id = ? AND type_id = ?
                GROUP BY status
            """, (vendor_id, row['id']))
            status_counts = cur.fetchall()
            
            free_count = 0
            reserved_count = 0
            for s in status_counts:
                if s[0] == 'free':
                    free_count = s[1]
                elif s[0] == 'reserved':
                    reserved_count = s[1]
            
            result.append({
                'id': row['id'],
                'name': row['name'],
                'seats': row['seats'],
                'total': row['total'],
                'freeCount': free_count,
                'reservedCount': reserved_count,
                'price': row['price'],
                'cancel': row['cancel_hours'],
                'timeStart': row['time_start'],
                'timeEnd': row['time_end'],
                'displayTime': f"{row['time_start']} - {row['time_end']}"
            })
        
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'types': result})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@nightlife_bp.route('/types/<int:type_id>', methods=['DELETE'])
def delete_table_type(type_id):
    """Delete table type"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database not available'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM nightlife_table_types WHERE id = ? AND vendor_id = ?", (type_id, vendor_id))
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Type deleted'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@nightlife_bp.route('/types/<int:type_id>/tables', methods=['GET'])
def get_tables_for_type(type_id):
    """Get all tables for a specific type"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database not available'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, table_number, status
            FROM nightlife_tables 
            WHERE vendor_id = ? AND type_id = ?
            ORDER BY table_number
        """, (vendor_id, type_id))
        rows = cur.fetchall()
        
        result = [{
            'id': row['id'],
            'num': row['table_number'],
            'status': row['status']
        } for row in rows]
        
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'tables': result})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@nightlife_bp.route('/tables/<int:table_id>/toggle', methods=['POST'])
def toggle_table_status(table_id):
    """Toggle table status between free and unavailable"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database not available'}), 500
    
    try:
        cur = conn.cursor()
        
        cur.execute("SELECT status FROM nightlife_tables WHERE id = ? AND vendor_id = ?", 
                   (table_id, vendor_id))
        row = cur.fetchone()
        
        if not row:
            return jsonify({'success': False, 'message': 'Table not found'}), 404
        
        if row['status'] == 'reserved':
            return jsonify({'success': False, 'message': 'Cannot change reserved table'}), 400
        
        new_status = 'unavailable' if row['status'] == 'free' else 'free'
        cur.execute("UPDATE nightlife_tables SET status = ? WHERE id = ?", (new_status, table_id))
        conn.commit()
        
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'status': new_status})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@nightlife_bp.route('/tables/mark_all_free', methods=['POST'])
def mark_all_tables_free():
    """Mark all tables of a type as free"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    data = request.get_json()
    type_id = data.get('typeId')
    
    if not type_id:
        return jsonify({'success': False, 'message': 'typeId required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database not available'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute("""
            UPDATE nightlife_tables 
            SET status = 'free' 
            WHERE vendor_id = ? AND type_id = ? AND status != 'reserved'
        """, (vendor_id, type_id))
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'All tables marked as free'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ============================================================
# SLOTS ROUTES
# ============================================================

@nightlife_bp.route('/slots', methods=['POST'])
def create_slot():
    """Create or update slot"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    data = request.get_json()
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database not available'}), 500
    
    try:
        cur = conn.cursor()
        
        slot_id = data.get('id')
        if slot_id:
            cur.execute("""
                UPDATE nightlife_slots 
                SET name = ?, start_time = ?, end_time = ?
                WHERE id = ? AND vendor_id = ?
            """, (data.get('name'), data.get('start'), data.get('end'), slot_id, vendor_id))
        else:
            cur.execute("""
                INSERT INTO nightlife_slots (vendor_id, name, start_time, end_time)
                VALUES (?, ?, ?, ?)
            """, (vendor_id, data.get('name'), data.get('start'), data.get('end')))
            slot_id = cur.lastrowid
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'slot': {
            'id': slot_id,
            'name': data.get('name'),
            'start': data.get('start'),
            'end': data.get('end')
        }})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@nightlife_bp.route('/slots', methods=['GET'])
def get_slots():
    """Get all slots for vendor"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database not available'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, name, start_time, end_time
            FROM nightlife_slots 
            WHERE vendor_id = ?
            ORDER BY start_time
        """, (vendor_id,))
        rows = cur.fetchall()
        
        result = [{
            'id': row['id'],
            'name': row['name'],
            'start': row['start_time'],
            'end': row['end_time']
        } for row in rows]
        
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
        return jsonify({'success': False, 'message': 'Database not available'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM nightlife_slots WHERE id = ? AND vendor_id = ?", (slot_id, vendor_id))
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Slot deleted'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ============================================================
# BOOKINGS WITH OTP
# ============================================================

@nightlife_bp.route('/bookings', methods=['POST'])
def create_booking():
    """Create a new booking with OTP"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    data = request.get_json()
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database not available'}), 500
    
    try:
        booking_id = generate_booking_id()
        otp_code = generate_otp()
        otp_expiry = (datetime.now() + timedelta(minutes=10)).isoformat()
        
        cur = conn.cursor()
        
        # Get vendor name for email
        cur.execute("SELECT name FROM vendors WHERE id = ?", (vendor_id,))
        vendor_row = cur.fetchone()
        club_name = vendor_row['name'] if vendor_row else 'Nightlife Club'
        
        # Insert booking with PENDING status and OTP
        cur.execute("""
            INSERT INTO nightlife_bookings 
            (booking_id, vendor_id, customer, phone, date, slot_id, table_type_id, table_numbers, price, status, otp_code, otp_expiry)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?, ?)
        """, (
            booking_id,
            vendor_id,
            data.get('customer', ''),
            data.get('phone', ''),
            data.get('date', ''),
            data.get('slot_id'),
            data.get('table_type_id'),
            data.get('table_numbers', ''),
            data.get('price', 0),
            otp_code,
            otp_expiry
        ))
        
        db_booking_id = cur.lastrowid
        
        # Reserve tables
        if data.get('table_numbers') and data.get('table_type_id'):
            table_nums = [x.strip() for x in data.get('table_numbers').split(',') if x.strip()]
            for tn in table_nums:
                try:
                    cur.execute("""
                        UPDATE nightlife_tables 
                        SET status = 'reserved' 
                        WHERE vendor_id = ? AND type_id = ? AND table_number = ?
                    """, (vendor_id, data.get('table_type_id'), int(tn)))
                except:
                    pass
        
        conn.commit()
        
        # Send OTP email
        user_email = data.get('email', '')
        if user_email:
            subject = f"Booking Confirmation - {club_name} | ZomaClone"
            body = f"""Dear {data.get('customer')},

Your table booking at {club_name} has been initiated!

Booking ID: {booking_id}
Date: {data.get('date')}
Tables: {data.get('table_numbers')}
Price: ₹{data.get('price', 0)}

Your OTP Code: {otp_code}

Please verify your booking with this OTP.

This OTP is valid for 10 minutes.

Thank you for choosing ZomaClone!
"""
            html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; padding: 20px;">
    <h2 style="color: #8b5cf6;">🎉 Booking Confirmation</h2>
    <p>Dear <strong>{data.get('customer')}</strong>,</p>
    <p>Your table booking at <strong>{club_name}</strong> has been initiated!</p>
    <div style="background: #f3f4f6; padding: 15px; border-radius: 8px; margin: 15px 0;">
        <p><strong>Booking ID:</strong> {booking_id}</p>
        <p><strong>Date:</strong> {data.get('date')}</p>
        <p><strong>Tables:</strong> {data.get('table_numbers')}</p>
        <p><strong>Price:</strong> ₹{data.get('price', 0)}</p>
    </div>
    <div style="background: #8b5cf6; color: white; padding: 20px; text-align: center; border-radius: 8px; margin: 20px 0;">
        <p style="font-size: 24px; margin: 0;">Your OTP: <strong>{otp_code}</strong></p>
    </div>
    <p>Please verify your booking with this OTP.</p>
    <p><small>This OTP is valid for 10 minutes.</small></p>
    <p>Thank you for choosing ZomaClone!</p>
</body>
</html>
"""
            send_email(user_email, subject, body, html_body)
        
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'booking': {
            'id': db_booking_id,
            'booking_id': booking_id,
            'otp_code': otp_code,
            'message': 'OTP sent to your email'
        }})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@nightlife_bp.route('/bookings/verify', methods=['POST'])
def verify_booking_otp():
    """Verify OTP and confirm booking"""
    data = request.get_json()
    booking_id = data.get('booking_id')
    otp_code = data.get('otp_code')
    
    if not booking_id or not otp_code:
        return jsonify({'success': False, 'message': 'booking_id and otp_code required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database not available'}), 500
    
    try:
        cur = conn.cursor()
        
        # Get booking
        cur.execute("""
            SELECT id, otp_code, otp_expiry, status, customer 
            FROM nightlife_bookings WHERE booking_id = ?
        """, (booking_id,))
        row = cur.fetchone()
        
        if not row:
            return jsonify({'success': False, 'message': 'Booking not found'}), 404
        
        # Check if already confirmed
        if row['status'] == 'confirmed':
            return jsonify({'success': False, 'message': 'Booking already confirmed'}), 400
        
        # Check OTP expiry
        if row['otp_expiry']:
            expiry = datetime.fromisoformat(row['otp_expiry'])
            if datetime.now() > expiry:
                cur.execute("UPDATE nightlife_bookings SET status = 'cancelled' WHERE booking_id = ?", (booking_id,))
                conn.commit()
                return jsonify({'success': False, 'message': 'OTP expired. Booking cancelled.'}), 400
        
        # Verify OTP
        if row['otp_code'] != otp_code:
            return jsonify({'success': False, 'message': 'Invalid OTP'}), 400
        
        # Confirm booking
        cur.execute("UPDATE nightlife_bookings SET status = 'confirmed' WHERE booking_id = ?", (booking_id,))
        conn.commit()
        
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Booking confirmed!', 'booking_id': booking_id})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@nightlife_bp.route('/bookings', methods=['GET'])
def get_bookings():
    """Get all bookings for vendor"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database not available'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT b.id, b.booking_id, b.customer, b.phone, b.date, b.table_numbers, 
                   b.price, b.status, b.created_at, b.otp_code,
                   s.name as slot_name, t.name as type_name
            FROM nightlife_bookings b
            LEFT JOIN nightlife_slots s ON b.slot_id = s.id
            LEFT JOIN nightlife_table_types t ON b.table_type_id = t.id
            WHERE b.vendor_id = ?
            ORDER BY b.date DESC, b.created_at DESC
            LIMIT 100
        """, (vendor_id,))
        rows = cur.fetchall()
        
        result = []
        for row in rows:
            result.append({
                'id': row['id'],
                'booking_id': row['booking_id'],
                'customer': row['customer'],
                'phone': row['phone'],
                'date': str(row['date']) if row['date'] else '',
                'tables': row['table_numbers'].split(',') if row['table_numbers'] else [],
                'price': row['price'],
                'status': row['status'],
                'otp': row['otp_code'] if row['status'] == 'PENDING' else '',
                'createdAt': row['created_at'].isoformat() if row['created_at'] else '',
                'slotName': row['slot_name'] if row['slot_name'] else '',
                'typeName': row['type_name'] if row['type_name'] else ''
            })
        
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'bookings': result})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@nightlife_bp.route('/bookings/<int:booking_id>/toggle', methods=['POST'])
def toggle_booking_status(booking_id):
    """Toggle booking status between confirmed and cancelled"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database not available'}), 500
    
    try:
        cur = conn.cursor()
        
        cur.execute("""
            SELECT status, table_numbers, table_type_id 
            FROM nightlife_bookings 
            WHERE id = ? AND vendor_id = ?
        """, (booking_id, vendor_id))
        row = cur.fetchone()
        
        if not row:
            return jsonify({'success': False, 'message': 'Booking not found'}), 404
        
        current_status = row['status']
        new_status = 'cancelled' if current_status == 'confirmed' else 'confirmed'
        
        cur.execute("UPDATE nightlife_bookings SET status = ? WHERE id = ? AND vendor_id = ?",
                   (new_status, booking_id, vendor_id))
        
        # Free/reserve tables
        if row['table_numbers'] and row['table_type_id']:
            table_nums = [x.strip() for x in row['table_numbers'].split(',') if x.strip()]
            new_table_status = 'free' if new_status == 'cancelled' else 'reserved'
            for tn in table_nums:
                try:
                    cur.execute("""
                        UPDATE nightlife_tables 
                        SET status = ? 
                        WHERE vendor_id = ? AND type_id = ? AND table_number = ?
                    """, (new_table_status, vendor_id, row['table_type_id'], int(tn)))
                except:
                    pass
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'status': new_status})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ============================================================
# SETTINGS & LOCATION
# ============================================================

@nightlife_bp.route('/settings', methods=['POST'])
def save_settings():
    """Save vendor settings"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    data = request.get_json()
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database not available'}), 500
    
    try:
        cur = conn.cursor()
        
        cur.execute("SELECT id FROM nightlife_settings WHERE vendor_id = ?", (vendor_id,))
        exists = cur.fetchone()
        
        if exists:
            cur.execute("""
                UPDATE nightlife_settings 
                SET max_advance_days = ?, cancel_before_hours = ?
                WHERE vendor_id = ?
            """, (data.get('maxAdvanceDays', 365), data.get('cancelBeforeHrs', 2), vendor_id))
        else:
            cur.execute("""
                INSERT INTO nightlife_settings (vendor_id, max_advance_days, cancel_before_hours)
                VALUES (?, ?, ?)
            """, (vendor_id, data.get('maxAdvanceDays', 365), data.get('cancelBeforeHrs', 2)))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Settings saved'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@nightlife_bp.route('/location/auto', methods=['POST'])
def auto_location():
    """Auto detect location"""
    vendor_id = request.args.get('vendor_id')
    data = request.get_json()
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    
    if not latitude or not longitude:
        return jsonify({'success': False, 'message': 'Latitude and longitude required'}), 400
    
    try:
        import requests
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {'lat': latitude, 'lon': longitude, 'format': 'json', 'addressdetails': 1}
        headers = {'User-Agent': 'ZomaClone/1.0'}
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            address = result.get('address', {})
            city = address.get('city') or address.get('town') or address.get('village') or ''
            state = address.get('state') or ''
            pincode = address.get('postcode') or ''
            
            return jsonify({'success': True, 'city': city, 'state': state, 'pincode': pincode})
    except Exception as e:
        pass
    
    return jsonify({'success': True, 'city': 'Mumbai', 'state': 'Maharashtra', 'pincode': '400001'})

@nightlife_bp.route('/location', methods=['POST'])
def save_location():
    """Save vendor location"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    data = request.get_json()
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database not available'}), 500
    
    try:
        cur = conn.cursor()
        
        cur.execute("SELECT id FROM nightlife_location WHERE vendor_id = ?", (vendor_id,))
        exists = cur.fetchone()
        
        if exists:
            cur.execute("""
                UPDATE nightlife_location 
                SET address_line1 = ?, address_line2 = ?, city = ?, state = ?, pincode = ?
                WHERE vendor_id = ?
            """, (data.get('addr1', ''), data.get('addr2', ''), data.get('city', ''),
                  data.get('state', ''), data.get('pincode', ''), vendor_id))
        else:
            cur.execute("""
                INSERT INTO nightlife_location (vendor_id, address_line1, address_line2, city, state, pincode)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (vendor_id, data.get('addr1', ''), data.get('addr2', ''), data.get('city', ''),
                  data.get('state', ''), data.get('pincode', '')))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Location saved'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ============================================================
# BANNER & GALLERY
# ============================================================

@nightlife_bp.route('/banner', methods=['POST'])
def upload_banner():
    """Upload vendor banner"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    if 'banner' not in request.files:
        return jsonify({'success': False, 'message': 'No file provided'}), 400
    
    file = request.files['banner']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400
    
    import os
    from werkzeug.utils import secure_filename
    
    upload_dir = os.path.join(os.path.dirname(__file__), '..', 'uploads', 'nightlife_banners')
    os.makedirs(upload_dir, exist_ok=True)
    
    ext = os.path.splitext(secure_filename(file.filename))[1]
    filename = f"banner_{vendor_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
    filepath = os.path.join(upload_dir, filename)
    
    file.save(filepath)
    
    # Store relative path
    banner_path = f"/uploads/nightlife_banners/{filename}"
    
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("UPDATE vendors SET banner = ? WHERE id = ?", (banner_path, vendor_id))
            conn.commit()
            cur.close()
            conn.close()
        except:
            pass
    
    return jsonify({
        'success': True,
        'bannerUrl': banner_path,
        'message': 'Banner uploaded'
    })

@nightlife_bp.route('/banner', methods=['DELETE'])
def delete_banner():
    """Delete vendor banner"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database not available'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute("UPDATE vendors SET banner = NULL WHERE id = ?", (vendor_id,))
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Banner deleted'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@nightlife_bp.route('/gallery', methods=['POST'])
def upload_gallery():
    """Upload gallery images"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    if 'images' not in request.files:
        return jsonify({'success': False, 'message': 'No files provided'}), 400
    
    files = request.files.getlist('images')
    
    import os
    from werkzeug.utils import secure_filename
    
    upload_dir = os.path.join(os.path.dirname(__file__), '..', 'uploads', 'nightlife_gallery')
    os.makedirs(upload_dir, exist_ok=True)
    
    uploaded = []
    for file in files:
        if file.filename == '':
            continue
        ext = os.path.splitext(secure_filename(file.filename))[1]
        filename = f"gallery_{vendor_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(uploaded)}{ext}"
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)
        uploaded.append(f"/uploads/nightlife_gallery/{filename}")
    
    return jsonify({'success': True, 'images': uploaded, 'message': f'{len(uploaded)} images uploaded'})

@nightlife_bp.route('/gallery', methods=['GET'])
def get_gallery():
    """Get gallery images"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    return jsonify({'success': True, 'images': []})

# ============================================================
# USER FACING - CLUBS & AVAILABILITY
# ============================================================

@nightlife_bp.route('/clubs', methods=['GET'])
def get_all_clubs():
    """Get all clubs for user view"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database not available'}), 500
    
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT v.id, v.name, v.banner, l.city, l.state
            FROM vendors v
            LEFT JOIN nightlife_location l ON v.id = l.vendor_id
            WHERE v.name IS NOT NULL AND v.name != ''
            ORDER BY v.name
        """)
        rows = cur.fetchall()
        
        clubs = [{
            'id': row['id'],
            'name': row['name'],
            'banner': get_banner_url(row['banner']),
            'city': row['city'] or '',
            'state': row['state'] or ''
        } for row in rows]
        
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'clubs': clubs})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@nightlife_bp.route('/clubs/<int:vendor_id>/details', methods=['GET'])
def get_club_details(vendor_id):
    """Get detailed club info"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database not available'}), 500
    
    try:
        cur = conn.cursor()
        
        cur.execute("""
            SELECT v.id, v.name, v.banner, v.upi_id,
                   l.address_line1, l.city, l.state, l.pincode,
                   s.max_advance_days
            FROM vendors v
            LEFT JOIN nightlife_location l ON v.id = l.vendor_id
            LEFT JOIN nightlife_settings s ON v.id = s.vendor_id
            WHERE v.id = ?
        """, (vendor_id,))
        row = cur.fetchone()
        
        if not row:
            return jsonify({'success': False, 'message': 'Club not found'}), 404
        
        vendor = {
            'id': row['id'],
            'name': row['name'],
            'banner': get_banner_url(row['banner']),
            'upi_id': row['upi_id'] or '',
            'address': f"{row['address_line1'] or ''}".strip(', '),
            'city': row['city'] or '',
            'state': row['state'] or '',
            'pincode': row['pincode'] or '',
            'maxAdvanceDays': row['max_advance_days'] or 30
        }
        
        # Table types with availability
        cur.execute("""
            SELECT id, name, seats, price, time_start, time_end
            FROM nightlife_table_types WHERE vendor_id = ? ORDER BY price
        """, (vendor_id,))
        type_rows = cur.fetchall()
        
        table_types = []
        for tr in type_rows:
            cur.execute("""
                SELECT COUNT(*) FROM nightlife_tables 
                WHERE vendor_id = ? AND type_id = ? AND status = 'free'
            """, (vendor_id, tr['id']))
            free_count = cur.fetchone()[0] or 0
            
            table_types.append({
                'id': tr['id'],
                'name': tr['name'],
                'seats': tr['seats'],
                'price': tr['price'],
                'timeStart': tr['time_start'],
                'timeEnd': tr['time_end'],
                'freeTables': free_count
            })
        
        # Slots
        cur.execute("SELECT id, name, start_time, end_time FROM nightlife_slots WHERE vendor_id = ? ORDER BY start_time", (vendor_id,))
        slots = [{'id': r['id'], 'name': r['name'], 'start': r['start_time'], 'end': r['end_time']} for r in cur.fetchall()]
        
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'vendor': vendor, 'tableTypes': table_types, 'slots': slots})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@nightlife_bp.route('/clubs/<int:vendor_id>/availability', methods=['GET'])
def get_table_availability(vendor_id):
    """Get available tables for date/slot"""
    date = request.args.get('date')
    slot_id = request.args.get('slot_id')
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database not available'}), 500
    
    try:
        cur = conn.cursor()
        
        # Get table types with dynamic availability
        cur.execute("""
            SELECT t.id, t.name, t.seats, t.price, t.total,
                   (SELECT COUNT(*) FROM nightlife_tables 
                    WHERE vendor_id = ? AND type_id = t.id AND status = 'free') as free_count
            FROM nightlife_table_types t
            WHERE t.vendor_id = ?
            ORDER BY t.price
        """, (vendor_id, vendor_id))
        rows = cur.fetchall()
        
        availability = []
        for row in rows:
            if row['free_count'] > 0:
                # Get available table numbers
                cur.execute("""
                    SELECT table_number FROM nightlife_tables 
                    WHERE vendor_id = ? AND type_id = ? AND status = 'free'
                    ORDER BY table_number
                """, (vendor_id, row['id']))
                table_nums = [r[0] for r in cur.fetchall()]
                
                availability.append({
                    'id': row['id'],
                    'name': row['name'],
                    'seats': row['seats'],
                    'price': row['price'],
                    'freeTables': row['free_count'],
                    'availableTables': table_nums
                })
        
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'availability': availability})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ============================================================
# ANALYTICS
# ============================================================

@nightlife_bp.route('/analytics', methods=['GET'])
def get_analytics():
    """Get vendor analytics"""
    vendor_id = request.args.get('vendor_id')
    if not vendor_id:
        return jsonify({'success': False, 'message': 'vendor_id required'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database not available'}), 500
    
    try:
        cur = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        month_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        # Revenue calculations
        cur.execute("""
            SELECT COALESCE(SUM(price), 0) FROM nightlife_bookings 
            WHERE vendor_id = ? AND status = 'confirmed' AND date = ?
        """, (vendor_id, today))
        today_revenue = cur.fetchone()[0] or 0
        
        cur.execute("""
            SELECT COALESCE(SUM(price), 0) FROM nightlife_bookings 
            WHERE vendor_id = ? AND status = 'confirmed' AND date >= ?
        """, (vendor_id, week_ago))
        weekly_revenue = cur.fetchone()[0] or 0
        
        cur.execute("""
            SELECT COALESCE(SUM(price), 0) FROM nightlife_bookings 
            WHERE vendor_id = ? AND status = 'confirmed' AND date >= ?
        """, (vendor_id, month_ago))
        monthly_revenue = cur.fetchone()[0] or 0
        
        cur.execute("""
            SELECT COALESCE(SUM(price), 0) FROM nightlife_bookings 
            WHERE vendor_id = ? AND status = 'confirmed'
        """, (vendor_id,))
        total_revenue = cur.fetchone()[0] or 0
        
        cur.execute("""
            SELECT COUNT(*) FROM nightlife_bookings 
            WHERE vendor_id = ? AND status = 'confirmed' AND date >= ?
        """, (vendor_id, today))
        upcoming_bookings = cur.fetchone()[0] or 0
        
        # Chart data
        chart_data = []
        for i in range(29, -1, -1):
            day = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            cur.execute("""
                SELECT COALESCE(SUM(price), 0) FROM nightlife_bookings 
                WHERE vendor_id = ? AND status = 'confirmed' AND date = ?
            """, (vendor_id, day))
            revenue = cur.fetchone()[0] or 0
            chart_data.append({'date': day, 'revenue': revenue})
        
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'analytics': {
            'todayRevenue': today_revenue,
            'weeklyRevenue': weekly_revenue,
            'monthlyRevenue': monthly_revenue,
            'totalRevenue': total_revenue,
            'upcomingBookings': upcoming_bookings,
            'chartData': chart_data
        }})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ============================================================
# HEALTH CHECK
# ============================================================

@nightlife_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({'success': True, 'message': 'Nightlife API is running'})
