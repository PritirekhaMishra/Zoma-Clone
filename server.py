from flask import make_response
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.utils import secure_filename
from sqlalchemy import or_
import os
import random
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import json
# -------------------------------
# Optional: Razorpay
# -------------------------------
try:
    import razorpay
except ImportError:
    razorpay = None

# ===========================
# FLASK APP
# ===========================


app = Flask(__name__)
from flask_cors import CORS

CORS(app,
     resources={r"/*": {"origins": ["http://127.0.0.1:5500", "http://localhost:5500"]}},
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])




# DATABASE
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql+psycopg2://neondb_owner:npg_bjNrH7GPR3vK@ep-wispy-meadow-agg97aix.c-2.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

print("Database in use =", app.config['SQLALCHEMY_DATABASE_URI'])


app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 180,
    "pool_size": 5,
    "max_overflow": 10
}
db = SQLAlchemy(app)

# ===========================
# STATIC ROUTE FOR DASHBOARD
# ===========================
@app.route("/vendor_dashboard")
def vendor_dashboard():
    # Make sure vendor_order_online.html is in same folder as server.py
    return send_from_directory(".", "vendor_order_online.html")
app.config["SECRET_KEY"] = "your_super_secret_key_here"



# =====================================================
#                EMAIL CONFIG (GMAIL)
# =====================================================
# =============================
#  BREVO SMTP CONFIG (FINAL)
# =============================
# ================================
#  BREVO SMTP CONFIG (FIXED)
# ================================
SMTP_FROM = "pritirekha7978@gmail.com"
SMTP_USER = "9c768f001@smtp-brevo.com"
SMTP_PASSWORD = "bskMS8EZEePdAO2"
SMTP_HOST = "smtp-relay.brevo.com"
SMTP_PORT = 587

def send_email(to_email: str, subject: str, body: str) -> bool:
    if not to_email:
        return False

    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = SMTP_FROM
        msg["To"] = to_email

        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_FROM, [to_email], msg.as_string())
        server.quit()

        print(f"[EMAIL SENT] -> {to_email}")
        return True

    except Exception as e:
        print("EMAIL ERROR:", e)
        return False


# =====================================================
#                SMS CONFIG (PLACEHOLDER)
# =====================================================

def send_sms(phone: str, code: str) -> bool:
    """
    Integrate Fast2SMS / MSG91 / Twilio later.
    For now, just prints OTP.
    """
    if not phone:
        return False
    print(f"[SMS SENT] To {phone}: OTP = {code}")
    return True


# =====================================================
#           FILE UPLOAD CONFIG (PRODUCT / CLUB IMAGES)
# =====================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

ALLOWED_EXT = {"jpg", "jpeg", "png", "webp", "jfif"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


def get_data():
    """
    Helper: get JSON or form data as dict.
    """
    data = request.get_json(silent=True)
    if not data:
        data = request.form.to_dict()
    return data or {}



# =====================================================
#                      MODELS
# =====================================================
class Orders(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)

    restaurant_id = db.Column(db.Integer, nullable=False)
    restaurant_name = db.Column(db.String(200), nullable=False)

    vendor_id = db.Column(db.Integer, nullable=False)

    items = db.Column(db.Text, nullable=False)       # stored as JSON string
    address = db.Column(db.Text, nullable=False)     # stored as JSON string

    total = db.Column(db.Integer, nullable=False)
    coupon_discount = db.Column(db.Integer, default=0)

    payment_method = db.Column(db.String(20), nullable=False) # COD / ONLINE
    payment_status = db.Column(db.String(20), nullable=False)  # PENDING / PAID
    upi_reference_id = db.Column(db.String(50), nullable=True)

    status = db.Column(db.String(30), default="PENDING")       # order flow

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class OTPLog(db.Model):
    __tablename__ = "otp_logs"
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(30), nullable=False)
    purpose = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(150))
    phone = db.Column(db.String(20))
    code = db.Column(db.String(10), nullable=False)
    attempts = db.Column(db.Integer, default=0)
    is_verified = db.Column(db.Boolean, default=False)
    blocked_until = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)


# --------------------- USERS --------------------------

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class UserSession(db.Model):
    __tablename__ = "user_sessions"

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    token      = db.Column(db.String(128), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)


# --------------------- VENDOR -------------------------

class Vendor(db.Model):
    __tablename__ = "vendors"
    id = db.Column(db.Integer, primary_key=True)
    restaurant_name = db.Column(db.String(200), nullable=False)
    owner_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    address = db.Column(db.String(300), nullable=False)
    password = db.Column(db.String(150))
    upi_id = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# --------------------- CLUBS --------------------------

class Club(db.Model):
    __tablename__ = "clubs"
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, nullable=False)
    club_name = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    music = db.Column(db.String(100))
    dress = db.Column(db.String(100))
    description = db.Column(db.String(2000))
    main_image = db.Column(db.String(300))


@app.route("/vendor/updateClub/<int:club_id>", methods=["PUT", "POST"])
def update_club(club_id):
    data = get_data()
    c = Club.query.get_or_404(club_id)

    if "club_name" in data:
        c.club_name = (data.get("club_name") or c.club_name).strip()
    if "location" in data:
        c.location = (data.get("location") or c.location).strip()
    if "music" in data:
        c.music = (data.get("music") or "").strip()
    if "dress" in data:
        c.dress = (data.get("dress") or "").strip()
    if "description" in data:
        c.description = (data.get("description") or "").strip()

    db.session.commit()
    return jsonify({"ok": True, "message": "Club updated"})


class ClubImage(db.Model):
    __tablename__ = "club_images"
    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, nullable=False)
    image_url = db.Column(db.String(300), nullable=False)


# --------------------- NIGHTLIFE MENU -----------------

class NightlifeMenuItem(db.Model):
    __tablename__ = "nightlife_menu_items"
    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(100))
    food_type = db.Column(db.String(20))       # Veg / Non-Veg (optional)
    available = db.Column(db.Boolean, default=True)
    image_url = db.Column(db.String(300))
    description = db.Column(db.String(1000))

# =====================================================
#      TABLE-BOOKING VENDOR PANEL MODELS (/api/rest)
# =====================================================

class RestVendorConfig(db.Model):
    """
    Extra config for the table-booking dashboard:
    - settings (maxAdvanceDays, cancelBeforeHrs)
    - location
    - banner image
    """
    __tablename__ = "rest_vendor_configs"

    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, nullable=False, unique=True)

    # settings
    max_advance_days = db.Column(db.Integer, default=365)
    cancel_before_hrs = db.Column(db.Integer, default=2)

    # location
    addr1 = db.Column(db.String(200))
    addr2 = db.Column(db.String(200))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    pincode = db.Column(db.String(20))

    # banner
    banner_url = db.Column(db.String(300))

    def as_settings(self):
        return {
            "maxAdvanceDays": self.max_advance_days or 365,
            "cancelBeforeHrs": self.cancel_before_hrs or 2,
        }

    def as_location(self):
        return {
            "addr1": self.addr1 or "",
            "addr2": self.addr2 or "",
            "city": self.city or "",
            "state": self.state or "",
            "pincode": self.pincode or "",
        }


class RestSlot(db.Model):
    __tablename__ = "rest_slots"
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    start = db.Column(db.String(5), nullable=False)  # "HH:MM"
    end = db.Column(db.String(5), nullable=False)    # "HH:MM"


class RestTableType(db.Model):
    __tablename__ = "rest_table_types"
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    seats = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Integer, default=0)
    price = db.Column(db.Integer, default=0)
    cancel = db.Column(db.Integer, default=2)        # hours
    time_start = db.Column(db.String(5))             # "HH:MM"
    time_end = db.Column(db.String(5))               # "HH:MM"


class RestTableSeat(db.Model):
    """
    Individual tables for a type: 1,2,3,...,total
    status: free / reserved / unavailable
    """
    __tablename__ = "rest_tables"
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, nullable=False)
    type_id = db.Column(db.Integer, nullable=False)
    num = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default="free")


class RestBooking(db.Model):
    __tablename__ = "rest_bookings"
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, nullable=False)
    type_id = db.Column(db.Integer, nullable=False)
    slot_id = db.Column(db.Integer, nullable=False)
    date = db.Column(db.String(10), nullable=False)  # "YYYY-MM-DD"

    customer = db.Column(db.String(150))
    phone = db.Column(db.String(50))

    count = db.Column(db.Integer, default=1)
    price = db.Column(db.Integer, default=0)

    status = db.Column(db.String(20), default="upcoming")  # upcoming / cancelled
    tables_json = db.Column(db.Text)                       # JSON list of table nums
    payment_status = db.Column(db.String(20), default="pending")   # 'pending','paid','failed'
    payment_method = db.Column(db.String(20))                      # 'upi','cash','card'
    payment_ref = db.Column(db.String(120))                        # transaction id / UTR / gateway id
    payment_amount = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
def _get_or_create_rest_config(vendor_id: int) -> RestVendorConfig:
    cfg = RestVendorConfig.query.filter_by(vendor_id=vendor_id).first()
    if not cfg:
        cfg = RestVendorConfig(vendor_id=vendor_id)
        db.session.add(cfg)
        db.session.commit()
    return cfg


def _table_counts_for_type(vendor_id: int, type_id: int):
    qs = RestTableSeat.query.filter_by(vendor_id=vendor_id, type_id=type_id)
    free = qs.filter_by(status="free").count()
    reserved = qs.filter_by(status="reserved").count()
    unavail = qs.filter_by(status="unavailable").count()
    total = qs.count()
    return free, reserved, unavail, total


# =====================================================
#        FOOD ORDERING / QR MODELS
# =====================================================

class Restaurant(db.Model):
    """
    One vendor can have multiple restaurants/clubs for food ordering.
    This is used for 'Order Online' + QR menus.
    """
    __tablename__ = "restaurants"
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.String(300), nullable=False)
    description = db.Column(db.String(1000))
    is_nightlife = db.Column(db.Boolean, default=False)  # True if this is also a club
    banner_image = db.Column(db.Text)   # can store full base64
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ❌ REMOVED old columns:
    # delivery_fee, packing_fee,
    # offer_slab1_min, offer_slab1_percent,
    # offer_slab2_min, offer_slab2_percent

    # ✅ All delivery/packing/offer config is now handled by:
    # - RestaurantConfig (delivery_charge, packing_charge)
    # - RestaurantOffer (unlimited offers based on min_amount)

class MenuItem(db.Model):
    __tablename__ = "menu_items"
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(1000))
    price = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(100))
    food_type = db.Column(db.String(20))   # Veg / Non-Veg
    available = db.Column(db.Boolean, default=True)
    image_url = db.Column(db.String(300))

    # ❌ REMOVED: offer_percent column
    # Item-level discount is now via MenuOffer model (menu_offers table)

# Extra per-restaurant config (delivery, packing)
class RestaurantConfig(db.Model):
    __tablename__ = "restaurant_configs"
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, nullable=False, unique=True)
    delivery_charge = db.Column(db.Integer, default=0)
    packing_charge = db.Column(db.Integer, default=0)


# Unlimited "order total" offers per restaurant
class RestaurantOffer(db.Model):
    __tablename__ = "restaurant_offers"
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, nullable=False)
    min_amount = db.Column(db.Integer, nullable=False)   # e.g. 199
    percent = db.Column(db.Integer, nullable=False)      # e.g. 20 (%)


# Optional single offer per menu item (percentage)
class MenuOffer(db.Model):
    __tablename__ = "menu_offers"
    id = db.Column(db.Integer, primary_key=True)
    menu_item_id = db.Column(db.Integer, nullable=False, unique=True)
    percent = db.Column(db.Integer, nullable=False, default=0)


class QRTable(db.Model):
    """
    Each table (or area) has a unique qr_code_id.
    The QR image printed in the restaurant encodes this code.
    """
    __tablename__ = "qr_tables"
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, nullable=False)
    table_label = db.Column(db.String(50), nullable=False)  # e.g. T1, VIP-3
    qr_code_id = db.Column(db.String(100), unique=True, nullable=False)
    active = db.Column(db.Boolean, default=True)


class FoodOrder(db.Model):
    """
    Orders placed by scanning QR code.
    items_json = JSON string:
      [{ "menu_item_id": ..., "name": "...", "qty": ..., "price": ... }, ...]
    """
    __tablename__ = "food_orders"
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, nullable=False)
    restaurant_id = db.Column(db.Integer, nullable=False)
    qr_table_id = db.Column(db.Integer, nullable=True)
    table_label = db.Column(db.String(50))

    items_json = db.Column(db.Text, nullable=False)
    subtotal = db.Column(db.Integer, nullable=False)
    tax = db.Column(db.Integer, default=0)
    total = db.Column(db.Integer, nullable=False)

    status = db.Column(db.String(50), default="PENDING")  # PENDING / ACCEPTED / PREPARING / READY / SERVED / CANCELLED
    payment_status = db.Column(db.String(50), default="UNPAID")  # UNPAID / PAID

    user_name = db.Column(db.String(150))
    user_contact = db.Column(db.String(150))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# =====================================================
#                 EXTRA MODELS
# =====================================================

class DeliveryPartner(db.Model):
    __tablename__ = "delivery_partners"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(150))
    vehicle_type = db.Column(db.String(50))
    status = db.Column(db.String(20), default="offline")  # offline/online/busy
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Admin(db.Model):
    __tablename__ = "admins"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Table(db.Model):
    __tablename__ = "tables"
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, nullable=False)
    club_id = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(150))
    capacity = db.Column(db.String(50))
    price = db.Column(db.Integer, default=0)
    feature = db.Column(db.String(200))
    total_tables = db.Column(db.Integer, default=0)
    free_tables = db.Column(db.Integer, default=0)


class Event(db.Model):
    __tablename__ = "events"
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, nullable=False)
    club_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    date = db.Column(db.String(100), nullable=False)
    fee = db.Column(db.Integer, default=0)


class Rating(db.Model):
    __tablename__ = "ratings"
    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, nullable=False)
    user_name = db.Column(db.String(150), default="Anonymous")
    stars = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.String(1000))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Booking(db.Model):
    __tablename__ = "bookings"
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, nullable=False)
    club_id = db.Column(db.Integer, nullable=False)
    table_id = db.Column(db.Integer)
    table_type = db.Column(db.String(150))
    amount = db.Column(db.Integer, nullable=False)
    payment_id = db.Column(db.String(200))
    status = db.Column(db.String(50), default="PENDING")
    user_email = db.Column(db.String(150))
    user_name = db.Column(db.String(150))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class NightlifeCoupon(db.Model):
    __tablename__ = "nightlife_coupons"
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, nullable=False)
    club_id = db.Column(db.Integer, nullable=True)  # Null = valid for all clubs of vendor
    code = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # "percent" or "flat"
    value = db.Column(db.Integer, nullable=False)
    min_order = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class NightlifeOrder(db.Model):
    __tablename__ = "nightlife_orders"
    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, nullable=False)
    vendor_id = db.Column(db.Integer, nullable=False)

    user_id = db.Column(db.Integer, nullable=True)
    user_name = db.Column(db.String(150))
    user_phone = db.Column(db.String(20))
    user_address = db.Column(db.String(300))

    items_json = db.Column(db.Text, nullable=False)
    subtotal = db.Column(db.Integer, nullable=False)
    discount = db.Column(db.Integer, default=0)
    total = db.Column(db.Integer, nullable=False)

    coupon_code = db.Column(db.String(50))
    payment_method = db.Column(db.String(20))        # "COD" / "ONLINE"
    payment_status = db.Column(db.String(20), default="UNPAID")  # UNPAID / PAID
    status = db.Column(db.String(30), default="PENDING")         # PENDING / ACCEPTED / PREPARING / OUT_FOR_DELIVERY / DELIVERED / CANCELLED
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class DeliveryAssignment(db.Model):
    __tablename__ = "delivery_assignments"
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, nullable=False)
    partner_id = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), default="ASSIGNED")  # ASSIGNED/PICKED/DELIVERED/CANCELLED
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

class Coupon(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    type = db.Column(db.String(20), nullable=False, default="flat")  # 'flat' or 'percent'
    value = db.Column(db.Integer, nullable=False, default=0)         # amount or percent
    min_amount = db.Column(db.Integer, nullable=False, default=0)    # min cart value
    active = db.Column(db.Boolean, default=True)

    # if vendor_id is NULL -> admin coupon (global)
    # if vendor_id is set -> vendor coupon
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendors.id'), nullable=True)


    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "type": self.type,          # 'flat' / 'percent'
            "value": self.value,        # number
            "min": self.min_amount      # what frontend uses
        }

class DeliveryOrder(db.Model):
    __tablename__ = "delivery_orders"

    id = db.Column(db.Integer, primary_key=True)
    
    vendor_id = db.Column(db.Integer, nullable=False)
    restaurant_id = db.Column(db.Integer, nullable=False)

    items_json = db.Column(db.Text, nullable=False)
    subtotal = db.Column(db.Integer, nullable=False)
    gst = db.Column(db.Integer, default=0)
    discount = db.Column(db.Integer, default=0)
    total = db.Column(db.Integer, nullable=False)

    payment_method = db.Column(db.String(20), nullable=False)
    payment_status = db.Column(db.String(20), default="UNPAID")

    # NEW — correct customer fields
    user_name = db.Column(db.String(120))
    user_phone = db.Column(db.String(20))

    # NEW — correct address fields
    address_line1 = db.Column(db.String(200))
    address_line2 = db.Column(db.String(200))
    landmark = db.Column(db.String(200))
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    pincode = db.Column(db.String(20))
    country = db.Column(db.String(120))

    # NEW — correct GPS columns
    gps_lat = db.Column(db.String(50))
    gps_lng = db.Column(db.String(50))

    status = db.Column(db.String(30), default="PENDING")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)



# =====================================================
#                  HEALTH CHECK
# =====================================================

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "ZomaClone backend running"})


# =====================================================
#         USER REAL LOGIN (COOKIE SESSION)
# =====================================================

@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    phone = (data.get("phone") or "").strip()
    identifier = email or phone

    if not identifier:
        return jsonify({"ok": False, "message": "Email or phone required"}), 400

    user = User.query.filter(
        or_(User.email == identifier, User.phone == identifier)
    ).first()

    if not user:
        return jsonify({"ok": False, "message": "User not found"}), 404

    # Create session cookie
    token = create_user_session(user.id)

    resp = make_response(jsonify({
        "ok": True,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "phone": user.phone
        }
    }))

    resp.set_cookie(
        "zoma_session",
        token,
        httponly=True,
        samesite="Lax",
        max_age=7 * 24 * 3600,
        path="/"
    )

    return resp


@app.route("/api/auth/me", methods=["GET"])
def auth_me():
    user = get_current_user()
    if not user:
        return jsonify({"ok": False, "user": None})

    return jsonify({
        "ok": True,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "phone": user.phone
        }
    })


@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    token = request.cookies.get("zoma_session")
    if token:
        UserSession.query.filter_by(token=token).delete()
        db.session.commit()

    resp = make_response(jsonify({"ok": True}))
    resp.set_cookie("zoma_session", "", expires=0, path="/")
    return resp


@app.route("/api/coupons/admin", methods=["GET"])
def get_admin_coupons():
    """
    Return active admin-level coupons (global coupons).
    Used by restaurant.html for all users.
    """
    coupons = Coupon.query.filter_by(active=True, vendor_id=None).all()
    return jsonify([c.to_dict() for c in coupons])

@app.route("/api/coupons/vendor/<int:vendor_id>", methods=["GET"])
def get_vendor_coupons(vendor_id):
    """
    Return active coupons created by a specific vendor.
    Frontend passes restaurant.vendor_id.
    """
    coupons = Coupon.query.filter_by(active=True, vendor_id=vendor_id).all()
    return jsonify([c.to_dict() for c in coupons])

# =====================================================
#                   OTP HELPERS
# =====================================================

def generate_otp() -> str:
    return str(random.randint(1000, 9999))


def is_blocked(email: str, phone: str, role: str, purpose: str):
    q = OTPLog.query.filter_by(role=role, purpose=purpose)
    if email:
        q = q.filter(OTPLog.email == email)
    if phone:
        q = q.filter(OTPLog.phone == phone)
    last = q.order_by(OTPLog.id.desc()).first()
    if not last:
        return False, None
    if last.blocked_until and last.blocked_until > datetime.utcnow():
        return True, last.blocked_until
    return False, None


# =====================================================
#               GENERIC OTP: SEND (DUAL)
# =====================================================

@app.route("/api/otp/send", methods=["POST"])
def api_send_otp():
    """
    Request JSON:
    {
      "role": "user" | "vendor" | "admin" | "delivery",
      "purpose": "signup" | "login" | "reset" | "verify",
      "email": "abc@example.com",
      "phone": "+91xxxxxxxxxx"
    }
    Sends same 4-digit OTP to both email + phone.
    """
    data = get_data()
    role = data.get("role")
    purpose = data.get("purpose")
    email = (data.get("email") or "").strip()
    phone = (data.get("phone") or "").strip()

    if not role or not purpose:
        return jsonify({"success": False, "message": "role & purpose required"}), 400

    if not email and not phone:
        return jsonify({"success": False, "message": "email or phone required"}), 400

    blocked, unblock_time = is_blocked(email, phone, role, purpose)
    if blocked:
        return jsonify({
            "success": False,
            "message": "Too many wrong attempts. Try later.",
            "unblock_at": unblock_time.isoformat()
        }), 403

    code = generate_otp()
    expires = datetime.utcnow() + timedelta(minutes=5)

    otp = OTPLog(
        role=role,
        purpose=purpose,
        email=email or None,
        phone=phone or None,
        code=code,
        expires_at=expires
    )
    db.session.add(otp)
    db.session.commit()

    email_status = send_email(email, "Your ZomaClone OTP", f"Your OTP is {code}") if email else False
    sms_status = send_sms(phone, code) if phone else False

    return jsonify({
        "success": True,
        "message": "OTP sent",
        "email_sent": email_status,
        "sms_sent": sms_status
    })


# =====================================================
#               GENERIC OTP: VERIFY
# =====================================================

@app.route("/api/otp/verify", methods=["POST"])
def api_verify_otp():
    """
    Request JSON:
    {
      "role": "user" | "vendor" | "admin" | "delivery",
      "purpose": "signup" | "login" | "reset" | "verify",
      "email": "...",
      "phone": "...",
      "code": "1234"
    }
    """
    data = get_data()
    role = data.get("role")
    purpose = data.get("purpose")
    email = (data.get("email") or "").strip()
    phone = (data.get("phone") or "").strip()
    code = (data.get("code") or "").strip()

    if not role or not purpose or not code:
        return jsonify({"success": False, "message": "role, purpose, code required"}), 400

    q = OTPLog.query.filter_by(role=role, purpose=purpose)
    if email:
        q = q.filter(OTPLog.email == email)
    if phone:
        q = q.filter(OTPLog.phone == phone)
    otp = q.order_by(OTPLog.id.desc()).first()

    if not otp:
        return jsonify({"success": False, "message": "OTP not found"}), 404

    if otp.blocked_until and otp.blocked_until > datetime.utcnow():
        return jsonify({"success": False, "message": "Blocked for 24 hours"}), 403

    if otp.expires_at < datetime.utcnow():
        return jsonify({"success": False, "message": "OTP expired"}), 400

    if otp.code == code:
        otp.is_verified = True
        db.session.commit()
        return jsonify({"success": True, "message": "OTP verified"})

    # wrong OTP
    otp.attempts += 1
    if otp.attempts >= 5:
        otp.blocked_until = datetime.utcnow() + timedelta(hours=24)
    db.session.commit()
    return jsonify({"success": False, "message": "Incorrect OTP", "attempts": otp.attempts})

def create_user_session(user_id):
    token = str(uuid.uuid4())
    now = datetime.utcnow()
    session = UserSession(
        user_id=user_id,
        token=token,
        created_at=now,
        expires_at=now + timedelta(days=7)
    )
    db.session.add(session)
    db.session.commit()
    return token


def get_current_user():
    token = request.cookies.get("zoma_session")
    if not token:
        return None

    session = UserSession.query.filter_by(token=token).first()
    if not session:
        return None
    if session.expires_at < datetime.utcnow():
        return None

    user = User.query.get(session.user_id)
    return user


# =====================================================
#      VENDOR-SPECIFIC OTP ENDPOINTS (for vendor.html)
# =====================================================

@app.route("/api/vendor/send-otp", methods=["POST"])
def vendor_send_otp():
    """
    Used by vendor.html registration:
    Body: { "email": "..." }
    role = vendor, purpose = signup
    """
    data = get_data()
    email = (data.get("email") or "").strip().lower()

    if not email:
        return jsonify({"success": False, "message": "Email required"}), 400

    blocked, unblock_time = is_blocked(email, None, "vendor", "signup")
    if blocked:
        return jsonify({
            "success": False,
            "message": "Too many attempts. Try later.",
            "unblock_at": unblock_time.isoformat()
        }), 403

    code = generate_otp()
    expires = datetime.utcnow() + timedelta(minutes=5)

    otp = OTPLog(
        role="vendor",
        purpose="signup",
        email=email,
        phone=None,
        code=code,
        expires_at=expires
    )
    db.session.add(otp)
    db.session.commit()

    email_ok = send_email(email, "Verify your vendor account", f"Your ZomaClone vendor OTP is {code}")

    return jsonify({
        "success": True,
        "message": "OTP sent to email",
        "email_sent": email_ok
    })


@app.route("/api/vendor/verify-otp", methods=["POST"])
def vendor_verify_otp():
    """
    Used by vendor.html register OTP modal:
    Body: { "email": "...", "otp": "1234" }
    """
    data = get_data()
    email = (data.get("email") or "").strip().lower()
    code = (data.get("otp") or data.get("code") or "").strip()

    if not email or not code:
        return jsonify({"success": False, "message": "Email & OTP required"}), 400

    q = OTPLog.query.filter_by(role="vendor", purpose="signup", email=email)
    otp = q.order_by(OTPLog.id.desc()).first()

    if not otp:
        return jsonify({"success": False, "message": "OTP not found"}), 404

    if otp.blocked_until and otp.blocked_until > datetime.utcnow():
        return jsonify({"success": False, "message": "Blocked for 24 hours"}), 403

    if otp.expires_at < datetime.utcnow():
        return jsonify({"success": False, "message": "OTP expired"}), 400

    if otp.code != code:
        otp.attempts += 1
        if otp.attempts >= 5:
            otp.blocked_until = datetime.utcnow() + timedelta(hours=24)
        db.session.commit()
        return jsonify({"success": False, "message": "Incorrect OTP"}), 400

    otp.is_verified = True
    db.session.commit()
    return jsonify({"success": True, "message": "OTP verified"})



# ---------- Vendor LOGIN OTP (email OR phone) ----------

@app.route("/api/vendor/login-send-otp", methods=["POST"])
def vendor_login_send_otp():
    """
    Vendor Login (OTP only)
    Body: { "identifier": "<email or phone>" }
    Sends OTP to vendor's email + phone
    """
    data = get_data()
    identifier = (data.get("identifier") or "").strip()

    if not identifier:
        return jsonify({"success": False, "message": "Email or phone required"}), 400

    vendor = Vendor.query.filter(
        or_(Vendor.email == identifier, Vendor.phone == identifier)
    ).first()

    if not vendor:
        return jsonify({"success": False, "message": "Vendor not found"}), 404

    email = vendor.email
    phone = vendor.phone

    blocked, unblock_time = is_blocked(email, phone, "vendor", "login")
    if blocked:
        return jsonify({
            "success": False,
            "message": "Too many attempts. Try again later.",
            "unblock_at": unblock_time.isoformat()
        }), 403

    code = generate_otp()
    expires = datetime.utcnow() + timedelta(minutes=5)

    otp = OTPLog(
        role="vendor",
        purpose="login",
        email=email,
        phone=phone,
        code=code,
        expires_at=expires
    )
    db.session.add(otp)
    db.session.commit()

    email_ok = send_email(email, "Vendor Login OTP", f"Your login OTP is {code}")
    sms_ok = send_sms(phone, code)

    return jsonify({
        "success": True,
        "message": "OTP sent to your registered email / phone.",
        "email_sent": email_ok,
        "sms_sent": sms_ok
    })


@app.route("/api/vendor/login-verify-otp", methods=["POST"])
def vendor_login_verify_otp():
    """
    Vendor Login OTP verification
    Body: { "identifier": "<email or phone>", "otp": "1234" }
    """
    data = get_data()
    identifier = (data.get("identifier") or "").strip()
    code = (data.get("otp") or data.get("code") or "").strip()

    if not identifier or not code:
        return jsonify({"success": False, "message": "Identifier & OTP required"}), 400

    vendor = Vendor.query.filter(
        or_(Vendor.email == identifier, Vendor.phone == identifier)
    ).first()

    if not vendor:
        return jsonify({"success": False, "message": "Vendor not found"}), 404

    q = OTPLog.query.filter_by(role="vendor", purpose="login", email=vendor.email)
    otp = q.order_by(OTPLog.id.desc()).first()

    if not otp:
        return jsonify({"success": False, "message": "OTP not found"}), 404

    if otp.blocked_until and otp.blocked_until > datetime.utcnow():
        return jsonify({"success": False, "message": "Blocked for 24 hours"}), 403

    if otp.expires_at < datetime.utcnow():
        return jsonify({"success": False, "message": "OTP expired"}), 400

    if otp.code != code:
        otp.attempts += 1
        if otp.attempts >= 5:
            otp.blocked_until = datetime.utcnow() + timedelta(hours=24)
        db.session.commit()
        return jsonify({"success": False, "message": "Incorrect OTP"}), 400

    otp.is_verified = True
    db.session.commit()

    # success → send vendor details
    return jsonify({
        "success": True,
        "message": "Login successful",
        "vendor": {
            "id": vendor.id,
            "restaurant_name": vendor.restaurant_name,
            "owner_name": vendor.owner_name,
            "email": vendor.email,
            "phone": vendor.phone,
            "address": vendor.address
        }
    })


# =====================================================
#                   USER AUTH / PROFILE
# =====================================================

@app.route("/api/users/register", methods=["POST"])
def register_user():
    """
    Flow:
      1) /api/otp/send (role=user, purpose=signup)
      2) /api/otp/verify
      3) /api/users/register
    """
    data = get_data()

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    phone = (data.get("phone") or "").strip()

    if not name or not email or not phone:
        return jsonify({"success": False, "message": "name, email, phone required"}), 400

    # Check duplicate user
    existing = User.query.filter(
        or_(User.email == email, User.phone == phone)
    ).first()

    if existing:
        return jsonify({"success": False, "message": "User already exists"}), 409

    # Match OTP using email OR phone
    otp_verified = OTPLog.query.filter(
        OTPLog.role == "user",
        OTPLog.purpose == "signup",
        OTPLog.is_verified == True,
        or_(OTPLog.email == email, OTPLog.phone == phone)
    ).order_by(OTPLog.id.desc()).first()

    if not otp_verified:
        return jsonify({"success": False, "message": "OTP not verified"}), 400

    # Create user
    u = User(name=name, email=email, phone=phone)
    db.session.add(u)
    db.session.commit()

    return jsonify({
        "success": True,
        "user": {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "phone": u.phone
        }
    })


@app.route("/api/users/login", methods=["POST"])
def login_user():
    """
    Use OTP (role=user, purpose=login) separately.
    Here we just confirm user exists.
    """
    data = get_data()
    identifier = (data.get("identifier") or "").strip()

    if not identifier:
        return jsonify({"success": False, "message": "identifier required"}), 400

    u = User.query.filter(or_(User.email == identifier, User.phone == identifier)).first()
    if not u:
        return jsonify({"success": False, "message": "User not found"}), 404

    return jsonify({
        "success": True,
        "user": {"id": u.id, "name": u.name, "email": u.email, "phone": u.phone}
    })


# =====================================================
#                   VENDOR AUTH (NON-OTP)
# =====================================================

@app.route("/api/vendors/register", methods=["POST"])
def register_vendor():
    """
    For restaurant / club owners.
    """
    data = get_data()
    restaurant_name = (data.get("restaurant_name") or "").strip()
    owner_name = (data.get("owner_name") or "").strip()
    email = (data.get("email") or "").strip()
    phone = (data.get("phone") or "").strip()
    address = (data.get("address") or "").strip()
    password = (data.get("password") or "").strip() or None

    if not restaurant_name or not owner_name or not email or not phone or not address:
        return jsonify({"success": False, "message": "Missing fields"}), 400

    existing = Vendor.query.filter(or_(Vendor.email == email, Vendor.phone == phone)).first()
    if existing:
        return jsonify({"success": False, "message": "Vendor already exists"}), 409

    v = Vendor(
        restaurant_name=restaurant_name,
        owner_name=owner_name,
        email=email,
        phone=phone,
        address=address,
        password=password
    )
    db.session.add(v)
    db.session.commit()

    return jsonify({"success": True, "vendor_id": v.id})


@app.route("/api/vendors/login", methods=["POST"])
def login_vendor_plain():
    data = get_data()
    identifier = (data.get("identifier") or "").strip()
    password = (data.get("password") or "").strip() or None

    if not identifier:
        return jsonify({"success": False, "message": "identifier required"}), 400

    q = Vendor.query.filter(or_(Vendor.email == identifier, Vendor.phone == identifier))
    if password:
        q = q.filter(Vendor.password == password)
    v = q.first()

    if not v:
        return jsonify({"success": False, "message": "Invalid credentials"}), 401

    return jsonify({
        "success": True,
        "vendor": {
            "id": v.id,
            "restaurant_name": v.restaurant_name,
            "owner_name": v.owner_name,
            "email": v.email,
            "phone": v.phone,
            "address": v.address
        }
    })


# =====================================================
#                DELIVERY PARTNER AUTH
# =====================================================

@app.route("/api/delivery/register", methods=["POST"])
def register_delivery_partner():
    data = get_data()
    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip()
    email = (data.get("email") or "").strip() or None
    vehicle_type = (data.get("vehicle_type") or "").strip() or None

    if not name or not phone:
        return jsonify({"success": False, "message": "name & phone required"}), 400

    # build filters safely
    filters = [DeliveryPartner.phone == phone]
    if email:
        filters.append(DeliveryPartner.email == email)

    existing = DeliveryPartner.query.filter(or_(*filters)).first()
    if existing:
        return jsonify({"success": False, "message": "Delivery partner already exists"}), 409

    dp = DeliveryPartner(
        name=name, phone=phone, email=email, vehicle_type=vehicle_type, status="offline"
    )
    db.session.add(dp)
    db.session.commit()

    return jsonify({"success": True, "partner_id": dp.id})


@app.route("/api/delivery/login", methods=["POST"])
def login_delivery_partner():
    data = get_data()
    identifier = (data.get("identifier") or "").strip()

    if not identifier:
        return jsonify({"success": False, "message": "identifier required"}), 400

    dp = DeliveryPartner.query.filter(
        or_(DeliveryPartner.phone == identifier, DeliveryPartner.email == identifier)
    ).first()

    if not dp:
        return jsonify({"success": False, "message": "Delivery partner not found"}), 404

    return jsonify({
        "success": True,
        "partner": {
            "id": dp.id,
            "name": dp.name,
            "phone": dp.phone,
            "email": dp.email,
            "vehicle_type": dp.vehicle_type,
            "status": dp.status
        }
    })


@app.route("/api/delivery/<int:partner_id>/status", methods=["POST"])
def update_partner_status(partner_id):
    data = get_data()
    status = (data.get("status") or "").strip()  # offline / online / busy

    dp = DeliveryPartner.query.get(partner_id)
    if not dp:
        return jsonify({"success": False, "message": "Partner not found"}), 404

    if status not in ("offline", "online", "busy"):
        return jsonify({"success": False, "message": "Invalid status"}), 400

    dp.status = status
    db.session.commit()

    return jsonify({"success": True})


# =====================================================
#                     ADMIN LOGIN (OTP)
# =====================================================

@app.route("/api/admin/login/start", methods=["POST"])
def admin_login_start():
    """
    Step 1: admin enters email_or_phone → send dual OTP
    (role=admin, purpose=login)
    """
    data = get_data()
    identifier = (data.get("identifier") or "").strip()

    if not identifier:
        return jsonify({"success": False, "message": "identifier required"}), 400

    admin = Admin.query.filter(
        or_(Admin.email == identifier, Admin.phone == identifier)
    ).first()

    if not admin:
        return jsonify({"success": False, "message": "Admin not found"}), 404

    code = generate_otp()
    expires = datetime.utcnow() + timedelta(minutes=5)

    otp = OTPLog(
        role="admin",
        purpose="login",
        email=admin.email,
        phone=admin.phone,
        code=code,
        expires_at=expires
    )
    db.session.add(otp)
    db.session.commit()

    send_email(admin.email, "Admin Login OTP", f"Your admin OTP is {code}")
    send_sms(admin.phone, code)

    return jsonify({"success": True, "message": "OTP sent to admin"})


@app.route("/api/admin/login/verify", methods=["POST"])
def admin_login_verify():
    data = get_data()
    email = (data.get("email") or "").strip()
    phone = (data.get("phone") or "").strip()
    code = (data.get("code") or "").strip()

    if not email and not phone:
        return jsonify({"success": False, "message": "email or phone required"}), 400

    q = OTPLog.query.filter_by(role="admin", purpose="login")
    if email:
        q = q.filter(OTPLog.email == email)
    if phone:
        q = q.filter(OTPLog.phone == phone)
    otp = q.order_by(OTPLog.id.desc()).first()

    if not otp or otp.code != code or otp.expires_at < datetime.utcnow():
        return jsonify({"success": False, "message": "Invalid/expired OTP"}), 400

    otp.is_verified = True
    db.session.commit()

    admin = Admin.query.filter(
        or_(Admin.email == email, Admin.phone == phone)
    ).first()

    if not admin:
        return jsonify({"success": False, "message": "Admin not found"}), 404

    return jsonify({
        "success": True,
        "admin": {
            "id": admin.id,
            "name": admin.name,
            "email": admin.email,
            "phone": admin.phone
        }
    })


# =====================================================
#                    VENDOR PANEL: CLUBS
# =====================================================

@app.route("/vendor/addClub", methods=["POST"])
def add_club():
    data = get_data()

    try:
        vendor_id = int(data.get("vendor_id"))
    except Exception:
        return jsonify({"ok": False, "error": "vendor_id invalid"}), 400

    # Count existing clubs (max 5 per vendor)
    existing_clubs = Club.query.filter_by(vendor_id=vendor_id).count()
    if existing_clubs >= 5:
        return jsonify({
            "ok": False,
            "message": "Maximum 5 clubs allowed per vendor"
        }), 400

    club = Club(
        vendor_id=vendor_id,
        club_name=(data.get("club_name") or "").strip(),
        location=(data.get("location") or "").strip(),
        music=(data.get("music") or "").strip(),
        dress=(data.get("dress") or "").strip(),
        description=(data.get("description") or "").strip()
    )
    db.session.add(club)
    db.session.commit()

    return jsonify({"ok": True, "message": "Club Added", "club_id": club.id})


@app.route("/vendor/getClubs/<int:vendor_id>")
def get_clubs(vendor_id):
    clubs = Club.query.filter_by(vendor_id=vendor_id).all()
    result = []
    for c in clubs:
        img = ClubImage.query.filter_by(club_id=c.id).first()
        thumb = img.image_url if img else "/Images/default.jpg"
        result.append({
            "club_id": c.id,
            "club_name": c.club_name,
            "location": c.location,
            "music": c.music,
            "dress": c.dress,
            "description": c.description,
            "image": thumb
        })
    return jsonify(result)

@app.route("/Images/<path:filename>")
def images(filename):
    return send_from_directory("Images", filename)

@app.route("/vendor/uploadClubImages/<int:club_id>", methods=["POST"])
def upload_club_images(club_id):
    if "images" not in request.files:
        return jsonify({"ok": False, "message": "No images found"}), 400

    files = request.files.getlist("images")[:5]
    saved = []

    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            new_name = f"{club_id}_{filename}".replace(" ", "_")
            path = os.path.join(app.config["UPLOAD_FOLDER"], new_name)
            file.save(path)

            img = ClubImage(club_id=club_id, image_url=f"/uploads/{new_name}")
            db.session.add(img)
            saved.append(f"/uploads/{new_name}")

    db.session.commit()
    return jsonify({"ok": True, "message": "Images uploaded", "images": saved})


@app.route("/vendor/getClubImages/<int:club_id>")
def get_club_images(club_id):
    imgs = ClubImage.query.filter_by(club_id=club_id).all()
    return jsonify([i.image_url for i in imgs])


# =====================================================
#                    VENDOR PANEL: TABLES
# =====================================================

@app.route("/vendor/addTable", methods=["POST"])
def add_table():
    data = get_data()
    try:
        vendor_id = int(data.get("vendor_id"))
        club_id = int(data.get("club_id"))
    except Exception:
        return jsonify({"ok": False, "error": "vendor_id/club_id invalid"}), 400

    def to_int(val, default=0):
        try:
            return int(str(val)) if val not in (None, "", "null") else default
        except ValueError:
            return default

    t = Table(
        vendor_id=vendor_id,
        club_id=club_id,
        category=(data.get("category") or "").strip(),
        capacity=(data.get("capacity") or "").strip(),
        price=to_int(data.get("price"), 0),
        feature=(data.get("feature") or "").strip(),
        total_tables=to_int(data.get("total_tables"), 0),
        free_tables=to_int(data.get("free_tables"), 0),
    )
    db.session.add(t)
    db.session.commit()
    return jsonify({"ok": True, "message": "Table added"})


@app.route("/vendor/getTables/<int:club_id>")
def get_tables(club_id):
    tables = Table.query.filter_by(club_id=club_id).all()
    return jsonify([
        {
            "id": t.id,
            "category": t.category,
            "capacity": t.capacity,
            "price": t.price,
            "feature": t.feature,
            "total_tables": t.total_tables,
            "free_tables": t.free_tables
        }
        for t in tables
    ])


@app.route("/vendor/deleteTable/<int:table_id>", methods=["DELETE"])
def delete_table(table_id):
    t = Table.query.get(table_id)
    if t:
        db.session.delete(t)
        db.session.commit()
    return jsonify({"ok": True})


# =====================================================
#                    VENDOR PANEL: EVENTS
# =====================================================

@app.route("/vendor/addEvent", methods=["POST"])
def add_event():
    data = get_data()
    try:
        vendor_id = int(data.get("vendor_id"))
        club_id = int(data.get("club_id"))
    except Exception:
        return jsonify({"ok": False, "error": "vendor_id/club_id invalid"}), 400

    def to_int(val, default=0):
        try:
            return int(str(val)) if val not in (None, "", "null") else default
        except ValueError:
            return default

    e = Event(
        vendor_id=vendor_id,
        club_id=club_id,
        name=(data.get("name") or "").strip(),
        date=(data.get("date") or "").strip(),
        fee=to_int(data.get("fee"), 0)
    )
    db.session.add(e)
    db.session.commit()
    return jsonify({"ok": True, "message": "Event added"})


@app.route("/vendor/getEvents/<int:club_id>")
def get_events(club_id):
    events = Event.query.filter_by(club_id=club_id).all()
    return jsonify([
        {"id": e.id, "name": e.name, "date": e.date, "fee": e.fee} for e in events
    ])


# =====================================================
#                   USER SIDE: CLUB LIST
# =====================================================
@app.get("/api/restaurant/<int:restaurant_id>")
def get_single_restaurant(restaurant_id):
    r = Restaurant.query.get(restaurant_id)
    if not r:
        return jsonify({"success": False, "message": "Restaurant not found"}), 404

    cfg = RestaurantConfig.query.filter_by(restaurant_id=r.id).first()
    offers = RestaurantOffer.query.filter_by(restaurant_id=r.id).all()

    prefix = "data:image/jpeg;base64,"

    return jsonify({
        "success": True,
        "restaurant": {
            "id": r.id,
            "vendor_id": r.vendor_id,
            "name": r.name,
            "address": r.address,
            "description": r.description,
            "is_nightlife": r.is_nightlife,
            "banner_image": (
                prefix + r.banner_image
                if r.banner_image and not r.banner_image.startswith("data:image")
                else r.banner_image
            ) or None,
            "delivery_charge": cfg.delivery_charge if cfg else 0,
            "packing_charge": cfg.packing_charge if cfg else 0,
            "offers": [
                {"id": o.id, "min_amount": o.min_amount, "percent": o.percent}
                for o in offers
            ],
        }
    })



@app.route("/nightlife/clubs")
def nightlife_club_list():
    """
    Used by nightlife_order.html (user side) to show all nightlife restaurants.
    """
    clubs = Club.query.all()
    result = []
    for c in clubs:
        img = ClubImage.query.filter_by(club_id=c.id).first()
        thumb = img.image_url if img else "/Images/default.jpg"
        desc = c.description or ""
        short_desc = (desc[:120] + "...") if len(desc) > 120 else desc
        result.append({
            "club_id": c.id,
            "vendor_id": c.vendor_id,
            "club_name": c.club_name,
            "location": c.location,
            "music": c.music,
            "description": short_desc,
            "image": thumb
        })
    return jsonify(result)


@app.route("/user/club/<int:club_id>")
def user_club(club_id):
    c = Club.query.get(club_id)
    if not c:
        return jsonify({"error": "Club not found"}), 404

    tables = Table.query.filter_by(club_id=club_id).all()
    events = Event.query.filter_by(club_id=club_id).all()
    imgs = ClubImage.query.filter_by(club_id=club_id).all()

    return jsonify({
        "club": {
            "id": c.id,
            "vendor_id": c.vendor_id,
            "name": c.club_name,
            "location": c.location,
            "music": c.music,
            "dress": c.dress,
            "description": c.description,
            "images": [i.image_url for i in imgs]
        },
        "tables": [
            {
                "id": t.id,
                "category": t.category,
                "capacity": t.capacity,
                "price": t.price,
                "feature": t.feature,
                "total_tables": t.total_tables,
                "free_tables": t.free_tables
            } for t in tables
        ],
        "events": [
            {"id": e.id, "name": e.name, "date": e.date, "fee": e.fee}
            for e in events
        ]
    })


# =====================================================
#                         RATINGS
# =====================================================

@app.route("/rating/add", methods=["POST"])
def add_rating():
    data = get_data()
    try:
        club_id = int(data.get("club_id"))
        stars = int(data.get("stars"))
    except Exception:
        return jsonify({"ok": False, "error": "club_id/stars invalid"}), 400

    r = Rating(
        club_id=club_id,
        user_name=(data.get("name") or "Anonymous").strip(),
        stars=stars,
        comment=(data.get("comment") or "").strip()
    )
    db.session.add(r)
    db.session.commit()
    return jsonify({"ok": True})


@app.route("/rating/club/<int:club_id>")
def get_ratings(club_id):
    ratings = Rating.query.filter_by(club_id=club_id).all()
    if not ratings:
        return jsonify({"avg": 0, "count": 0, "items": []})

    avg = round(sum([r.stars for r in ratings]) / len(ratings), 1)
    return jsonify({
        "avg": avg,
        "count": len(ratings),
        "items": [
            {"name": r.user_name, "stars": r.stars, "comment": r.comment}
            for r in ratings
        ]
    })


# ------------------ NIGHTLIFE MENU ITEMS (OLD STYLE) ------------------

@app.route("/vendor/nightlife/<int:club_id>/menu-item", methods=["POST"])
def add_nightlife_menu_item(club_id):
    data = get_data()

    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"success": False, "message": "Item name required"}), 400

    try:
        price = int(str(data.get("price")))
    except Exception:
        return jsonify({"success": False, "message": "Invalid price"}), 400

    item = NightlifeMenuItem(
        club_id=club_id,
        name=name,
        price=price,
        category=(data.get("category") or "").strip(),
        food_type=(data.get("food_type") or "").strip(),
        available=True,
        image_url=(data.get("image_url") or "").strip(),
        description=(data.get("description") or "").strip()
    )

    db.session.add(item)
    db.session.commit()

    return jsonify({"success": True, "message": "Nightlife item added", "item_id": item.id})


@app.route("/nightlife/menu/<int:club_id>", methods=["GET"])
def get_nightlife_menu(club_id):
    items = NightlifeMenuItem.query.filter_by(club_id=club_id).all()
    return jsonify([
        {
            "id": i.id,
            "name": i.name,
            "price": i.price,
            "category": i.category,
            "food_type": i.food_type,
            "image_url": i.image_url,
            "description": i.description
        }
        for i in items
    ])


@app.route("/vendor/nightlife/menu-item/<int:item_id>", methods=["DELETE"])
def delete_nightlife_item(item_id):
    item = NightlifeMenuItem.query.get(item_id)
    if not item:
        return jsonify({"success": False, "message": "Item not found"}), 404

    db.session.delete(item)
    db.session.commit()

    return jsonify({"success": True, "message": "Item deleted"})


# ------------------ NIGHTLIFE ITEMS (for vendor_order_online.html) ------------------

@app.route("/vendor/getNightlifeItems/<int:vendor_id>")
def get_nightlife_items_for_vendor(vendor_id):
    """
    Used by vendor_order_online.html:
      GET /vendor/getNightlifeItems/<vendor_id>
    Returns all nightlife items for all clubs of that vendor.
    """
    clubs = Club.query.filter_by(vendor_id=vendor_id).all()
    if not clubs:
        return jsonify([])

    club_ids = [c.id for c in clubs]
    items = NightlifeMenuItem.query.filter(
        NightlifeMenuItem.club_id.in_(club_ids)
    ).all()

    result = []
    for i in items:
        result.append({
            "id": i.id,
            "item_id": i.id,
            "vendor_id": vendor_id,
            "club_id": i.club_id,
            "item_name": i.name,
            "name": i.name,
            "category": i.category,
            "price": i.price,
            "description": i.description,
            "availability": "Available" if i.available else "Out of Stock",
            "image_url": i.image_url,
            "image": i.image_url
        })
    return jsonify(result)


@app.route("/vendor/addNightlifeItem", methods=["POST"])
def add_nightlife_item_for_vendor():
    """
    Used by vendor_order_online.html:
      POST multipart/form-data to /vendor/addNightlifeItem
      Fields:
        vendor_id, club_id, item_name, category, price,
        description, availability, image(file)
    """
    form = request.form
    try:
        vendor_id = int(form.get("vendor_id") or 0)
        club_id = int(form.get("club_id") or 0)
    except Exception:
        return jsonify({"success": False, "message": "Invalid vendor_id/club_id"}), 400

    if not vendor_id or not club_id:
        return jsonify({"success": False, "message": "vendor_id and club_id required"}), 400

    club = Club.query.filter_by(id=club_id, vendor_id=vendor_id).first()
    if not club:
        return jsonify({"success": False, "message": "Club not found for this vendor"}), 404

    name = (form.get("item_name") or "").strip()
    category = (form.get("category") or "").strip()
    description = (form.get("description") or "").strip()
    availability_raw = (form.get("availability") or "Available").strip()

    try:
        price = int(str(form.get("price")))
    except Exception:
        return jsonify({"success": False, "message": "Invalid price"}), 400

    if not name or not category:
        return jsonify({"success": False, "message": "item_name & category required"}), 400

    image_file = request.files.get("image")
    img_url = None
    if image_file and allowed_file(image_file.filename):
        filename = secure_filename(image_file.filename)
        new_name = f"night_{club_id}_{filename}".replace(" ", "_")
        path = os.path.join(app.config["UPLOAD_FOLDER"], new_name)
        image_file.save(path)
        img_url = f"/uploads/{new_name}"

    item = NightlifeMenuItem(
        club_id=club_id,
        name=name,
        price=price,
        category=category,
        food_type=None,
        available=(availability_raw.lower() == "available"),
        image_url=img_url,
        description=description
    )
    db.session.add(item)
    db.session.commit()

    return jsonify({"success": True, "message": "Nightlife item added", "item_id": item.id})


@app.route("/vendor/editNightlifeItem/<int:item_id>", methods=["PUT"])
def edit_nightlife_item_for_vendor(item_id):
    """
    Used by vendor_order_online.html:
      PUT JSON to /vendor/editNightlifeItem/<id>
      Body can include: item_name/name, category, price, description, availability
    """
    data = get_data()
    item = NightlifeMenuItem.query.get(item_id)
    if not item:
        return jsonify({"success": False, "message": "Item not found"}), 404

    if "item_name" in data or "name" in data:
        item.name = (data.get("item_name") or data.get("name") or item.name).strip()
    if "category" in data:
        item.category = (data.get("category") or item.category or "").strip()
    if "price" in data:
        try:
            item.price = int(str(data.get("price")))
        except Exception:
            pass
    if "description" in data:
        item.description = (data.get("description") or item.description or "").strip()
    if "availability" in data:
        av = (data.get("availability") or "").strip()
        if av:
            item.available = (av.lower() == "available")

    db.session.commit()
    return jsonify({"success": True, "message": "Item updated"})


@app.route("/vendor/deleteNightlifeItem/<int:item_id>", methods=["DELETE"])
def delete_nightlife_item_legacy(item_id):
    """
    Used by vendor_order_online.html:
      DELETE /vendor/deleteNightlifeItem/<id>
    """
    item = NightlifeMenuItem.query.get(item_id)
    if not item:
        return jsonify({"success": False, "message": "Item not found"}), 404

    db.session.delete(item)
    db.session.commit()
    return jsonify({"success": True, "message": "Item deleted"})


# =====================================================
#          FOOD RESTAURANTS & MENUS (VENDOR)
# =====================================================
@app.get("/api/vendors/<int:vendor_id>")
def get_vendor(vendor_id):
    v = Vendor.query.get(vendor_id)
    if not v:
        return jsonify({"success": False, "message": "Vendor not found"}), 404

    return jsonify({
        "success": True,
        "vendor": {
            "id": v.id,
            "restaurant_name": v.restaurant_name,
            "owner_name": v.owner_name,
            "email": v.email,
            "phone": v.phone,
            "address": v.address,
            "upi_id": v.upi_id  # 👈 real UPI ID from DB (can be null)
        }
    })

# UPI update – allow both PUT and POST so frontend can use either
@app.route("/api/vendors/<int:vendor_id>/upi", methods=["PUT"])
@app.route("/api/rest/vendor/<int:vendor_id>/upi", methods=["PUT"])
def update_vendor_upi(vendor_id):
    data = get_data()
    upi = (data.get("upi_id") or "").strip()

    v = Vendor.query.get(vendor_id)
    if not v:
        return jsonify({"success": False, "message": "Vendor not found"}), 404

    v.upi_id = upi or None
    db.session.commit()

    return jsonify({"success": True, "upi_id": v.upi_id})

@app.route("/api/vendor/restaurants", methods=["POST"])
def create_or_update_restaurant():
    """
    Create or update restaurant.

    Supports:
    - application/json (base64 banner + delivery/packing/offers)
    - multipart/form-data (file upload; charges/offers ignored there)
    """
    is_multipart = request.content_type and "multipart/form-data" in request.content_type

    # ---------- MULTIPART (file upload from some old forms) ----------
    if is_multipart:
        form = request.form
        vendor_id = form.get("vendor_id")
        name = (form.get("name") or "").strip()
        address = (form.get("address") or "").strip()
        description = (form.get("description") or "").strip()
        is_nightlife = form.get("is_nightlife") == "true"
        file = request.files.get("banner_image")
        base64_banner = None
        rest_id = form.get("restaurant_id")

        # for multipart we ignore offers; delivery/packing can be default
        delivery_charge = 0
        packing_charge = 0
        offers = []

    # ---------- JSON (what your vendor frontend uses) ----------
    else:
        data = request.get_json() or {}
        vendor_id = data.get("vendor_id")
        name = (data.get("name") or "").strip()
        address = (data.get("address") or "").strip()
        description = (data.get("description") or "").strip()
        is_nightlife = bool(data.get("is_nightlife"))
        file = None
        base64_banner = data.get("banner_image")
        rest_id = data.get("restaurant_id")

        # ✅ NEW: delivery / packing / unlimited offers
        try:
            delivery_charge = int(data.get("delivery_charge") or 0)
        except Exception:
            delivery_charge = 0

        try:
            packing_charge = int(data.get("packing_charge") or 0)
        except Exception:
            packing_charge = 0

        # e.g. [{min_amount:199, percent:20}, {min_amount:399, percent:25}, ...]
        offers = data.get("offers") or []

    # --------- VALIDATION ----------
    try:
        vendor_id = int(vendor_id)
    except Exception:
        return jsonify({"success": False, "message": "Invalid vendor_id"}), 400

    if not name or not address:
        return jsonify({"success": False, "message": "name & address required"}), 400

    # --------- UPDATE RESTAURANT ---------
    if rest_id:
        rest_id = int(rest_id)
        r = Restaurant.query.get(rest_id)
        if not r:
            return jsonify({"success": False, "message": "Restaurant not found"}), 404
        if r.vendor_id != vendor_id:
            return jsonify({"success": False, "message": "Not allowed"}), 403

        r.name = name
        r.address = address
        r.description = description
        r.is_nightlife = is_nightlife

        # Banner
        if is_multipart and file:
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                new_name = f"rest_{rest_id}_{filename}".replace(" ", "_")
                path = os.path.join(app.config["UPLOAD_FOLDER"], new_name)
                file.save(path)
                r.banner_image = f"/uploads/{new_name}"
        elif base64_banner:
            r.banner_image = base64_banner

        db.session.commit()

        # ✅ for JSON calls, update RestaurantConfig + RestaurantOffer
        if not is_multipart:
            _save_restaurant_config_and_offers(r.id, delivery_charge, packing_charge, offers)

        return jsonify({"success": True, "message": "Restaurant updated", "restaurant_id": r.id})

    # --------- CREATE NEW RESTAURANT ---------
    r = Restaurant(
        vendor_id=vendor_id,
        name=name,
        address=address,
        description=description,
        is_nightlife=is_nightlife
    )
    db.session.add(r)
    db.session.commit()

    # Banner
    if is_multipart and file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        new_name = f"rest_{r.id}_{filename}".replace(" ", "_")
        path = os.path.join(app.config["UPLOAD_FOLDER"], new_name)
        file.save(path)
        r.banner_image = f"/uploads/{new_name}"
    elif base64_banner:
        r.banner_image = base64_banner

    db.session.commit()

    # ✅ save config + offers for JSON
    if not is_multipart:
        _save_restaurant_config_and_offers(r.id, delivery_charge, packing_charge, offers)

    return jsonify({"success": True, "message": "Restaurant created", "restaurant_id": r.id})
def _save_restaurant_config_and_offers(restaurant_id, delivery_charge, packing_charge, offers):
    """Helper: upsert RestaurantConfig and replace RestaurantOffer list."""

    # Config
    cfg = RestaurantConfig.query.filter_by(restaurant_id=restaurant_id).first()
    if not cfg:
        cfg = RestaurantConfig(restaurant_id=restaurant_id)
    cfg.delivery_charge = max(0, int(delivery_charge or 0))
    cfg.packing_charge = max(0, int(packing_charge or 0))
    db.session.add(cfg)

    # Offers: clear old + insert new
    RestaurantOffer.query.filter_by(restaurant_id=restaurant_id).delete()
    for o in offers:
        try:
            min_amount = int(o.get("min_amount") or o.get("min") or 0)
            percent = int(o.get("percent") or o.get("off") or 0)
        except Exception:
            continue

        if min_amount <= 0 or percent <= 0:
            continue

        ro = RestaurantOffer(
            restaurant_id=restaurant_id,
            min_amount=min_amount,
            percent=percent
        )
        db.session.add(ro)

    db.session.commit()

@app.route("/api/vendor/restaurants/<int:vendor_id>", methods=["GET"])
def list_vendor_restaurants(vendor_id):
    restaurants = Restaurant.query.filter_by(vendor_id=vendor_id, active=True).all()
    prefix = "data:image/jpeg;base64,"
    result = []

    for r in restaurants:
        cfg = RestaurantConfig.query.filter_by(restaurant_id=r.id).first()
        offers = RestaurantOffer.query.filter_by(restaurant_id=r.id).all()

        result.append({
            "id": r.id,
            "name": r.name,
            "address": r.address,
            "description": r.description,
            "is_nightlife": r.is_nightlife,
            "banner_image": (
                prefix + r.banner_image
                if r.banner_image and not r.banner_image.startswith("data:image")
                else r.banner_image
            ) or None,
            # ✅ NEW
            "delivery_charge": cfg.delivery_charge if cfg else 0,
            "packing_charge": cfg.packing_charge if cfg else 0,
            "offers": [
                {"id": o.id, "min_amount": o.min_amount, "percent": o.percent}
                for o in offers
            ],
        })

    return jsonify(result)


# ------------------ MENU ITEMS ------------------

@app.route("/api/vendor/restaurants/<int:restaurant_id>/menu-item", methods=["POST"])
def add_menu_item(restaurant_id):
    data = get_data()
    r = Restaurant.query.get(restaurant_id)
    if not r:
        return jsonify({"success": False, "message": "Restaurant not found"}), 404

    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"success": False, "message": "name required"}), 400

    try:
        price = int(str(data.get("price")))
    except Exception:
        return jsonify({"success": False, "message": "Invalid price"}), 400

    try:
        offer_percent = int(data.get("offer_percent") or 0)
    except Exception:
        offer_percent = 0

    item = MenuItem(
        restaurant_id=restaurant_id,
        name=name,
        description=(data.get("description") or "").strip(),
        price=price,
        category=(data.get("category") or "").strip(),
        food_type=(data.get("food_type") or "").strip(),
        available=bool(data.get("available")) if data.get("available") is not None else True,
        image_url=(data.get("image_url") or "").strip() or None
    )
    db.session.add(item)
    db.session.commit()

    # ✅ optional offer
    if offer_percent > 0:
        mo = MenuOffer(menu_item_id=item.id, percent=offer_percent)
        db.session.add(mo)
        db.session.commit()

    return jsonify({"success": True, "message": "Menu item added", "item_id": item.id})

@app.route("/api/vendor/restaurants/<int:restaurant_id>/menu", methods=["GET"])
def list_menu_items(restaurant_id):
    items = MenuItem.query.filter_by(restaurant_id=restaurant_id).all()
    result = []
    for i in items:
        mo = MenuOffer.query.filter_by(menu_item_id=i.id).first()
        offer_percent = mo.percent if mo else 0
        result.append({
            "id": i.id,
            "name": i.name,
            "description": i.description,
            "price": i.price,
            "category": i.category,
            "food_type": i.food_type,
            "available": i.available,
            "image_url": i.image_url,
            "offer_percent": offer_percent,
        })
    return jsonify(result)


@app.route("/api/vendor/menu-item/<int:item_id>", methods=["DELETE"])
def delete_menu_item(item_id):
    item = MenuItem.query.get(item_id)
    if not item:
        return jsonify({"success": False, "message": "Item not found"}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({"success": True})

@app.route("/api/vendor/menu-item/<int:item_id>", methods=["PUT"])
def update_menu_item(item_id):
    data = get_data()
    item = MenuItem.query.get(item_id)
    if not item:
        return jsonify({"success": False, "message": "Item not found"}), 404

    if "name" in data:
        item.name = (data.get("name") or item.name).strip()
    if "description" in data:
        item.description = (data.get("description") or item.description or "").strip()
    if "price" in data:
        try:
            item.price = int(str(data.get("price")))
        except Exception:
            pass
    if "category" in data:
        item.category = (data.get("category") or item.category or "").strip()
    if "food_type" in data:
        item.food_type = (data.get("food_type") or item.food_type or "").strip()
    if "available" in data:
        item.available = bool(data.get("available"))
    if "image_url" in data:
        item.image_url = (data.get("image_url") or "").strip() or item.image_url

    # ✅ Offer update
    if "offer_percent" in data:
        try:
            offer_percent = int(data.get("offer_percent") or 0)
        except Exception:
            offer_percent = 0

        mo = MenuOffer.query.filter_by(menu_item_id=item.id).first()
        if offer_percent > 0:
            if not mo:
                mo = MenuOffer(menu_item_id=item.id, percent=offer_percent)
                db.session.add(mo)
            else:
                mo.percent = offer_percent
        else:
            # remove offer if set to 0
            if mo:
                db.session.delete(mo)

    db.session.commit()
    return jsonify({"success": True, "message": "Menu item updated"})


@app.route("/api/vendor/restaurants/<int:restaurant_id>/qr-tables", methods=["POST"])
def create_qr_table(restaurant_id):
    """
    Create a QR table.
    Body:
    {
      "table_label": "T1" or "VIP-3",
      "qr_code_id": "optional-custom-code"
    }
    """
    data = get_data()
    r = Restaurant.query.get(restaurant_id)
    if not r:
        return jsonify({"success": False, "message": "Restaurant not found"}), 404

    table_label = (data.get("table_label") or "").strip()
    if not table_label:
        return jsonify({"success": False, "message": "table_label required"}), 400

    qr_code_id = (data.get("qr_code_id") or "").strip()
    if not qr_code_id:
        # auto-generate unique
        while True:
            qr_code_id = _generate_qr_code_id()
            if not QRTable.query.filter_by(qr_code_id=qr_code_id).first():
                break
    else:
        # ensure unique if custom code
        if QRTable.query.filter_by(qr_code_id=qr_code_id).first():
            return jsonify({"success": False, "message": "qr_code_id already used"}), 400

    qt = QRTable(
        restaurant_id=restaurant_id,
        table_label=table_label,
        qr_code_id=qr_code_id,
        active=True
    )
    db.session.add(qt)
    db.session.commit()

    # Frontend can generate QR using this link:
    #   https://your-domain/qr?code=<qr_code_id>
    return jsonify({
        "success": True,
        "message": "QR table created",
        "qr_table": {
            "id": qt.id,
            "table_label": qt.table_label,
            "qr_code_id": qt.qr_code_id
        }
    })


@app.route("/api/vendor/restaurants/<int:restaurant_id>/qr-tables", methods=["GET"])
def list_qr_tables(restaurant_id):
    tables = QRTable.query.filter_by(restaurant_id=restaurant_id).all()
    return jsonify([
        {
            "id": t.id,
            "table_label": t.table_label,
            "qr_code_id": t.qr_code_id,
            "active": t.active
        } for t in tables
    ])


# =====================================================
#            USER SIDE: FOOD RESTAURANTS LIST
# =====================================================

@app.route("/food/restaurants", methods=["GET"])
def food_restaurants():
    restaurants = Restaurant.query.filter_by(active=True).all()
    prefix = "data:image/jpeg;base64,"

    result = []
    for r in restaurants:
        cfg = RestaurantConfig.query.filter_by(restaurant_id=r.id).first()
        offers = RestaurantOffer.query.filter_by(restaurant_id=r.id).all()

        result.append({
            "id": r.id,
            "vendor_id": r.vendor_id,
            "name": r.name,
            "address": r.address,
            "description": r.description,
            "is_nightlife": r.is_nightlife,
            "banner_image": (
                prefix + r.banner_image
                if r.banner_image and not r.banner_image.startswith("data:image")
                else r.banner_image
            ) or None,
            "delivery_charge": cfg.delivery_charge if cfg else 0,
            "packing_charge": cfg.packing_charge if cfg else 0,
            "offers": [
                {"id": o.id, "min_amount": o.min_amount, "percent": o.percent}
                for o in offers
            ],
        })
    return jsonify(result)


# =====================================================
#               QR MENU + ORDER (USER FLOW)
# =====================================================

@app.route("/api/qr/menu/<string:qr_code_id>", methods=["GET"])
def qr_menu(qr_code_id):
    """
    User scans QR → frontend calls this.
    Returns restaurant + table info + menu.
    """
    qt = QRTable.query.filter_by(qr_code_id=qr_code_id, active=True).first()
    if not qt:
        return jsonify({"success": False, "message": "QR not found / inactive"}), 404

    r = Restaurant.query.get(qt.restaurant_id)
    if not r:
        return jsonify({"success": False, "message": "Restaurant not found"}), 404

    items = MenuItem.query.filter_by(restaurant_id=r.id, available=True).all()
    return jsonify({
        "success": True,
        "restaurant": {
            "id": r.id,
            "name": r.name,
            "address": r.address,
            "description": r.description,
            "banner_image": r.banner_image
        },
        "table": {
            "id": qt.id,
            "table_label": qt.table_label,
            "qr_code_id": qt.qr_code_id
        },
        "menu": [
            {
                "id": i.id,
                "name": i.name,
                "description": i.description,
                "price": i.price,
                "category": i.category,
                "food_type": i.food_type,
                "image_url": i.image_url
            } for i in items
        ]
    })


@app.route("/api/qr/order", methods=["POST"])
def qr_place_order():
    """
    Body:
    {
      "qr_code_id": "<from QR>",
      "items": [
        { "menu_item_id": 1, "qty": 2 },
        ...
      ],
      "user_name": "optional",
      "user_contact": "optional"
    }

    It finds restaurant & vendor from qr_code_id, calculates totals,
    and creates a FoodOrder with status PENDING.
    """
    data = get_data()
    qr_code_id = (data.get("qr_code_id") or "").strip()
    items_req = data.get("items") or []

    if not qr_code_id or not items_req:
        return jsonify({"success": False, "message": "qr_code_id & items required"}), 400

    qt = QRTable.query.filter_by(qr_code_id=qr_code_id, active=True).first()
    if not qt:
        return jsonify({"success": False, "message": "Invalid QR"}), 404

    r = Restaurant.query.get(qt.restaurant_id)
    if not r:
        return jsonify({"success": False, "message": "Restaurant not found"}), 404

    vendor = Vendor.query.get(r.vendor_id)
    if not vendor:
        return jsonify({"success": False, "message": "Vendor not found"}), 404

    # calculate total
    items_final = []
    subtotal = 0
    for item in items_req:
        try:
            mid = int(item.get("menu_item_id"))
            qty = int(item.get("qty") or 1)
        except Exception:
            return jsonify({"success": False, "message": "Invalid item data"}), 400
        m = MenuItem.query.get(mid)
        if not m or not m.available or m.restaurant_id != r.id:
            return jsonify({"success": False, "message": f"Menu item {mid} not available"}), 400
        line_total = m.price * qty
        subtotal += line_total
        items_final.append({
            "menu_item_id": m.id,
            "name": m.name,
            "qty": qty,
            "price": m.price,
            "line_total": line_total
        })

    tax = 0  # you can add GST logic later
    total = subtotal + tax

    fo = FoodOrder(
        vendor_id=vendor.id,
        restaurant_id=r.id,
        qr_table_id=qt.id,
        table_label=qt.table_label,
        items_json=json.dumps(items_final),
        subtotal=subtotal,
        tax=tax,
        total=total,
        status="PENDING",
        payment_status="UNPAID",
        user_name=(data.get("user_name") or "").strip() or None,
        user_contact=(data.get("user_contact") or "").strip() or None
    )
    db.session.add(fo)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Order placed",
        "order": {
            "id": fo.id,
            "restaurant_id": fo.restaurant_id,
            "vendor_id": fo.vendor_id,
            "table_label": fo.table_label,
            "subtotal": fo.subtotal,
            "tax": fo.tax,
            "total": fo.total,
            "status": fo.status
        }
    })


# =====================================================
#         VENDOR: VIEW & UPDATE QR FOOD ORDERS
# =====================================================

@app.route("/api/vendor/orders/qr/<int:vendor_id>", methods=["GET"])
def vendor_qr_orders(vendor_id):
    """
    Used in vendor_order_online.html to show orders coming from QR scan.
    """
    orders = FoodOrder.query.filter_by(vendor_id=vendor_id).order_by(FoodOrder.created_at.desc()).all()
    result = []
    for o in orders:
        try:
            items = json.loads(o.items_json)
        except Exception:
            items = []
        result.append({
            "id": o.id,
            "restaurant_id": o.restaurant_id,
            "table_label": o.table_label,
            "items": items,
            "subtotal": o.subtotal,
            "tax": o.tax,
            "total": o.total,
            "status": o.status,
            "payment_status": o.payment_status,
            "user_name": o.user_name,
            "user_contact": o.user_contact,
            "created_at": o.created_at.isoformat()
        })
    return jsonify(result)


@app.route("/api/vendor/orders/qr/<int:order_id>/status", methods=["POST"])
def update_qr_order_status(order_id):
    """
    Body: { "status": "ACCEPTED" / "PREPARING" / "READY" / "SERVED" / "CANCELLED",
             "payment_status": "PAID" / "UNPAID" (optional) }
    """
    data = get_data()
    status = (data.get("status") or "").strip()
    if not status:
        return jsonify({"success": False, "message": "status required"}), 400

    if status not in ("PENDING", "ACCEPTED", "PREPARING", "READY", "SERVED", "CANCELLED"):
        return jsonify({"success": False, "message": "Invalid status"}), 400

    fo = FoodOrder.query.get(order_id)
    if not fo:
        return jsonify({"success": False, "message": "Order not found"}), 404

    fo.status = status
    if "payment_status" in data:
        ps = (data.get("payment_status") or "").strip()
        if ps in ("PAID", "UNPAID"):
            fo.payment_status = ps

    db.session.commit()
    return jsonify({"success": True})


# =====================================================
#               PAYMENT + BOOKING (RAZORPAY)
# =====================================================

RAZORPAY_KEY_ID = "YOUR_KEY"
RAZORPAY_KEY_SECRET = "YOUR_SECRET"

if razorpay and RAZORPAY_KEY_ID != "YOUR_KEY" and RAZORPAY_KEY_SECRET != "YOUR_SECRET":
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
else:
    razorpay_client = None
    print("INFO: Razorpay not fully configured.")


@app.route("/api/create_order", methods=["POST"])
def create_order():
    if not razorpay_client:
        return jsonify({"status": "failed", "error": "Razorpay not configured"}), 500

    data = get_data()
    try:
        amount = int(str(data.get("amount")))
    except Exception:
        return jsonify({"status": "failed", "error": "Invalid amount"}), 400

    order = razorpay_client.order.create({
        "amount": amount * 100,
        "currency": "INR",
        "payment_capture": 1
    })
    return jsonify(order)


@app.route("/api/verify_payment", methods=["POST"])
def verify_payment():
    if not razorpay_client:
        return jsonify({"status": "failed", "error": "Razorpay not configured"}), 500

    data = get_data()
    required = [
        "order_id", "payment_id", "signature",
        "vendor_id", "club_id", "table_type", "amount",
        "user_email", "user_name"
    ]
    for k in required:
        if k not in data:
            return jsonify({"status": "failed", "error": f"Missing field: {k}"}), 400

    try:
        razorpay_client.utility.verify_payment_signature({
            "razorpay_order_id": data["order_id"],
            "razorpay_payment_id": data["payment_id"],
            "razorpay_signature": data["signature"]
        })
    except Exception as e:
        print("PAYMENT SIGNATURE ERROR:", e)
        return jsonify({"status": "failed", "error": "Invalid payment signature"}), 400

    table_id = data.get("table_id")
    b = Booking(
        vendor_id=int(data["vendor_id"]),
        club_id=int(data["club_id"]),
        table_id=int(table_id) if table_id else None,
        table_type=data["table_type"],
        amount=int(str(data["amount"])),
        payment_id=data["payment_id"],
        status="CONFIRMED",
        user_email=data["user_email"],
        user_name=data["user_name"]
    )
    db.session.add(b)

    # decrease free_tables if table_id provided
    if table_id:
        t = Table.query.get(int(table_id))
        if t and t.free_tables > 0:
            t.free_tables -= 1

    db.session.commit()

    return jsonify({
        "status": "success",
        "booking": {
            "id": b.id,
            "vendor_id": b.vendor_id,
            "club_id": b.club_id,
            "table_type": b.table_type,
            "amount": b.amount,
            "payment_id": b.payment_id,
            "status": b.status,
            "user_email": b.user_email,
            "user_name": b.user_name
        }
    })


@app.route("/vendor/bookings/<int:vendor_id>")
def vendor_bookings(vendor_id):
    bookings = Booking.query.filter_by(vendor_id=vendor_id).all()
    return jsonify([
        {
            "id": b.id,
            "club_id": b.club_id,
            "table_id": b.table_id,
            "table_type": b.table_type,
            "amount": b.amount,
            "payment_id": b.payment_id,
            "status": b.status,
            "user_email": b.user_email,
            "user_name": b.user_name,
            "created_at": b.created_at.isoformat()
        }
        for b in bookings
    ])


# =====================================================
#             DELIVERY ASSIGNMENTS (BACKEND)
# =====================================================

@app.route("/api/admin/assign-delivery", methods=["POST"])
def admin_assign_delivery():
    """
    Admin (or system) assigns a booking to a delivery partner.
    Body: { "booking_id": ..., "partner_id": ... }
    """
    data = get_data()
    try:
        booking_id = int(data.get("booking_id"))
        partner_id = int(data.get("partner_id"))
    except Exception:
        return jsonify({"success": False, "message": "booking_id/partner_id invalid"}), 400

    if not Booking.query.get(booking_id):
        return jsonify({"success": False, "message": "Booking not found"}), 404
    if not DeliveryPartner.query.get(partner_id):
        return jsonify({"success": False, "message": "Partner not found"}), 404

    da = DeliveryAssignment(booking_id=booking_id, partner_id=partner_id, status="ASSIGNED")
    db.session.add(da)
    db.session.commit()

    return jsonify({"success": True, "assignment_id": da.id})


@app.route("/api/delivery/assignments/<int:partner_id>")
def delivery_assignments(partner_id):
    assigns = DeliveryAssignment.query.filter_by(partner_id=partner_id).all()
    result = []
    for a in assigns:
        b = Booking.query.get(a.booking_id)
        club = Club.query.get(b.club_id) if b else None
        result.append({
            "assignment_id": a.id,
            "booking_id": a.booking_id,
            "status": a.status,
            "assigned_at": a.assigned_at.isoformat(),
            "updated_at": a.updated_at.isoformat(),
            "booking": {
                "user_name": b.user_name if b else None,
                "user_email": b.user_email if b else None,
                "amount": b.amount if b else None,
                "club_name": club.club_name if club else None,
            }
        })
    return jsonify(result)


@app.route("/api/delivery/assignments/<int:assignment_id>/status", methods=["POST"])
def update_assignment_status(assignment_id):
    data = get_data()
    status = (data.get("status") or "").strip()  # ASSIGNED / PICKED / DELIVERED / CANCELLED

    if status not in ("ASSIGNED", "PICKED", "DELIVERED", "CANCELLED"):
        return jsonify({"success": False, "message": "Invalid status"}), 400

    a = DeliveryAssignment.query.get(assignment_id)
    if not a:
        return jsonify({"success": False, "message": "Assignment not found"}), 404

    a.status = status
    a.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({"success": True})


# =====================================================
#                 ADMIN OVERVIEW APIs
# =====================================================

@app.route("/api/admin/overview")
def admin_overview():
    user_count = User.query.count()
    vendor_count = Vendor.query.count()
    club_count = Club.query.count()
    booking_count = Booking.query.count()
    partner_count = DeliveryPartner.query.count()
    return jsonify({
        "users": user_count,
        "vendors": vendor_count,
        "clubs": club_count,
        "bookings": booking_count,
        "delivery_partners": partner_count
    })


@app.route("/api/admin/vendors")
def admin_vendors():
    vendors = Vendor.query.all()
    return jsonify([
        {
            "id": v.id,
            "restaurant_name": v.restaurant_name,
            "owner_name": v.owner_name,
            "email": v.email,
            "phone": v.phone,
            "address": v.address
        } for v in vendors
    ])


@app.route("/api/admin/delivery-partners")
def admin_delivery_partners():
    partners = DeliveryPartner.query.all()
    return jsonify([
        {
            "id": p.id,
            "name": p.name,
            "email": p.email,
            "phone": p.phone,
            "vehicle_type": p.vehicle_type,
            "status": p.status
        } for p in partners
    ])


# =====================================================
#                 SERVE UPLOADED IMAGES
# =====================================================
# =====================================================
#  BRIDGE FOR vendor_table.html (email -> vendor)
# =====================================================

@app.post("/api/rest/vendor/by_email")
def rest_vendor_by_email():
    """
    Adapter for vendor_table.html.

    Request body: { "email": "...", "restaurant_name": "optional" }
    Returns: { success, vendor, settings, location, banner, stats }
    """
    data = request.get_json(force=True) or {}
    email = (data.get("email") or "").strip().lower()

    if not email:
        return jsonify({"success": False, "message": "Email required"}), 400

    vendor = Vendor.query.filter(
        db.func.lower(Vendor.email) == email
    ).first()

    if not vendor:
        return jsonify({"success": False, "message": "Vendor not found"}), 404

    # ✅ use TBVendorSettings instead of dummy data
    settings_model = _get_settings_for_vendor(vendor.id)
    upcoming = TBBooking.query.filter_by(
        vendor_id=vendor.id,
        status="upcoming"
    ).count()

    return jsonify({
        "success": True,
        "vendor": {
            "id": vendor.id,
            "email": vendor.email,
            "restaurant_name": vendor.restaurant_name,
            "owner_name": vendor.owner_name,
            "phone": vendor.phone,
            "address": vendor.address,
        },
        "settings": {
            "maxAdvanceDays": settings_model.max_advance_days,
            "cancelBeforeHrs": settings_model.cancel_before_hrs,
        },
        "location": {
            "addr1": settings_model.addr1,
            "addr2": settings_model.addr2,
            "city": settings_model.city,
            "state": settings_model.state,
            "pincode": settings_model.pincode,
        },
        "banner": settings_model.banner_url,
        "stats": {
            "upcomingBookings": upcoming
        },
    })



@app.route("/uploads/<path:filename>")
def serve_uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# ⭐ NEW: upload endpoint for menu item images
@app.post("/api/upload/menu-image")
def upload_menu_image():
    """
    Accepts a single image file and returns a URL like /uploads/xxx.png
    Used by vendor_use.html when you choose an image from gallery.
    """
    if "image" not in request.files:
        return jsonify({"success": False, "message": "No image file"}), 400

    file = request.files["image"]
    if not file or file.filename == "":
        return jsonify({"success": False, "message": "Empty filename"}), 400

    if not allowed_file(file.filename):
        return jsonify({"success": False, "message": "Invalid file type"}), 400

    filename = secure_filename(file.filename)
    new_name = f"menu_{int(datetime.utcnow().timestamp())}_{filename}".replace(" ", "_")
    path = os.path.join(app.config["UPLOAD_FOLDER"], new_name)
    file.save(path)

    url = f"/uploads/{new_name}"
    return jsonify({"success": True, "url": url})


@app.post("/api/vendor/getByEmail")
def api_vendor_get_by_email():
    data = request.get_json()
    email = (data.get("email") or "").strip().lower()

    if not email:
        return jsonify({"success": False, "message": "Email required"}), 400

    vendor = Vendor.query.filter(
        db.func.lower(Vendor.email) == email
    ).first()

    if not vendor:
        return jsonify({"success": False, "message": "Vendor not found"}), 404

    return jsonify({
        "success": True,
        "vendor": {
            "id": vendor.id,
            "email": vendor.email,
            "restaurant_name": vendor.restaurant_name,
            "owner_name": vendor.owner_name,
            "phone": vendor.phone,
            "address": vendor.address
        }
    })

@app.post("/api/order/place")
def place_delivery_order():
    try:
        data = request.get_json(force=True)
    except Exception as e:
        print("JSON error:", e)
        return jsonify({"success": False, "message": "Invalid JSON"}), 400

    restaurant_id = data.get("restaurant_id")
    vendor_id = data.get("vendor_id")
    items = data.get("items", [])
    total_from_frontend = data.get("total")   # not trusted fully
    coupon_discount = data.get("coupon_discount", 0) or 0
    payment_method = data.get("payment_method")
    address = data.get("address")

    if not restaurant_id or not vendor_id or not items:
        return jsonify({"success": False, "message": "Missing required fields"}), 400

    if not address:
        return jsonify({"success": False, "message": "Address missing"}), 400

    required_addr = ["name", "phone", "line1", "city", "state", "pincode"]
    for f in required_addr:
        if not address.get(f):
            return jsonify({"success": False, "message": f"Address {f} missing"}), 400

    # Fetch restaurant + config + offers
    try:
        restaurant_id_int = int(restaurant_id)
        vendor_id_int = int(vendor_id)
    except Exception:
        return jsonify({"success": False, "message": "Invalid vendor_id/restaurant_id"}), 400

    rest = Restaurant.query.get(restaurant_id_int)
    if not rest:
        return jsonify({"success": False, "message": "Restaurant not found"}), 404

    cfg = RestaurantConfig.query.filter_by(restaurant_id=rest.id).first()
    offer_rows = RestaurantOffer.query.filter_by(restaurant_id=rest.id).all()

    # -----------------------------
    # SUBTOTAL: sum of item prices
    # -----------------------------
    subtotal = 0
    try:
        for i in items:
            price = int(i.get("price", 0))
            qty = int(i.get("qty", 0))
            subtotal += price * qty
    except Exception as e:
        print("Subtotal calc error:", e)
        try:
            subtotal = int(total_from_frontend) + int(coupon_discount)
        except Exception:
            subtotal = int(total_from_frontend or 0)

    # -----------------------------
    # RESTAURANT OFFERS (UNLIMITED)
    # -----------------------------
    # pick the highest percent whose min_amount <= subtotal
    offer_discount = 0
    best_percent = 0
    for o in offer_rows:
        if subtotal >= (o.min_amount or 0):
            if (o.percent or 0) > best_percent:
                best_percent = o.percent or 0

    if best_percent > 0:
        offer_discount = subtotal * best_percent // 100

    # -----------------------------
    # DELIVERY + PACKING
    # -----------------------------
    delivery_fee = cfg.delivery_charge if cfg else 0
    packing_fee = cfg.packing_charge if cfg else 0

    # total discount = coupon + restaurant offer
    total_discount = int(coupon_discount) + int(offer_discount)

    # FINAL TOTAL
    grand_total = subtotal + delivery_fee + packing_fee - total_discount
    if grand_total < 0:
        grand_total = 0

    order = DeliveryOrder(
        vendor_id=vendor_id_int,
        restaurant_id=restaurant_id_int,
        items_json=json.dumps(items),

        subtotal=int(subtotal),
        gst=0,
        discount=int(total_discount),
        total=int(grand_total),

        payment_method=payment_method,
        payment_status="UNPAID",

        user_name=address.get("name"),
        user_phone=address.get("phone"),

        address_line1=address.get("line1"),
        address_line2=address.get("line2"),
        landmark=address.get("landmark"),
        city=address.get("city"),
        state=address.get("state"),
        pincode=address.get("pincode"),
        country="India",

        gps_lat=address.get("lat"),
        gps_lng=address.get("lng"),

        status="PENDING"
    )

    db.session.add(order)
    db.session.commit()

    return jsonify({
        "success": True,
        "order_id": order.id,
        "computed_total": grand_total,
        "subtotal": subtotal,
        "delivery_fee": delivery_fee,
        "packing_fee": packing_fee,
        "offer_discount": int(offer_discount),
        "coupon_discount": int(coupon_discount),
        "total_discount": int(total_discount)
    })




@app.get("/api/orders/user/<phone>")
def get_user_orders(phone):
    try:
        # normalize phone (remove spaces etc.)
        phone = (phone or "").strip()

        # fetch all orders for this phone
        orders = (
            DeliveryOrder.query
            .filter_by(user_phone=phone)
            .order_by(DeliveryOrder.id.desc())
            .all()
        )

        result = []
        for o in orders:
            # get restaurant name safely
            restaurant_name = "Unknown"
            try:
                # if you have relationship DeliveryOrder.restaurant
                if hasattr(o, "restaurant") and o.restaurant:
                    restaurant_name = o.restaurant.name
                else:
                    r = Restaurant.query.get(o.restaurant_id)
                    if r:
                        restaurant_name = r.name
            except Exception:
                restaurant_name = "Unknown"

            try:
                items = json.loads(o.items_json or "[]")
            except Exception:
                items = []

            result.append({
                "id": o.id,
                "restaurant_id": o.restaurant_id,
                "restaurant_name": restaurant_name,
                "items": items,
                "total": o.total,
                "subtotal": o.subtotal,
                "gst": o.gst,
                "discount": o.discount,
                "status": o.status,
                "payment_method": o.payment_method,
                "created_at": (
                    o.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    if o.created_at else None
                )
            })

        return jsonify({"success": True, "orders": result})

    except Exception as e:
        print("Order fetch error:", e)
        return jsonify({"success": False, "message": "Error fetching orders"}), 500


@app.get("/api/order/<int:order_id>")
def get_single_order(order_id):
    """
    Unified order details endpoint for delivery orders.
    Used by track_order page.
    """
    try:
        # Fetch order
        order = DeliveryOrder.query.get(order_id)
        if not order:
            return jsonify({"success": False, "message": "Order not found"}), 404

        # Fetch restaurant name (safe)
        restaurant_name = "Restaurant"
        try:
            r = Restaurant.query.get(order.restaurant_id)
            if r:
                restaurant_name = r.name
        except Exception:
            restaurant_name = "Restaurant"

        # Parse items JSON safely
        try:
            items = json.loads(order.items_json or "[]")
        except Exception:
            items = []

        return jsonify({
            "success": True,
            "order": {
                "id": order.id,
                "restaurant_id": order.restaurant_id,
                "restaurant_name": restaurant_name,

                "vendor_id": order.vendor_id,

                # Items
                "items": items,

                # Price
                "subtotal": order.subtotal,
                "gst": order.gst,
                "discount": order.discount,
                "total": order.total,

                # Payment
                "payment_method": order.payment_method,
                "payment_status": order.payment_status,

                # Customer
                "user_name": order.user_name,
                "user_phone": order.user_phone,

                # Address
                "address": {
                    "name": order.user_name,
                    "phone": order.user_phone,
                    "line1": order.address_line1,
                    "line2": order.address_line2,
                    "landmark": order.landmark,
                    "city": order.city,
                    "state": order.state,
                    "pincode": order.pincode,
                    "country": order.country,
                    "lat": order.gps_lat,
                    "lng": order.gps_lng
                },

                # Status
                "status": order.status,

                # Created time
                "created_at": (
                    order.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    if order.created_at else None
                )
            }
        })
    except Exception as e:
        print("Fetch single order error:", e)
        return jsonify({"success": False, "message": "Error fetching order"}), 500


# ---------- VENDOR: DELIVERY ORDERS LIST + STATUS UPDATE ----------

@app.get("/api/vendor/delivery-orders/<int:vendor_id>")
def vendor_delivery_orders(vendor_id):
    """
    Vendor panel: list all delivery orders for this vendor.
    Used by vendor_use.html -> loadDeliveryOrders()
    """
    orders = (
        DeliveryOrder.query
        .filter_by(vendor_id=vendor_id)
        .order_by(DeliveryOrder.created_at.desc())
        .all()
    )

    result = []
    for o in orders:
        try:
            items = json.loads(o.items_json or "[]")
        except Exception:
            items = []

        result.append({
            "id": o.id,
            "vendor_id": o.vendor_id,
            "restaurant_id": o.restaurant_id,
            "user_name": o.user_name,
            "user_phone": o.user_phone,
            "total": o.total,
            "status": o.status,
            "payment_method": o.payment_method,
            "payment_status": o.payment_status,
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "items": items,
            "address": {
                "line1": o.address_line1,
                "line2": o.address_line2,
                "landmark": o.landmark,
                "city": o.city,
                "state": o.state,
                "pincode": o.pincode,
            },
        })

    return jsonify(result)


@app.post("/api/vendor/delivery-orders/<int:order_id>/status")
def update_delivery_status(order_id):
    """
    Vendor updates a single delivery order status.
    Body: { "status": "PENDING" | "PREPARING" | "OUT_FOR_DELIVERY" | "DELIVERED" | "CANCELLED" }
    """
    data = get_data()
    status = (data.get("status") or "").strip().upper()

    allowed = ["PENDING", "PREPARING", "OUT_FOR_DELIVERY", "DELIVERED", "CANCELLED"]
    if status not in allowed:
        return jsonify({"success": False, "message": "Invalid status"}), 400

    o = DeliveryOrder.query.get(order_id)
    if not o:
        return jsonify({"success": False, "message": "Order not found"}), 404

    o.status = status
    db.session.commit()

    return jsonify({"success": True})

# =====================================================
#          TABLE BOOKING — EXTRA MODELS
#          (USED BY vendor_table.html)
# =====================================================

class TBVendorSettings(db.Model):
    """
    Per-vendor table-booking config + banner + address
    """
    __tablename__ = "tb_vendor_settings"
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, nullable=False, unique=True)

    max_advance_days = db.Column(db.Integer, default=365)
    cancel_before_hrs = db.Column(db.Integer, default=2)

    banner_url = db.Column(db.String(300))

    addr1 = db.Column(db.String(300))
    addr2 = db.Column(db.String(300))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    pincode = db.Column(db.String(20))


class TBTableType(db.Model):
    """
    A type of table: 4-seater, VIP etc
    """
    __tablename__ = "tb_table_types"
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, nullable=False)

    name = db.Column(db.String(150), nullable=False)
    seats = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Integer, nullable=False, default=1)
    price = db.Column(db.Integer, nullable=False, default=0)
    cancel_hrs = db.Column(db.Integer, nullable=False, default=2)

    time_start = db.Column(db.String(5), default="10:00")  # "HH:MM"
    time_end = db.Column(db.String(5), default="23:00")


class TBTable(db.Model):
    """
    Individual table for a given type.
    status: free / reserved / unavailable
    """
    __tablename__ = "tb_tables"
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, nullable=False)
    type_id = db.Column(db.Integer, nullable=False)
    num = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="free")


class TBSlot(db.Model):
    """
    Time slots (Lunch, Dinner etc)
    """
    __tablename__ = "tb_slots"
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    start_time = db.Column(db.String(5), nullable=False)  # "HH:MM"
    end_time = db.Column(db.String(5), nullable=False)    # "HH:MM"


class TBBooking(db.Model):
    """
    Simple booking entity for dashboard simulator.
    """
    __tablename__ = "tb_bookings"
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, nullable=False)
    type_id = db.Column(db.Integer, nullable=False)
    slot_id = db.Column(db.Integer, nullable=False)

    date = db.Column(db.String(20), nullable=False)  # "YYYY-MM-DD"
    customer = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(50))
    table_numbers = db.Column(db.String(300))        # e.g. "1,2,5"
    price = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default="upcoming")  # upcoming / cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# =====================================================
#          TABLE BOOKING — HELPERS
# =====================================================

def _get_vendor_or_404(vendor_id: int):
    v = Vendor.query.get(vendor_id)
    if not v:
        return None
    return v


def _get_settings_for_vendor(vendor_id: int) -> TBVendorSettings:
    s = TBVendorSettings.query.filter_by(vendor_id=vendor_id).first()
    if not s:
        s = TBVendorSettings(vendor_id=vendor_id, max_advance_days=365, cancel_before_hrs=2)
        db.session.add(s)
        db.session.commit()
    return s


def _format_12h(time_str: str) -> str:
    """
    "HH:MM" -> "h:MM AM/PM"
    """
    try:
        h, m = map(int, time_str.split(":"))
        period = "PM" if h >= 12 else "AM"
        h12 = h % 12
        if h12 == 0:
            h12 = 12
        return f"{h12}:{m:02d} {period}"
    except Exception:
        return time_str or ""


# =====================================================
#          TABLE BOOKING — VENDOR + SETTINGS
# =====================================================


@app.get("/api/rest/vendor/me")
def tb_vendor_me():
    vendor_id = request.args.get("vendor_id", type=int)
    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400

    v = _get_vendor_or_404(vendor_id)
    if not v:
        return jsonify({"success": False, "message": "Vendor not found"}), 404

    s = _get_settings_for_vendor(vendor_id)
    upcoming = TBBooking.query.filter_by(vendor_id=vendor_id, status="upcoming").count()

    return jsonify({
        "success": True,
        "vendor": {
            "id": v.id,
            "restaurant_name": v.restaurant_name,
            "owner_name": v.owner_name,
            "email": v.email,
            "phone": v.phone,
            "address": v.address
        },
        "settings": {
            "maxAdvanceDays": s.max_advance_days,
            "cancelBeforeHrs": s.cancel_before_hrs
        },
        "location": {
            "addr1": s.addr1,
            "addr2": s.addr2,
            "city": s.city,
            "state": s.state,
            "pincode": s.pincode
        },
        "banner": s.banner_url,
        "stats": {
            "upcomingBookings": upcoming
        }
    })


@app.post("/api/rest/settings")
def tb_save_settings():
    vendor_id = request.args.get("vendor_id", type=int)
    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400
    s = _get_settings_for_vendor(vendor_id)
    data = request.get_json() or {}
    s.max_advance_days = int(data.get("maxAdvanceDays") or 365)
    s.cancel_before_hrs = int(data.get("cancelBeforeHrs") or 2)
    db.session.commit()
    return jsonify({"success": True})


@app.post("/api/rest/location")
def tb_save_location():
    vendor_id = request.args.get("vendor_id", type=int)
    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400
    s = _get_settings_for_vendor(vendor_id)
    data = request.get_json() or {}
    s.addr1 = (data.get("addr1") or "").strip()
    s.addr2 = (data.get("addr2") or "").strip()
    s.city = (data.get("city") or "").strip()
    s.state = (data.get("state") or "").strip()
    s.pincode = (data.get("pincode") or "").strip()
    db.session.commit()
    return jsonify({"success": True})


# --------------------- BANNER UPLOAD --------------------

@app.post("/api/rest/banner")
def tb_upload_banner():
    vendor_id = request.args.get("vendor_id", type=int)
    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400

    if "banner" not in request.files:
        return jsonify({"success": False, "message": "No banner file"}), 400

    file = request.files["banner"]
    if not file or file.filename == "":
        return jsonify({"success": False, "message": "Empty file"}), 400

    if not allowed_file(file.filename):
        return jsonify({"success": False, "message": "Invalid file type"}), 400

    filename = secure_filename(file.filename)
    new_name = f"tb_banner_{vendor_id}_{int(datetime.utcnow().timestamp())}_{filename}".replace(" ", "_")
    path = os.path.join(app.config["UPLOAD_FOLDER"], new_name)
    file.save(path)

    s = _get_settings_for_vendor(vendor_id)
    s.banner_url = f"/uploads/{new_name}"
    db.session.commit()

    return jsonify({"success": True, "bannerUrl": s.banner_url})


@app.delete("/api/rest/banner")
def tb_delete_banner():
    vendor_id = request.args.get("vendor_id", type=int)
    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400
    s = _get_settings_for_vendor(vendor_id)
    s.banner_url = None
    db.session.commit()
    return jsonify({"success": True})
    

# =====================================================
#          TABLE BOOKING — TYPES & TABLES
# =====================================================

@app.get("/api/rest/types")
def tb_get_types():
    vendor_id = request.args.get("vendor_id", type=int)
    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400

    types = TBTableType.query.filter_by(vendor_id=vendor_id).all()
    result = []
    for t in types:
        free_count = TBTable.query.filter_by(type_id=t.id, status="free").count()
        reserved_count = TBTable.query.filter_by(type_id=t.id, status="reserved").count()
        unavail_count = TBTable.query.filter_by(type_id=t.id, status="unavailable").count()
        display_time = f"{_format_12h(t.time_start)} - {_format_12h(t.time_end)}"
        result.append({
            "id": t.id,
            "name": t.name,
            "seats": t.seats,
            "total": t.total,
            "price": t.price,
            "cancel": t.cancel_hrs,
            "timeStart": t.time_start,
            "timeEnd": t.time_end,
            "displayTime": display_time,
            "freeCount": free_count,
            "reservedCount": reserved_count,
            "unavailCount": unavail_count,
        })

    return jsonify({"success": True, "types": result})


@app.post("/api/rest/types")
def tb_save_type():
    vendor_id = request.args.get("vendor_id", type=int)
    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400

    data = request.get_json() or {}
    type_id = data.get("id")
    name = (data.get("name") or "").strip()
    seats = int(data.get("seats") or 0)
    total = int(data.get("total") or 0)
    price = int(data.get("price") or 0)
    cancel = int(data.get("cancel") or 2)
    time_start = (data.get("timeStart") or "10:00")[:5]
    time_end = (data.get("timeEnd") or "23:00")[:5]
    free_tables = int(data.get("freeTables") or total)

    if not name or seats <= 0 or total <= 0:
        return jsonify({"success": False, "message": "Invalid type data"}), 400

    if type_id:
        # update existing (keep existing tables as-is)
        t = TBTableType.query.filter_by(id=int(type_id), vendor_id=vendor_id).first()
        if not t:
            return jsonify({"success": False, "message": "Type not found"}), 404
        t.name = name
        t.seats = seats
        t.total = total
        t.price = price
        t.cancel_hrs = cancel
        t.time_start = time_start
        t.time_end = time_end
        db.session.commit()
        return jsonify({"success": True, "id": t.id})

    # create new type + tables
    t = TBTableType(
        vendor_id=vendor_id,
        name=name,
        seats=seats,
        total=total,
        price=price,
        cancel_hrs=cancel,
        time_start=time_start,
        time_end=time_end,
    )
    db.session.add(t)
    db.session.commit()

    free_tables = max(0, min(free_tables, total))
    for num in range(1, total + 1):
        status = "free" if num <= free_tables else "unavailable"
        tb = TBTable(vendor_id=vendor_id, type_id=t.id, num=num, status=status)
        db.session.add(tb)
    db.session.commit()

    return jsonify({"success": True, "id": t.id})


@app.delete("/api/rest/types/<int:type_id>")
def tb_delete_type(type_id):
    vendor_id = request.args.get("vendor_id", type=int)
    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400

    t = TBTableType.query.filter_by(id=type_id, vendor_id=vendor_id).first()
    if not t:
        return jsonify({"success": False, "message": "Type not found"}), 404

    TBTable.query.filter_by(type_id=type_id, vendor_id=vendor_id).delete()
    db.session.delete(t)
    db.session.commit()
    return jsonify({"success": True})

def _parse_table_numbers(table_numbers: str):
    """
    '1,2, 5' -> {1,2,5}
    """
    if not table_numbers:
        return set()
    out = set()
    for part in table_numbers.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.add(int(part))
        except Exception:
            continue
    return out


def _get_reserved_table_nums(vendor_id: int, type_id: int, slot_id: int, date_str: str):
    """
    All table numbers already reserved for this vendor + type + date + slot.
    Only bookings with status='upcoming' are counted.
    """
    if not date_str or not slot_id:
        return set()

    bookings = TBBooking.query.filter_by(
        vendor_id=vendor_id,
        type_id=type_id,
        slot_id=slot_id,
        date=date_str,
        status="upcoming"
    ).all()

    reserved = set()
    for b in bookings:
        reserved |= _parse_table_numbers(b.table_numbers)
    return reserved

@app.get("/api/rest/types/<int:type_id>/tables")
def tb_get_tables_for_type(type_id):
    vendor_id = request.args.get("vendor_id", type=int)
    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400

    # NEW: optional date + slot_id from query string
    date_str = request.args.get("date", type=str)  # "YYYY-MM-DD"
    slot_id = request.args.get("slot_id", type=int)

    t = TBTableType.query.filter_by(id=type_id, vendor_id=vendor_id).first()
    if not t:
        return jsonify({"success": False, "message": "Type not found"}), 404

    tables = TBTable.query.filter_by(
        type_id=type_id,
        vendor_id=vendor_id
    ).order_by(TBTable.num.asc()).all()

    # If date/slot provided → compute reserved tables for that combination.
    reserved_for_slot = _get_reserved_table_nums(
        vendor_id=vendor_id,
        type_id=type_id,
        slot_id=slot_id or 0,
        date_str=date_str or ""
    )

    result = []
    free = reserved = unavail = 0

    for tb in tables:
        # Base status is only used to mark "unavailable".
        # Reservation is now controlled ONLY by TBBooking.
        if tb.status == "unavailable":
            status = "unavailable"
            unavail += 1
        else:
            if tb.num in reserved_for_slot:
                status = "reserved"
                reserved += 1
            else:
                status = "free"
                free += 1

        result.append({
            "id": tb.id,
            "num": tb.num,
            "status": status,
        })

    return jsonify({
        "success": True,
        "tables": result,
        "stats": {
            "free": free,
            "reserved": reserved,
            "unavailable": unavail,
            "total": len(tables),
        }
    })

@app.post("/api/rest/tables/<int:table_id>/toggle")
def tb_toggle_table(table_id):
    vendor_id = request.args.get("vendor_id", type=int)
    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400

    tb = TBTable.query.filter_by(id=table_id, vendor_id=vendor_id).first()
    if not tb:
        return jsonify({"success": False, "message": "Table not found"}), 404

    if tb.status == "reserved":
        # reserved tables are not toggled from dashboard
        return jsonify({"success": False, "message": "Reserved table cannot be toggled"}), 400

    tb.status = "unavailable" if tb.status == "free" else "free"
    db.session.commit()
    return jsonify({"success": True})


@app.post("/api/rest/tables/mark_all_free")
def tb_mark_all_free():
    vendor_id = request.args.get("vendor_id", type=int)
    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400
    data = request.get_json() or {}
    type_id = int(data.get("typeId") or 0)
    if not type_id:
        return jsonify({"success": False, "message": "typeId required"}), 400

    tables = TBTable.query.filter_by(vendor_id=vendor_id, type_id=type_id).all()
    for tb in tables:
        if tb.status != "reserved":
            tb.status = "free"
    db.session.commit()
    return jsonify({"success": True})


# =====================================================
#          TABLE BOOKING — SLOTS
# =====================================================

@app.get("/api/rest/slots")
def tb_get_slots():
    vendor_id = request.args.get("vendor_id", type=int)
    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400

    slots = TBSlot.query.filter_by(vendor_id=vendor_id).all()
    return jsonify({
        "success": True,
        "slots": [
            {
                "id": s.id,
                "name": s.name,
                "start": s.start_time,
                "end": s.end_time
            } for s in slots
        ]
    })


@app.post("/api/rest/slots")
def tb_save_slot():
    vendor_id = request.args.get("vendor_id", type=int)
    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400

    data = request.get_json() or {}
    slot_id = data.get("id")
    name = (data.get("name") or "").strip()
    start = (data.get("start") or "").strip()[:5]
    end = (data.get("end") or "").strip()[:5]

    if not name or not start or not end:
        return jsonify({"success": False, "message": "Invalid slot data"}), 400

    if slot_id:
        s = TBSlot.query.filter_by(id=int(slot_id), vendor_id=vendor_id).first()
        if not s:
            return jsonify({"success": False, "message": "Slot not found"}), 404
        s.name = name
        s.start_time = start
        s.end_time = end
        db.session.commit()
        return jsonify({"success": True, "id": s.id})

    s = TBSlot(vendor_id=vendor_id, name=name, start_time=start, end_time=end)
    db.session.add(s)
    db.session.commit()
    return jsonify({"success": True, "id": s.id})


@app.delete("/api/rest/slots/<int:slot_id>")
def tb_delete_slot(slot_id):
    vendor_id = request.args.get("vendor_id", type=int)
    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400

    s = TBSlot.query.filter_by(id=slot_id, vendor_id=vendor_id).first()
    if not s:
        return jsonify({"success": False, "message": "Slot not found"}), 404
    db.session.delete(s)
    db.session.commit()
    return jsonify({"success": True})


# =====================================================
#          TABLE BOOKING — BOOKINGS
# =====================================================

@app.get("/api/rest/bookings")
def tb_get_bookings():
    vendor_id = request.args.get("vendor_id", type=int)
    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400

    bookings = TBBooking.query.filter_by(vendor_id=vendor_id).all()
    res = []
    for b in bookings:
        t = TBTableType.query.get(b.type_id)
        s = TBSlot.query.get(b.slot_id)
        tables = []
        if b.table_numbers:
            try:
                tables = [int(x) for x in b.table_numbers.split(",") if x.strip()]
            except Exception:
                tables = []
        res.append({
            "id": b.id,
            "customer": b.customer,
            "phone": b.phone,
            "typeName": t.name if t else "",
            "date": b.date,
            "slotName": s.name if s else "",
            "tables": tables,
            "price": b.price,
            "status": b.status,
            "createdAt": b.created_at.isoformat() if b.created_at else None
        })
    return jsonify({"success": True, "bookings": res})


from datetime import datetime, timedelta, date as date_cls
# (you already import datetime at top; just make sure timedelta, date_cls are available)

@app.post("/api/rest/bookings")
def tb_create_booking():
    vendor_id = request.args.get("vendor_id", type=int)
    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400

    data = request.get_json() or {}
    type_id = int(data.get("typeId") or 0)
    slot_id = int(data.get("slotId") or 0)
    date_str = (data.get("date") or "").strip()
    customer = (data.get("customer") or "Guest").strip()
    phone = (data.get("phone") or "").strip()
    count = int(data.get("count") or 1)

    if not type_id or not slot_id or not date_str:
        return jsonify({"success": False, "message": "Missing booking fields"}), 400

    # --------- DATE VALIDATION (no past dates, respect maxAdvanceDays) ----------
    try:
        booking_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        return jsonify({"success": False, "message": "Invalid date format"}), 400

    today = datetime.utcnow().date()
    settings = _get_settings_for_vendor(vendor_id)
    max_days = settings.max_advance_days or 365
    max_date = today + timedelta(days=max_days)

    if booking_date < today:
        return jsonify({"success": False, "message": "You cannot book for past dates"}), 400
    if booking_date > max_date:
        return jsonify({"success": False, "message": "Selected date is beyond allowed advance window"}), 400

    # --------- BASIC ENTITIES ----------
    t = TBTableType.query.filter_by(id=type_id, vendor_id=vendor_id).first()
    s = TBSlot.query.filter_by(id=slot_id, vendor_id=vendor_id).first()
    if not t or not s:
        return jsonify({"success": False, "message": "Type or slot not found"}), 404

    if count <= 0:
        return jsonify({"success": False, "message": "Invalid table count"}), 400

    # --------- AVAILABLE TABLES FOR THIS DATE + SLOT ----------
    already_reserved = _get_reserved_table_nums(
        vendor_id=vendor_id,
        type_id=type_id,
        slot_id=slot_id,
        date_str=date_str
    )

    # Only consider tables that are NOT unavailable and NOT already reserved for this slot/date
    candidate_tables = (
        TBTable.query
        .filter_by(vendor_id=vendor_id, type_id=type_id)
        .filter(TBTable.status != "unavailable")
        .order_by(TBTable.num.asc())
        .all()
    )

    free_tables_for_slot = [tb for tb in candidate_tables if tb.num not in already_reserved]

    if len(free_tables_for_slot) < count:
        return jsonify({"success": False, "message": "Not enough free tables for this slot"}), 400

    selected_tables = free_tables_for_slot[:count]
    table_nums = [tb.num for tb in selected_tables]

    total_price = t.price * count

    # --------- CREATE BOOKING ONLY (NO TBTable.status change) ----------
    b = TBBooking(
        vendor_id=vendor_id,
        type_id=type_id,
        slot_id=slot_id,
        date=date_str,
        customer=customer,
        phone=phone,
        table_numbers=",".join(str(n) for n in table_nums),
        price=total_price,
        status="upcoming"
    )
    db.session.add(b)
    db.session.commit()

    return jsonify({"success": True, "id": b.id})


@app.post("/api/rest/bookings/<int:booking_id>/toggle")
def tb_toggle_booking(booking_id):
    vendor_id = request.args.get("vendor_id", type=int)
    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400

    b = TBBooking.query.filter_by(id=booking_id, vendor_id=vendor_id).first()
    if not b:
        return jsonify({"success": False, "message": "Booking not found"}), 404

    # parse table numbers
    table_nums = []
    if b.table_numbers:
        try:
            table_nums = [int(x) for x in b.table_numbers.split(",") if x.strip()]
        except Exception:
            table_nums = []

    if b.status == "cancelled":
        # restore booking → reserve tables again
        for num in table_nums:
            tb = TBTable.query.filter_by(
                vendor_id=vendor_id, type_id=b.type_id, num=num
            ).first()
            if tb and tb.status != "reserved":
                tb.status = "reserved"
        b.status = "upcoming"
    else:
        # cancel booking → free tables
        for num in table_nums:
            tb = TBTable.query.filter_by(
                vendor_id=vendor_id, type_id=b.type_id, num=num
            ).first()
            if tb and tb.status == "reserved":
                tb.status = "free"
        b.status = "cancelled"

    db.session.commit()
    return jsonify({"success": True})

# -----------------------------------------------------
#  LEGACY ENDPOINT FOR vendor_order_online.html
#  GET /vendor/find/<id>  →  { ok, vendor }
# -----------------------------------------------------
@app.get("/vendor/find/<int:vendor_id>")
def legacy_vendor_find(vendor_id):
    v = Vendor.query.get(vendor_id)
    if not v:
        return jsonify({"ok": False, "message": "Vendor not found"}), 404

    return jsonify({
        "ok": True,
        "vendor": {
            "id": v.id,
            "restaurant_name": v.restaurant_name,
            "owner_name": v.owner_name,
            "email": v.email,
            "phone": v.phone,
            "address": v.address,
            "upi_id": v.upi_id
        }
    })



# =====================================================
#                    RUN SERVER
# =====================================================


# =====================================================
#                    RUN SERVER
# =====================================================

if __name__ == "__main__":
    # Ensure all tables (including TB* table booking ones) exist
    with app.app_context():
        db.create_all()
        print("✅ All DB tables ensured (db.create_all())")

    # host="0.0.0.0" allows you to call from browser on same network
    app.run(host="127.0.0.1", port=5000, debug=True)
