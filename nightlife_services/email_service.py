"""
Unified Email Service
=====================
Reusable email service for all booking modules
"""

import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from functools import wraps

# Try to import Flask-Mail if available, otherwise use SMTP directly
try:
    from flask_mail import Mail, Message
    FLASK_MAIL_AVAILABLE = True
except ImportError:
    FLASK_MAIL_AVAILABLE = False
    Mail = None

from nightlife_services.config import EMAIL_CONFIG, DATABASE_CONFIG
import psycopg2


class EmailService:
    """Unified email service for all booking systems"""
    
    def __init__(self, app=None):
        self.app = app
        self.mail = None
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app"""
        if FLASK_MAIL_AVAILABLE:
            self.mail = Mail(app)
        else:
            self.mail = None
    
    def get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(**DATABASE_CONFIG)
    
    def log_email(self, booking_id, vendor_id, email_type, recipient, subject, body, status='sent', error=None):
        """Log email to database"""
        try:
            conn = self.get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO nightlife_email_logs 
                (booking_id, vendor_id, email_type, recipient_email, subject, body, status, error_message, sent_at, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (booking_id, vendor_id, email_type, recipient, subject, body, status, error, datetime.now(), datetime.now()))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Error logging email: {e}")
    
    def send_email(self, to_email, subject, body, html_body=None, booking_id=None, vendor_id=None, email_type='general'):
        """Send email using SMTP"""
        try:
            if not EMAIL_CONFIG['MAIL_USERNAME'] or not EMAIL_CONFIG['MAIL_PASSWORD']:
                # Log as pending if no email config
                self.log_email(booking_id, vendor_id, email_type, to_email, subject, body, 'pending', 'No email credentials')
                print(f"📧 Email (simulated): {to_email} - {subject}")
                return True
            
            msg = MIMEMultipart('alternative')
            msg['From'] = EMAIL_CONFIG['MAIL_DEFAULT_SENDER']
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Attach plain text
            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)
            
            # Attach HTML if provided
            if html_body:
                html_part = MIMEText(html_body, 'html')
                msg.attach(html_part)
            
            # Send via SMTP
            server = smtplib.SMTP(EMAIL_CONFIG['MAIL_SERVER'], EMAIL_CONFIG['MAIL_PORT'])
            server.starttls()
            server.login(EMAIL_CONFIG['MAIL_USERNAME'], EMAIL_CONFIG['MAIL_PASSWORD'])
            server.send_message(msg)
            server.quit()
            
            # Log success
            self.log_email(booking_id, vendor_id, email_type, to_email, subject, body, 'sent')
            print(f"✅ Email sent to {to_email}")
            return True
            
        except Exception as e:
            # Log error
            self.log_email(booking_id, vendor_id, email_type, to_email, subject, body, 'failed', str(e))
            print(f"❌ Email failed: {e}")
            return False
    
    def send_booking_confirmation(self, booking_data):
        """Send booking confirmation email with OTP"""
        user_name = booking_data.get('user_name')
        user_email = booking_data.get('user_email')
        club_name = booking_data.get('club_name')
        booking_id = booking_data.get('booking_id')
        date = booking_data.get('date')
        slot = booking_data.get('slot')
        table_type = booking_data.get('table_type')
        price = booking_data.get('price')
        otp_code = booking_data.get('otp_code')
        vendor_id = booking_data.get('vendor_id')
        
        subject = f"Booking Confirmation – {club_name} | ZomaClone Nightlife"
        
        body = f"""Dear {user_name},

Your table booking at {club_name} has been confirmed!

Booking Details:
- Booking ID: {booking_id}
- Date: {date}
- Time Slot: {slot}
- Table Type: {table_type}
- Total Price: ₹{price}

Your OTP Code: {otp_code}

Please share this OTP with the venue to confirm your reservation.

This OTP is valid for 10 minutes.

Thank you for choosing ZomaClone!

Best regards,
ZomaClone Team
"""
        
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #8b5cf6, #ec4899); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .otp-box {{ background: #8b5cf6; color: white; padding: 20px; text-align: center; font-size: 32px; font-weight: bold; border-radius: 10px; margin: 20px 0; }}
        .details {{ background: white; padding: 20px; border-radius: 10px; margin: 20px 0; }}
        .details td {{ padding: 10px; }}
        .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎉 Booking Confirmed!</h1>
            <p>{club_name}</p>
        </div>
        <div class="content">
            <p>Dear <strong>{user_name}</strong>,</p>
            <p>Your table booking has been confirmed!</p>
            
            <div class="details">
                <table>
                    <tr><td><strong>Booking ID:</strong></td><td>{booking_id}</td></tr>
                    <tr><td><strong>Date:</strong></td><td>{date}</td></tr>
                    <tr><td><strong>Time Slot:</strong></td><td>{slot}</td></tr>
                    <tr><td><strong>Table Type:</strong></td><td>{table_type}</td></tr>
                    <tr><td><strong>Total Price:</strong></td><td>₹{price}</td></tr>
                </table>
            </div>
            
            <p>Your OTP Code:</p>
            <div class="otp-box">{otp_code}</div>
            
            <p>Please share this OTP with the venue to confirm your reservation.</p>
            <p><small>This OTP is valid for 10 minutes.</small></p>
            
            <p>Thank you for choosing ZomaClone!</p>
        </div>
        <div class="footer">
            <p>© 2026 ZomaClone. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""
        
        return self.send_email(user_email, subject, body, html_body, booking_id, vendor_id, 'booking_confirmation')
    
    def send_booking_verified(self, booking_data):
        """Send booking verified/confirmed email"""
        user_name = booking_data.get('user_name')
        user_email = booking_data.get('user_email')
        club_name = booking_data.get('club_name')
        booking_id = booking_data.get('booking_id')
        
        subject = f"✅ Booking Verified - {club_name} | ZomaClone"
        
        body = f"""Dear {user_name},

Your booking has been verified successfully!

Booking ID: {booking_id}
Club: {club_name}

Your table is reserved. See you soon!

Best regards,
ZomaClone Team
"""
        
        return self.send_email(user_email, subject, body, booking_id=booking_id, email_type='booking_verified')
    
    def send_booking_cancelled(self, booking_data):
        """Send booking cancellation email"""
        user_name = booking_data.get('user_name')
        user_email = booking_data.get('user_email')
        club_name = booking_data.get('club_name')
        booking_id = booking_data.get('booking_id')
        reason = booking_data.get('reason', 'Cancelled by user')
        
        subject = f"❌ Booking Cancelled - {booking_id} | ZomaClone"
        
        body = f"""Dear {user_name},

Your booking at {club_name} has been cancelled.

Booking ID: {booking_id}
Reason: {reason}

We hope to serve you soon!

Best regards,
ZomaClone Team
"""
        
        return self.send_email(user_email, subject, body, booking_id=booking_id, email_type='booking_cancelled')
    
    def send_vendor_notification(self, vendor_data):
        """Send notification to vendor about new booking"""
        vendor_email = vendor_data.get('vendor_email')
        vendor_name = vendor_data.get('vendor_name')
        booking_id = vendor_data.get('booking_id')
        customer_name = vendor_data.get('customer_name')
        date = vendor_data.get('date')
        slot = vendor_data.get('slot')
        table_type = vendor_data.get('table_type')
        
        subject = f"🔔 New Booking - {booking_id} | ZomaClone"
        
        body = f"""Dear {vendor_name},

You have a new table booking!

Customer: {customer_name}
Booking ID: {booking_id}
Date: {date}
Slot: {slot}
Table: {table_type}

Please verify the customer's OTP to confirm the booking.

Best regards,
ZomaClone Team
"""
        
        return self.send_email(vendor_email, subject, body, booking_id=booking_id, email_type='vendor_notification')


# Global instance
email_service = EmailService()

# Decorator for email logging
def log_email_action(action_name):
    """Decorator to log email actions"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            # Log action to database
            try:
                conn = email_service.get_db_connection()
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO nightlife_booking_history (booking_id, action, notes, created_at)
                    VALUES (%s, %s, %s, %s)
                """, (kwargs.get('booking_id'), action_name, f"Email sent: {action_name}", datetime.now()))
                conn.commit()
                cur.close()
                conn.close()
            except:
                pass
            return result
        return wrapper
    return decorator


# Convenience functions
def send_booking_email(booking_data):
    """Send booking confirmation email"""
    return email_service.send_booking_confirmation(booking_data)

def send_order_email(order_data):
    """Send order confirmation email"""
    return email_service.send_email(
        order_data.get('user_email'),
        f"Order Confirmation - {order_data.get('restaurant_name')}",
        f"Your order #{order_data.get('order_id')} has been confirmed!",
        booking_id=order_data.get('order_id'),
        email_type='order_confirmation'
    )

def send_vendor_notification_email(vendor_data):
    """Send vendor notification"""
    return email_service.send_vendor_notification(vendor_data)
