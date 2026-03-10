import os
from dotenv import load_dotenv
import secrets
# Load environment variables from .env file
load_dotenv()
from flask import Flask, request, jsonify, make_response, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from sqlalchemy import text, or_, func
from datetime import datetime, timedelta
import uuid
import json
import random
import smtplib
from email.mime.text import MIMEText


# ========================
# FLASK SETUP
# ========================
app = Flask(__name__)
app.secret_key = "zomaclone_secret_key"
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True,
     allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

# ========================
# DATABASE - PostgreSQL with SQLite fallback
# ========================
# First try PostgreSQL, fall back to SQLite if not available
DATABASE_URI = "sqlite:///instance/zomaclone.db"

# Check if PostgreSQL is available, otherwise use SQLite
def get_database_uri():
    # First check if DATABASE_URI is set in environment
    uri = os.getenv("DATABASE_URI")
    
    # If DATABASE_URI is set, try to use it but test connection first
    if uri:
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(uri, connect_args={"connect_timeout": 3})
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            engine.dispose()
            return uri
        except Exception as e:
            print(f"⚠️ DATABASE_URI set but connection failed: {e}")
            # Continue to SQLite fallback
    
    # Default PostgreSQL URI
    pg_uri = "postgresql+psycopg2://postgres:password@localhost:5432/zomaclone"
    
    # Try to test PostgreSQL connection
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(pg_uri, connect_args={"connect_timeout": 3})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return pg_uri
    except Exception as e:
        print(f"⚠️ PostgreSQL not available: {e}")
        # Use SQLite fallback for development
        base_dir = os.path.dirname(os.path.abspath(__file__))
        sqlite_path = os.path.join(base_dir, "instance", "zomaclone.db")
        os.makedirs(os.path.dirname(sqlite_path), exist_ok=True)
        sqlite_uri = f"sqlite:///{sqlite_path}"
        print(f"📀 Using SQLite fallback: {sqlite_uri}")
        return sqlite_uri

DATABASE_URI = get_database_uri()

if "sqlite" in DATABASE_URI.lower():
    print(" Using SQLite database (Development mode)")
else:
    print(f" Using PostgreSQL database: {DATABASE_URI[:50]}...")


app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
if "sqlite" not in DATABASE_URI:
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True, "pool_recycle": 180, "pool_size": 5, "max_overflow": 10}
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "your_super_secret_key_here")

db = SQLAlchemy(app)

# ========================
# UPLOAD CONFIG
# ========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED_EXT = {"jpg", "jpeg", "png", "webp", "jfif"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT

def get_data():
    data = request.get_json(silent=True)
    if not data:
        data = request.form.to_dict()
    return data or {}

# ========================
# EMAIL CONFIG
# ========================
SMTP_FROM = os.getenv("SMTP_FROM")
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp-relay.brevo.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))

def send_email(to_email, subject, body):
    if not to_email:
        return False
    try:
        msg = MIMEText(body, 'html')
        msg["Subject"] = subject
        msg["From"] = SMTP_FROM
        msg["To"] = to_email
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_FROM, [to_email], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False


def generate_otp():
    return str(secrets.randbelow(9000) + 1000)

# ========================
# COMMON MODELS (Shared)
# ========================
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
    blocked_until = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class UserSession(db.Model):
    __tablename__ = "user_sessions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    token = db.Column(db.String(128), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)

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
    vendor_type = db.Column(db.String(20), default="restaurant")  # "restaurant" or "nightlife"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class EmailLog(db.Model):
    __tablename__ = "email_logs"
    id = db.Column(db.Integer, primary_key=True)
    recipient = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(300), nullable=False)
    body = db.Column(db.Text)
    status = db.Column(db.String(20), default="sent")
    booking_id = db.Column(db.Integer)
    booking_type = db.Column(db.String(20))  # "restaurant" or "nightlife"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ========================
# RESTAURANT BOOKING MODELS
# ========================
class RestVendorConfig(db.Model):
    __tablename__ = "rest_vendor_configs"
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, nullable=False, unique=True)
    max_advance_days = db.Column(db.Integer, default=365)
    cancel_before_hrs = db.Column(db.Integer, default=2)
    addr1 = db.Column(db.String(200))
    addr2 = db.Column(db.String(200))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    pincode = db.Column(db.String(20))
    banner_url = db.Column(db.String(300))

class RestSlot(db.Model):
    __tablename__ = "rest_slots"
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    start = db.Column(db.String(5), nullable=False)
    end = db.Column(db.String(5), nullable=False)

class RestTableType(db.Model):
    __tablename__ = "rest_table_types"
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    seats = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Integer, default=0)
    price = db.Column(db.Integer, default=0)
    cancel = db.Column(db.Integer, default=2)
    time_start = db.Column(db.String(5))
    time_end = db.Column(db.String(5))

class RestTableSeat(db.Model):
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
    date = db.Column(db.String(10), nullable=False)
    customer = db.Column(db.String(150))
    phone = db.Column(db.String(50))
    customer_email = db.Column(db.String(150))
    count = db.Column(db.Integer, default=1)
    price = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default="pending")  # pending, confirmed, cancelled
    tables_json = db.Column(db.Text)
    payment_status = db.Column(db.String(20), default="pending")
    otp_code = db.Column(db.String(10))
    otp_verified = db.Column(db.Boolean, default=False)
    otp_expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class RestClosedDate(db.Model):
    __tablename__ = "rest_closed_dates"
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, nullable=False)
    closed_date = db.Column(db.String(10), nullable=False)
    is_weekly_off = db.Column(db.Boolean, default=False)
    day_of_week = db.Column(db.String(10))
    reason = db.Column(db.String(200))

# ========================
# NIGHTLIFE BOOKING MODELS
# ========================
class NightlifeVendorConfig(db.Model):
    __tablename__ = "nightlife_vendor_configs"
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, nullable=False, unique=True)
    max_advance_days = db.Column(db.Integer, default=365)
    cancel_before_hrs = db.Column(db.Integer, default=2)
    venue_name = db.Column(db.String(200))
    addr1 = db.Column(db.String(200))
    addr2 = db.Column(db.String(200))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    pincode = db.Column(db.String(20))
    banner_url = db.Column(db.String(300))
    gallery_urls = db.Column(db.Text)  # JSON array of image URLs

class NightlifeSlot(db.Model):
    __tablename__ = "nightlife_slots"
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    start_time = db.Column(db.String(5), nullable=False)
    end_time = db.Column(db.String(5), nullable=False)

class NightlifeTableType(db.Model):
    __tablename__ = "nightlife_table_types"
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    seats = db.Column(db.Integer, nullable=False)
    total_tables = db.Column(db.Integer, default=0)
    price = db.Column(db.Integer, default=0)
    start_time = db.Column(db.String(10))
    end_time = db.Column(db.String(10))
    cancel_hours = db.Column(db.Integer, default=2)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class NightlifeTable(db.Model):
    __tablename__ = "nightlife_tables"
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, nullable=False)
    type_id = db.Column(db.Integer, nullable=False)
    table_number = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default="free")  # free/reserved/unavailable

class NightlifeBooking(db.Model):
    __tablename__ = "nightlife_bookings"

    id = db.Column(db.Integer, primary_key=True)
    slot_id = db.Column(db.Integer)
    booking_date = db.Column(db.String(10))  # YYYY-MM-DD format
    table_numbers = db.Column(db.Text)  # JSON array of table numbers
    total_price = db.Column(db.Integer)
    otp_expiry = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    vendor_id = db.Column(db.Integer, nullable=False)
    type_id = db.Column(db.Integer)
    booking_id = db.Column(db.String(50), unique=True, nullable=False)
    customer_email = db.Column(db.String(150))
    customer_phone = db.Column(db.String(50))
    status = db.Column(db.String(20), default="pending")
    otp_code = db.Column(db.String(10))
    customer_name = db.Column(db.String(150))
    
class NightlifeClosedDate(db.Model):
    __tablename__ = "nightlife_closed_dates"
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, nullable=False)
    closed_date = db.Column(db.String(10), nullable=False)
    reason = db.Column(db.String(200))

# ========================
# RESTAURANT/CLUB MODELS
# ========================
class Restaurant(db.Model):
    __tablename__ = "restaurants"

    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, nullable=False)

    name = db.Column(db.String(200), nullable=False)

    phone = db.Column(db.String(20))
    city = db.Column(db.String(100))

    address = db.Column(db.String(300), nullable=False)
    description = db.Column(db.String(1000))

    is_nightlife = db.Column(db.Boolean, default=False)

    banner_image = db.Column(db.Text)
    delivery_charge = db.Column(db.Float, default=0)
    packing_charge = db.Column(db.Float, default=0)
    active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
class PlatformSettings(db.Model):
    __tablename__ = "platform_settings"

    id = db.Column(db.Integer, primary_key=True)

    platform_commission = db.Column(db.Float, default=10)
    delivery_per_km = db.Column(db.Float, default=10)
    packing_fee = db.Column(db.Float, default=20)
    gst = db.Column(db.Float, default=5)
# ========================
# NIGHTLIFE ORDER MODEL (For Nightlife Online Orders)
# ========================
class NightlifeOrder(db.Model):
    __tablename__ = "nightlife_orders"
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(50), unique=True)
    vendor_id = db.Column(db.Integer, nullable=False)
    club_id = db.Column(db.Integer)  # Reference to nightlife venue
    items_json = db.Column(db.Text)
    subtotal = db.Column(db.Integer, default=0)
    delivery_charge = db.Column(db.Integer, default=0)
    packing_charge = db.Column(db.Integer, default=0)
    coupon_discount = db.Column(db.Integer, default=0)
    total = db.Column(db.Integer, default=0)
    payment_method = db.Column(db.String(20), default="COD")
    payment_status = db.Column(db.String(20), default="PENDING")
    coupon_code = db.Column(db.String(20))
    customer_name = db.Column(db.String(150))
    customer_phone = db.Column(db.String(50))
    customer_email = db.Column(db.String(150))
    delivery_address = db.Column(db.String(500))
    status = db.Column(db.String(30), default="PENDING")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class RestaurantConfig(db.Model):
    __tablename__ = "restaurant_configs"
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, nullable=False, unique=True)
    delivery_charge = db.Column(db.Integer, default=0)
    packing_charge = db.Column(db.Integer, default=0)

class MenuItem(db.Model):
    __tablename__ = "menu_items"
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(1000))
    price = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(100))
    food_type = db.Column(db.String(20))
    available = db.Column(db.Boolean, default=True)
    image_url = db.Column(db.String(300))

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

class ClubImage(db.Model):
    __tablename__ = "club_images"
    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, nullable=False)
    image_url = db.Column(db.String(300), nullable=False)

class DeliveryOrder(db.Model):
    __tablename__ = "delivery_orders"
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, nullable=False)
    restaurant_id = db.Column(db.Integer, nullable=False)
    items_json = db.Column(db.Text, nullable=False)
    subtotal = db.Column(db.Integer, nullable=False)
    delivery_charge = db.Column(db.Integer, default=0)
    packing_charge = db.Column(db.Integer, default=0)
    total = db.Column(db.Integer, nullable=False)
    payment_method = db.Column(db.String(20), nullable=False)
    payment_status = db.Column(db.String(20), default="UNPAID")
    user_name = db.Column(db.String(120))
    user_phone = db.Column(db.String(20))
    address_line1 = db.Column(db.String(200))
    address_line2 = db.Column(db.String(200))
    landmark = db.Column(db.String(200))
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    pincode = db.Column(db.String(20))
    status = db.Column(db.String(30), default="PENDING")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Delivery tracking fields
    delivery_lat = db.Column(db.Float, nullable=True)
    delivery_lng = db.Column(db.Float, nullable=True)

class Rating(db.Model):
    __tablename__ = "ratings"
    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, nullable=False)
    user_name = db.Column(db.String(150), default="Anonymous")
    stars = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.String(1000))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ========================
# NIGHTLIFE ITEMS MODEL (For Online Ordering)
# ========================
class NightlifeItem(db.Model):
    __tablename__ = "nightlife_items"
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, nullable=False)
    club_id = db.Column(db.Integer, nullable=True)
    item_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(1000))
    price = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(100))
    image_url = db.Column(db.String(300))
    availability = db.Column(db.String(20), default="Available")  # Available, Out of Stock
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ========================
# ONLINE ORDERS MODEL
# ========================
class OnlineOrder(db.Model):

    __tablename__ = "online_orders"

    id = db.Column(db.Integer, primary_key=True)

    order_id = db.Column(db.String(50), unique=True)

    vendor_id = db.Column(db.Integer)

    restaurant_id = db.Column(db.Integer)

    items_json = db.Column(db.Text)

    subtotal = db.Column(db.Integer, default=0)

    delivery_charge = db.Column(db.Integer, default=0)

    packing_charge = db.Column(db.Integer, default=0)

    coupon_discount = db.Column(db.Integer, default=0)

    total = db.Column(db.Integer)

    payment_method = db.Column(db.String(20))

    payment_status = db.Column(db.String(20))

    customer_name = db.Column(db.String(150))

    customer_phone = db.Column(db.String(20))

    customer_email = db.Column(db.String(150))

    delivery_address = db.Column(db.String(300))

    status = db.Column(db.String(30))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ========================
# COUPON MODEL
# ========================
class Coupon(db.Model):
    __tablename__ = "coupons"
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    discount_type = db.Column(db.String(10), default="percent")  # percent, flat
    discount_value = db.Column(db.Integer, nullable=False)
    min_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AdminSettings(db.Model):

    __tablename__ = "admin_settings"

    id = db.Column(db.Integer, primary_key=True)

    # Restaurant settings
    restaurant_gst = db.Column(db.Float, default=5)
    restaurant_delivery_fee = db.Column(db.Float, default=0)
    restaurant_packing_fee = db.Column(db.Float, default=0)
    restaurant_platform_commission = db.Column(db.Float, default=25)

    # Nightlife settings
    nightlife_platform_commission = db.Column(db.Float, default=20)
    nightlife_service_fee = db.Column(db.Float, default=0)
# ========================
# HELPERS
# ========================
def create_user_session(user_id):
    token = str(uuid.uuid4())
    now = datetime.utcnow()
    session = UserSession(user_id=user_id, token=token, created_at=now, expires_at=now + timedelta(days=7))
    db.session.add(session)
    db.session.commit()
    return token

def get_current_user():
    token = request.cookies.get("zoma_session")
    if not token:
        return None
    session = UserSession.query.filter_by(token=token).first()
    if not session or session.expires_at < datetime.utcnow():
        return None
    return User.query.get(session.user_id)

@app.route("/vendor/getNightlifeItems/<int:vendor_id>")
def getNightlifeItems(vendor_id):

    items = NightlifeItem.query.filter_by(vendor_id=vendor_id).all()

    result = []

    for item in items:

        img = item.image

        if img and not img.startswith("http") and not img.startswith("data:image"):
            img = "data:image/jpeg;base64," + img.lstrip("/")

        result.append({
            "id": item.id,
            "name": item.name,
            "description": item.description,
            "price": item.price,
            "image": img,
            "available": item.available
        })

    return jsonify({
        "success": True,
        "items": result
    })



def _get_or_create_rest_config(vendor_id):
    cfg = RestVendorConfig.query.filter_by(vendor_id=vendor_id).first()
    if not cfg:
        cfg = RestVendorConfig(vendor_id=vendor_id)
        db.session.add(cfg)
        db.session.commit()
    return cfg

def is_rest_date_closed(vendor_id, check_date):
    closed = RestClosedDate.query.filter_by(vendor_id=vendor_id, closed_date=check_date, is_weekly_off=False).first()
    if closed:
        return True
    try:
        check_dt = datetime.strptime(check_date, "%Y-%m-%d")
        day_name = check_dt.strftime("%A")
        weekly_off = RestClosedDate.query.filter_by(vendor_id=vendor_id, is_weekly_off=True, day_of_week=day_name).first()
        if weekly_off:
            return True
    except:
        pass
    return False

def calculate_rest_availability(vendor_id, type_id, slot_id, date_str):

    type_obj = RestTableType.query.filter_by(
        id=type_id,
        vendor_id=vendor_id
    ).first()

    if not type_obj:
        return 0

    confirmed_tables = db.session.query(func.sum(RestBooking.count)).filter(
        RestBooking.vendor_id == vendor_id,
        RestBooking.type_id == type_id,
        RestBooking.slot_id == slot_id,
        RestBooking.date == date_str,
        RestBooking.status == "confirmed"
    ).scalar() or 0

    available_tables = type_obj.total - confirmed_tables

    return max(0, available_tables)
def _get_or_create_nightlife_config(vendor_id):
    cfg = NightlifeVendorConfig.query.filter_by(vendor_id=vendor_id).first()
    if not cfg:
        cfg = NightlifeVendorConfig(vendor_id=vendor_id)
        db.session.add(cfg)
        db.session.commit()
    return cfg

def is_nightlife_date_closed(vendor_id, check_date):
    closed = NightlifeClosedDate.query.filter_by(vendor_id=vendor_id, closed_date=check_date).first()
    if closed:
        return True
    return False

def calculate_nightlife_availability(vendor_id, type_id, slot_id, date_str):
    type_obj = NightlifeTableType.query.filter_by(id=type_id, vendor_id=vendor_id).first()
    if not type_obj:
        return 0
    confirmed_bookings = NightlifeBooking.query.filter(
        NightlifeBooking.vendor_id == vendor_id,
        NightlifeBooking.type_id == type_id,
        NightlifeBooking.slot_id == slot_id,
        NightlifeBooking.booking_date == date_str,
        NightlifeBooking.status == "confirmed"
    ).all()
    confirmed_count = sum(len(json.loads(b.table_numbers)) if b.table_numbers else 0 for b in confirmed_bookings)
    return type_obj.total_tables - confirmed_count

# ========================
# STATIC FILES & HTML SERVING
# ========================
@app.route("/")
def home():
    return send_from_directory(".", "nightlife.html")

@app.route("/<path:filename>")
def serve_static(filename):

    if filename.startswith("api/"):
        return jsonify({"error": "API endpoint not found"}), 404

    return send_from_directory(".", filename)

@app.route("/vendor_dashboard")
def vendor_dashboard():
    return send_from_directory(".", "vendor_order_online.html")

@app.route("/uploads/<path:filename>")
def serve_uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/Images/<path:filename>")
def images(filename):
    return send_from_directory("Images", filename)

@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "message": "ZomaClone backend running"})


@app.route("/api/vendor/menus", methods=["GET"])
def get_vendor_menus():

    vendor_id = request.args.get("vendor_id", type=int)

    if not vendor_id:
        return jsonify({
            "success": False,
            "message": "vendor_id required"
        }), 400

    restaurants = Restaurant.query.filter_by(
        vendor_id=vendor_id,
        is_nightlife=False
    ).all()

    restaurant_ids = [r.id for r in restaurants]

    if not restaurant_ids:
        return jsonify({"success": True, "menu": []})

    items = MenuItem.query.filter(
        MenuItem.restaurant_id.in_(restaurant_ids)
    ).all()

    restaurant_map = {r.id: r.name for r in restaurants}

    result = []

    for item in items:

        img = item.image_url

        # FIX IMAGE FORMAT
        if img:
            img = img.strip()

            # if raw base64
            if img.startswith("/9j") or img.startswith("iVBOR"):
                img = "data:image/jpeg;base64," + img.lstrip("/")

        result.append({
            "id": item.id,
            "restaurant_id": item.restaurant_id,
            "restaurant_name": restaurant_map.get(item.restaurant_id, "Unknown"),
            "name": item.name,
            "description": item.description,
            "price": item.price,
            "category": item.category,
            "image": img,
            "available": item.available
        })

    return jsonify({
        "success": True,
        "menu": result
    })
# ========================
# OTP
# ========================
@app.route("/api/otp/send", methods=["POST"])
def api_send_otp():
    data = get_data()
    role = data.get("role")
    purpose = data.get("purpose")
    email = (data.get("email") or "").strip()
    phone = (data.get("phone") or "").strip()
    if not role or not purpose:
        return jsonify({"success": False, "message": "role & purpose required"}), 400
    if not email and not phone:
        return jsonify({"success": False, "message": "email or phone required"}), 400
    code = generate_otp()
    expires = datetime.utcnow() + timedelta(minutes=10)
    otp = OTPLog(role=role, purpose=purpose, email=email or None, phone=phone or None, code=code, expires_at=expires)
    db.session.add(otp)
    db.session.commit()
    if email:
        send_email(email, "Your ZomaClone OTP", f"Your OTP is {code}")
    return jsonify({"success": True, "message": "OTP sent"})

@app.route("/api/otp/verify", methods=["POST"])
def api_verify_otp():
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
        return jsonify({"success": False, "message": "Blocked"}), 403
    if otp.expires_at < datetime.utcnow():
        otp.attempts += 1
        db.session.commit()
        return jsonify({"success": False, "message": "OTP expired"}), 400
    if otp.code == code:
        otp.is_verified = True
        db.session.commit()
        return jsonify({"success": True, "message": "OTP verified"})
    otp.attempts += 1
    if otp.attempts >= 5:
        otp.blocked_until = datetime.utcnow() + timedelta(hours=24)
    db.session.commit()
    return jsonify({"success": False, "message": "Incorrect OTP"})

# ========================
# USER AUTH
# ========================
@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    data = request.get_json() or {}
    identifier = (data.get("email") or data.get("phone") or "").strip().lower()
    if not identifier:
        return jsonify({"ok": False, "message": "Email or phone required"}), 400
    user = User.query.filter(or_(User.email == identifier, User.phone == identifier)).first()
    if not user:
        return jsonify({"ok": False, "message": "User not found"}), 404
    token = create_user_session(user.id)
    resp = make_response(jsonify({"ok": True, "user": {"id": user.id, "name": user.name, "email": user.email, "phone": user.phone}}))
    resp.set_cookie("zoma_session", token, httponly=True, samesite="Lax", max_age=7*24*3600, path="/")
    return resp

@app.route("/api/auth/me", methods=["GET"])
def auth_me():
    user = get_current_user()
    if not user:
        return jsonify({"ok": False, "user": None})
    return jsonify({"ok": True, "user": {"id": user.id, "name": user.name, "email": user.email, "phone": user.phone}})

@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    token = request.cookies.get("zoma_session")
    if token:
        UserSession.query.filter_by(token=token).delete()
        db.session.commit()
    resp = make_response(jsonify({"ok": True}))
    resp.set_cookie("zoma_session", "", expires=0, path="/")
    return resp

@app.route("/api/users/register", methods=["POST"])
def register_user():
    data = get_data()
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    phone = (data.get("phone") or "").strip()
    if not name or not email or not phone:
        return jsonify({"success": False, "message": "name, email, phone required"}), 400
    existing = User.query.filter(or_(User.email == email, User.phone == phone)).first()
    if existing:
        return jsonify({"success": False, "message": "User already exists"}), 409
    otp_verified = OTPLog.query.filter(OTPLog.role == "user", OTPLog.purpose == "signup", OTPLog.is_verified == True, or_(OTPLog.email == email, OTPLog.phone == phone)).order_by(OTPLog.id.desc()).first()
    if not otp_verified:
        return jsonify({"success": False, "message": "OTP not verified"}), 400
    u = User(name=name, email=email, phone=phone)
    db.session.add(u)
    db.session.commit()
    return jsonify({"success": True, "user": {"id": u.id, "name": u.name, "email": u.email, "phone": u.phone}})

# ========================
# VENDOR AUTH
# ========================
@app.route("/api/vendors/register", methods=["POST"])
def register_vendor():
    data = get_data()
    restaurant_name = (data.get("restaurant_name") or "").strip()
    owner_name = (data.get("owner_name") or "").strip()
    email = (data.get("email") or "").strip()
    phone = (data.get("phone") or "").strip()
    address = (data.get("address") or "").strip()
    password = (data.get("password") or "").strip() or None
    vendor_type = (data.get("vendor_type") or "restaurant").strip()
    if not all([restaurant_name, owner_name, email, phone, address]):
        return jsonify({"success": False, "message": "Missing fields"}), 400
    existing = Vendor.query.filter(or_(Vendor.email == email, Vendor.phone == phone)).first()
    if existing:
        return jsonify({"success": False, "message": "Vendor already exists"}), 409
    v = Vendor(restaurant_name=restaurant_name, owner_name=owner_name, email=email, phone=phone, address=address, password=password, vendor_type=vendor_type)
    db.session.add(v)
    db.session.commit()
    return jsonify({"success": True, "vendor_id": v.id, "vendor_type": vendor_type})

@app.route("/api/vendors/login", methods=["POST"])
def login_vendor():
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
    return jsonify({"success": True, "vendor": {"id": v.id, "restaurant_name": v.restaurant_name, "owner_name": v.owner_name, "email": v.email, "phone": v.phone, "address": v.address, "vendor_type": v.vendor_type}})

# ========================
# VENDOR BY EMAIL
# ========================
@app.route("/api/vendor/getByEmail", methods=["POST"])
def get_vendor_by_email():
    data = get_data()
    email = (data.get("email") or "").strip().lower()
    if not email:
        return jsonify({"success": False, "message": "email required"}), 400
    vendor = Vendor.query.filter_by(email=email).first()
    if not vendor:
        return jsonify({"success": False, "message": "Vendor not found"}), 404
    return jsonify({"success": True, "vendor": {"id": vendor.id, "restaurant_name": vendor.restaurant_name, "owner_name": vendor.owner_name, "email": vendor.email, "phone": vendor.phone, "vendor_type": vendor.vendor_type}})

# ========================
# GET VENDOR BY ID
# ========================
@app.route("/api/vendors/<int:vendor_id>")
def get_vendor(vendor_id):
    vendor = Vendor.query.get(vendor_id)
    if not vendor:
        return jsonify({
            "success": False,
            "message": "Vendor not found"
        }), 404

    return jsonify({
        "success": True,
        "vendor": {
            "id": vendor.id,
            "restaurant_name": vendor.restaurant_name,
            "owner_name": vendor.owner_name,
            "email": vendor.email,
            "phone": vendor.phone,
            "address": vendor.address,
            "upi_id": vendor.upi_id
        }
    })

# ========================
# VENDOR OTP - REGISTRATION
# ========================
@app.route("/api/vendor/send-otp", methods=["POST"])
def vendor_send_otp():
    data = get_data()
    email = (data.get("email") or "").strip()
    if not email:
        return jsonify({"success": False, "message": "email required"}), 400
    existing = Vendor.query.filter_by(email=email).first()
    if existing:
        return jsonify({"success": False, "message": "Vendor already exists with this email"}), 409
    code = generate_otp()
    expires = datetime.utcnow() + timedelta(minutes=10)
    otp = OTPLog(role="vendor", purpose="signup", email=email, phone=None, code=code, expires_at=expires)
    db.session.add(otp)
    db.session.commit()
    email_sent = send_email(email, "Your ZomaClone Vendor Registration OTP", f"Your OTP is: {code}")
    print(f"[VENDOR REGISTRATION OTP] Email sent status: {email_sent}")
    return jsonify({"success": True, "message": "OTP sent to your email", "debug_otp": code})


@app.route("/api/vendor/verify-otp", methods=["POST"])
def vendor_verify_otp():
    data = get_data()
    email = (data.get("email") or "").strip()
    otp_code = (data.get("otp") or "").strip()
    if not email or not otp_code:
        return jsonify({"success": False, "message": "email and otp required"}), 400
    otp = OTPLog.query.filter(OTPLog.role == "vendor", OTPLog.purpose == "signup", OTPLog.email == email, OTPLog.code == otp_code).first()
    if not otp:
        return jsonify({"success": False, "message": "Invalid OTP"}), 400
    if otp.expires_at < datetime.utcnow():
        return jsonify({"success": False, "message": "OTP expired"}), 400
    otp.is_verified = True
    db.session.commit()
    return jsonify({"success": True, "message": "OTP verified successfully"})


# ========================
# VENDOR LOGIN OTP
# ========================
@app.route("/api/vendor/login-send-otp", methods=["POST"])
def vendor_login_send_otp():
    data = get_data()
    identifier = (data.get("identifier") or "").strip()
    if not identifier:
        return jsonify({"success": False, "message": "identifier required"}), 400
    vendor = Vendor.query.filter(or_(Vendor.email == identifier, Vendor.phone == identifier)).first()
    if not vendor:
        return jsonify({"success": False, "message": "Vendor not found with this email/phone"}), 404
    code = generate_otp()
    expires = datetime.utcnow() + timedelta(minutes=10)
    otp = OTPLog(role="vendor", purpose="login", email=vendor.email, phone=vendor.phone, code=code, expires_at=expires)
    db.session.add(otp)
    db.session.commit()
    email_sent = send_email(vendor.email, "Your ZomaClone Login OTP", f"Your login OTP is: {code}")
    print(f"[VENDOR LOGIN OTP] Email sent status: {email_sent}")
    return jsonify({"success": True, "message": "OTP sent to your email", "debug_otp": code})


@app.route("/api/vendor/login-verify-otp", methods=["POST"])
def vendor_login_verify_otp():
    data = get_data()
    identifier = (data.get("identifier") or "").strip()
    otp_code = (data.get("otp") or "").strip()

    if not identifier or not otp_code:
        return jsonify({"success": False, "message": "identifier and otp required"}), 400

    vendor = Vendor.query.filter(or_(Vendor.email == identifier, Vendor.phone == identifier)).first()
    if not vendor:
        return jsonify({"success": False, "message": "Vendor not found"}), 404

    otp = OTPLog.query.filter(
        OTPLog.role == "vendor",
        OTPLog.purpose == "login",
        OTPLog.code == otp_code,
        or_(OTPLog.email == identifier, OTPLog.phone == identifier)
    ).first()

    if not otp:
        return jsonify({"success": False, "message": "Invalid OTP"}), 400

    if otp.expires_at < datetime.utcnow():
        return jsonify({"success": False, "message": "OTP expired"}), 400

    otp.is_verified = True

    # 🔴 IMPORTANT PART
    session["vendor_id"] = vendor.id

    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Login successful",
        "vendor": {
            "id": vendor.id,
            "restaurant_name": vendor.restaurant_name,
            "owner_name": vendor.owner_name,
            "email": vendor.email,
            "phone": vendor.phone,
            "vendor_type": vendor.vendor_type
        }
    })


# ========================
# RESTAURANT BOOKING API
# ========================
@app.route("/api/dining/restaurants", methods=["GET"])
def dining_restaurants():

    vendors = Vendor.query.all()

    result = []

    for v in vendors:
        result.append({
            "id": v.id,
            "name": getattr(v, "restaurant_name", ""),
            "address": getattr(v, "address", ""),
            "banner": getattr(v, "banner", None)
        })

    return jsonify({
        "success": True,
        "data": result
    })

@app.route("/api/restaurant/types", methods=["GET"])
def rest_get_types():
    vendor_id = request.args.get("vendor_id", type=int)
    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400
    types = RestTableType.query.filter_by(vendor_id=vendor_id).all()
    result = []
    for t in types:
        result.append({"id": t.id, "name": t.name, "seats": t.seats, "total": t.total, "price": t.price, "timeStart": t.time_start, "timeEnd": t.time_end})
    return jsonify({"success": True, "types": result})

@app.route("/api/restaurant/types", methods=["POST"])
def rest_save_type():
    vendor_id = request.args.get("vendor_id", type=int)
    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400
    data = request.get_json() or {}
    type_id = data.get("id")
    name = (data.get("name") or "").strip()
    seats = int(data.get("seats") or 0)
    total = int(data.get("total") or 0)
    price = int(data.get("price") or 0)
    if not name or seats <= 0 or total <= 0:
        return jsonify({"success": False, "message": "Invalid type data"}), 400
    if type_id:
        t = RestTableType.query.filter_by(id=int(type_id), vendor_id=vendor_id).first()
        if not t:
            return jsonify({"success": False, "message": "Type not found"}), 404
    else:
        t = RestTableType(vendor_id=vendor_id)
        db.session.add(t)
    t.name = name
    t.seats = seats
    t.total = total
    t.price = price
    t.time_start = data.get("timeStart", "10:00")
    t.time_end = data.get("timeEnd", "23:00")
    db.session.commit()
    return jsonify({"success": True, "id": t.id})

@app.route("/api/restaurant/slots", methods=["GET"])
def rest_get_slots():
    vendor_id = request.args.get("vendor_id", type=int)
    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400
    slots = RestSlot.query.filter_by(vendor_id=vendor_id).all()
    return jsonify({"success": True, "slots": [{"id": s.id, "name": s.name, "start": s.start, "end": s.end} for s in slots]})

@app.route("/api/restaurant/slots", methods=["POST"])
def rest_save_slot():
    vendor_id = request.args.get("vendor_id", type=int)
    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400
    data = request.get_json() or {}
    slot_id = data.get("id")
    name = (data.get("name") or "").strip()
    start = (data.get("start") or "").strip()[:5]
    end = (data.get("end") or "").strip()[:5]
    if slot_id:
        s = RestSlot.query.filter_by(id=int(slot_id), vendor_id=vendor_id).first()
        if not s:
            return jsonify({"success": False, "message": "Slot not found"}), 404
    else:
        s = RestSlot(vendor_id=vendor_id)
        db.session.add(s)
    s.name = name
    s.start = start
    s.end = end
    db.session.commit()
    return jsonify({"success": True, "id": s.id})

@app.route("/api/restaurant/availability", methods=["GET"])
def rest_check_availability():
    vendor_id = request.args.get("vendor_id", type=int)
    type_id = request.args.get("type_id", type=int)
    slot_id = request.args.get("slot_id", type=int)
    date_str = request.args.get("date", "")
    if not all([vendor_id, type_id, slot_id, date_str]):
        return jsonify({"success": False, "message": "vendor_id, type_id, slot_id, date required"}), 400
    available = calculate_rest_availability(vendor_id, type_id, slot_id, date_str)
    return jsonify({"success": True, "available": available})

@app.route("/api/restaurant/bookings", methods=["POST"])
def rest_create_booking():

    vendor_id = request.args.get("vendor_id", type=int)

    if not vendor_id:
        return jsonify({
            "success": False,
            "message": "vendor_id required"
        }), 400


    data = request.get_json() or {}

    type_id = data.get("typeId")
    slot_id = data.get("slotId")
    date = data.get("date")
    count = int(data.get("count", 1))

    if not type_id or not slot_id or not date:
        return jsonify({
            "success": False,
            "message": "Missing booking fields"
        }), 400


    # Check table type
    table_type = RestTableType.query.filter_by(
        id=type_id,
        vendor_id=vendor_id
    ).first()

    if not table_type:
        return jsonify({
            "success": False,
            "message": "Table type not found"
        }), 404


    # Check slot
    slot = RestSlot.query.filter_by(
        id=slot_id,
        vendor_id=vendor_id
    ).first()

    if not slot:
        return jsonify({
            "success": False,
            "message": "Slot not found"
        }), 404


    # Check availability
    booked_tables = RestBooking.query.filter_by(
        vendor_id=vendor_id,
        type_id=type_id,
        slot_id=slot_id,
        date=date,
        status="confirmed"
    ).count()

    available = table_type.total - booked_tables

    if available < count:
        return jsonify({
            "success": False,
            "message": "Not enough tables available"
        }), 400


    # Create booking
    booking = RestBooking(
        vendor_id=vendor_id,
        type_id=type_id,
        slot_id=slot_id,
        date=date,
        customer=data.get("customer"),
        phone=data.get("phone"),
        customer_email=data.get("email"),
        count=count,
        price=table_type.price * count,
        status="confirmed"
    )

    db.session.add(booking)
    db.session.commit()


    return jsonify({
        "success": True,
        "booking_id": booking.id,
        "message": "Booking confirmed"
    })
@app.route("/api/restaurant/bookings/<int:booking_id>/verify-otp", methods=["POST"])
def rest_verify_booking_otp(booking_id):
    data = request.get_json() or {}
    otp_code = (data.get("otp") or "").strip()
    b = RestBooking.query.get(booking_id)
    if not b:
        return jsonify({"success": False, "message": "Booking not found"}), 404
    if b.status == "confirmed":
        return jsonify({"success": True, "message": "Already confirmed"})
    if b.otp_expires_at and b.otp_expires_at < datetime.utcnow():
        b.status = "cancelled"
        db.session.commit()
        return jsonify({"success": False, "message": "OTP expired, booking cancelled"}), 400
    if b.otp_code != otp_code:
        return jsonify({"success": False, "message": "Incorrect OTP"}), 400
    b.otp_verified = True
    b.status = "confirmed"
    db.session.commit()
    return jsonify({"success": True, "message": "Booking confirmed!", "booking": {"id": b.id, "status": b.status, "date": b.date}})

@app.route("/api/restaurant/bookings", methods=["GET"])
def rest_get_bookings():

    vendor_id = request.args.get("vendor_id")

    if not vendor_id:
        return jsonify({
            "success": False,
            "message": "vendor_id required"
        }), 400

    try:

        vendor_id = int(vendor_id)

        bookings = RestBooking.query.filter_by(vendor_id=vendor_id).all()

        result = []

        for b in bookings:

            table_type = db.session.get(RestTableType, b.type_id)
            slot = db.session.get(RestSlot, b.slot_id)

            result.append({
                "id": b.id,
                "customer": b.customer,
                "phone": b.phone,
                "typeName": table_type.name if table_type else "",
                "date": b.date,
                "slotName": slot.name if slot else "",
                "tables": b.count,
                "price": b.price,
                "status": b.status,
                "createdAt": b.created_at.isoformat() if b.created_at else None
            })

        return jsonify({
            "success": True,
            "bookings": result
        })

    except Exception as e:

        print("REST BOOKINGS ERROR:", e)

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

@app.route("/api/restaurant/closed-dates", methods=["GET"])
def rest_get_closed_dates():
    vendor_id = request.args.get("vendor_id", type=int)
    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400
    closed = RestClosedDate.query.filter_by(vendor_id=vendor_id).all()
    return jsonify({"success": True, "dates": [{"id": c.id, "date": c.closed_date, "is_weekly_off": c.is_weekly_off, "day_of_week": c.day_of_week, "reason": c.reason} for c in closed]})

@app.route("/api/restaurant/closed-dates", methods=["POST"])
def rest_add_closed_date():
    vendor_id = request.args.get("vendor_id", type=int)
    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400
    data = request.get_json() or {}
    closed_date = (data.get("date") or "").strip()
    is_weekly_off = data.get("is_weekly_off", False)
    day_of_week = data.get("day_of_week", "")
    reason = (data.get("reason") or "").strip()
    if not closed_date and not is_weekly_off:
        return jsonify({"success": False, "message": "date or weekly off required"}), 400
    cd = RestClosedDate(vendor_id=vendor_id, closed_date=closed_date or None, is_weekly_off=is_weekly_off, day_of_week=day_of_week if is_weekly_off else None, reason=reason)
    db.session.add(cd)
    db.session.commit()
    return jsonify({"success": True, "message": "Closed date added"})

@app.route("/api/restaurant/vendor/me")
def rest_vendor_me():
    vendor_id = request.args.get("vendor_id", type=int)
    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400
    v = Vendor.query.get(vendor_id)
    if not v:
        return jsonify({"success": False, "message": "Vendor not found"}), 404
    s = _get_or_create_rest_config(vendor_id)
    upcoming = RestBooking.query.filter_by(vendor_id=vendor_id, status="confirmed").count()
    return jsonify({"success": True, "vendor": {"id": v.id, "restaurant_name": v.restaurant_name, "owner_name": v.owner_name, "email": v.email, "phone": v.phone, "address": v.address}, "settings": {"maxAdvanceDays": s.max_advance_days, "cancelBeforeHrs": s.cancel_before_hrs}, "location": {"addr1": s.addr1, "city": s.city, "state": s.state, "pincode": s.pincode}, "banner": s.banner_url, "stats": {"upcomingBookings": upcoming}})


@app.route("/api/restaurants")
def get_restaurants():

    restaurants = Restaurant.query.filter_by(
        is_nightlife=False,
        active=True
    ).all()

    data = []

    for r in restaurants:
        data.append({
            "id": r.id,
            "vendor_id": r.vendor_id,
            "name": r.name,
            "city": r.city,
            "address": r.address,
            "description": r.description,
            "banner_image": r.banner_image,
            "delivery_charge": getattr(r, "delivery_charge", 0),
            "packing_charge": getattr(r, "packing_charge", 0)
        })

    return jsonify({
        "success": True,
        "data": data
    })
# REST Vendor endpoint (alias for restaurant_detail.html)
@app.route("/api/rest/vendor/me", methods=["GET"])
def rest_vendor_me_alias():
    """Alias for /api/restaurant/vendor/me - returns vendor info for restaurant_detail.html"""
    vendor_id = request.args.get("vendor_id", type=int)
    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400
    
    try:
        # Get vendor from Vendor table
        vendor = Vendor.query.get(vendor_id)
        if not vendor:
            return jsonify({"success": False, "message": "Vendor not found"}), 404
        
        # Get nightlife config if exists
        config = NightlifeVendorConfig.query.filter_by(vendor_id=vendor_id).first()
        
        return jsonify({
            "success": True,
            "data": {
                "id": vendor.id,
                "name": vendor.restaurant_name,
                "description": f"Premium nightlife experience at {vendor.restaurant_name}",
                "rating": 4.5,
                "image": config.banner_url if config else "",
                "latitude": None,
                "longitude": None,
                "delivery_fee_per_km": 10,
                "address": vendor.address,
                "phone": vendor.phone,
                "email": vendor.email,
                "upi_id": vendor.upi_id or ""
            }
        })
    except Exception as e:
        print(f"[ERROR] rest_vendor_me_alias: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/restaurant/settings", methods=["POST"])
def rest_save_settings():
    vendor_id = request.args.get("vendor_id", type=int)
    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400
    s = _get_or_create_rest_config(vendor_id)
    data = request.get_json() or {}
    s.max_advance_days = int(data.get("maxAdvanceDays") or 365)
    s.cancel_before_hrs = int(data.get("cancelBeforeHrs") or 2)
    db.session.commit()
    return jsonify({"success": True})

@app.route("/api/restaurant/location", methods=["POST"])
def rest_save_location():
    vendor_id = request.args.get("vendor_id", type=int)
    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400
    s = _get_or_create_rest_config(vendor_id)
    data = request.get_json() or {}
    s.addr1 = (data.get("addr1") or "").strip()
    s.addr2 = (data.get("addr2") or "").strip()
    s.city = (data.get("city") or "").strip()
    s.state = (data.get("state") or "").strip()
    s.pincode = (data.get("pincode") or "").strip()
    db.session.commit()
    return jsonify({"success": True})

@app.route("/api/restaurant/banner", methods=["POST"])
def rest_upload_banner():
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
    new_name = f"rest_banner_{vendor_id}_{int(datetime.utcnow().timestamp())}_{filename}".replace(" ", "_")
    path = os.path.join(app.config["UPLOAD_FOLDER"], new_name)
    file.save(path)
    s = _get_or_create_rest_config(vendor_id)
    s.banner_url = f"/uploads/{new_name}"
    db.session.commit()
    return jsonify({"success": True, "bannerUrl": s.banner_url})

# ========================
# NIGHTLIFE BOOKING API - USER FACING
# ========================
@app.route("/api/nightlife/clubs", methods=["GET"])
def nl_get_clubs():
    try:

        configs = NightlifeVendorConfig.query.all()

        clubs = []

        for cfg in configs:

            vendor = Vendor.query.get(cfg.vendor_id)

            if not vendor:
                continue

            clubs.append({
                "id": vendor.id,
                "name": vendor.restaurant_name,
                "banner": cfg.banner_url,
                "city": cfg.city,
                "state": cfg.state
            })

        return jsonify({
            "success": True,
            "clubs": clubs
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500
# Legacy endpoint for nightlife_order.html
@app.route("/nightlife/clubs", methods=["GET"])
def nl_get_all_clubs_legacy():
    """Get all clubs for user view - legacy endpoint (no /api prefix)"""
    clubs = []
    try:
        vendors_with_tables = db.session.query(NightlifeTableType.vendor_id).distinct().all()
        for vt in vendors_with_tables:
            v = Vendor.query.get(vt[0])
            if v:
                config = NightlifeVendorConfig.query.filter_by(vendor_id=v.id).first()
                clubs.append({
                    "club_id": v.id,
                    "club_name": v.restaurant_name,
                    "location": f"{config.city if config else ''}, {config.state if config else ''}".strip(', '),
                    "description": f"Premium nightlife experience at {v.restaurant_name}",
                    "image": config.banner_url if config else "https://images.unsplash.com/photo-1516450360452-9312f5e86fc7?w=400",
                    "rating": 4.5,
                    "status": "open"
                })
    except:
        pass
    try:
        configs = NightlifeVendorConfig.query.all()
        existing_ids = [c.get('club_id') for c in clubs if c.get('club_id')]
        for cfg in configs:
            if cfg.vendor_id not in existing_ids:
                v = Vendor.query.get(cfg.vendor_id)
                if v:
                    clubs.append({
                        "club_id": v.id,
                        "club_name": v.restaurant_name,
                        "location": f"{cfg.city if cfg else ''}, {cfg.state if cfg else ''}".strip(', '),
                        "description": f"Premium nightlife experience at {v.restaurant_name}",
                        "image": cfg.banner_url if cfg else "https://images.unsplash.com/photo-1516450360452-9312f5e86fc7?w=400",
                        "rating": 4.5,
                        "status": "open"
                    })
    except:
        pass
    return jsonify(clubs)

@app.route("/api/nightlife/bookings", methods=["GET"])
def nl_get_bookings():

    vendor_id = request.args.get("vendor_id", type=int)

    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400

    bookings = NightlifeBooking.query.filter_by(
        vendor_id=vendor_id
    ).order_by(NightlifeBooking.id.desc()).all()

    result = []

    for b in bookings:

        slot = NightlifeSlot.query.get(b.slot_id)
        table_type = NightlifeTableType.query.get(b.type_id)

        result.append({
            "booking_id": b.booking_id,
            "customer": b.customer_name,
            "phone": b.customer_phone,
            "date": b.booking_date,
            "slot": slot.name if slot else "",
            "tables": json.loads(b.table_numbers),
            "price": b.total_price,
            "status": b.status
        })

    return jsonify({
        "success": True,
        "bookings": result
    })
@app.route("/api/nightlife/clubs/<int:vendor_id>/details", methods=["GET"])
def nl_get_club_details(vendor_id):

    try:

        vendor = Vendor.query.get(vendor_id)

        if not vendor:
            return jsonify({"success": False, "message": "Club not found"}), 404


        config = NightlifeVendorConfig.query.filter_by(vendor_id=vendor_id).first()


        club_info = {
            "id": vendor.id,
            "name": vendor.restaurant_name,
            "banner": config.banner_url if config else None,
            "city": config.city if config else '',
            "state": config.state if config else '',
            "address": config.addr1 if config else '',
            "maxAdvanceDays": config.max_advance_days if config else 30
        }


        table_types = NightlifeTableType.query.filter_by(vendor_id=vendor_id).all()

        types_data = []

        for t in table_types:

            free_count = NightlifeTable.query.filter_by(
                vendor_id=vendor_id,
                type_id=t.id,
                status="free"
            ).count()


            types_data.append({
                "id": t.id,
                "name": t.name,
                "seats": t.seats,
                "price": t.price,
                "timeStart": str(t.start_time)[:5] if t.start_time else None,
                "timeEnd": str(t.end_time)[:5] if t.end_time else None,
                "freeTables": free_count
            })


        slots = NightlifeSlot.query.filter_by(vendor_id=vendor_id)\
                .order_by(NightlifeSlot.start_time).all()
        slots_data = []
        for s in slots:
            slots_data.append({
                "id": s.id,
                "name": s.name,
                "start": str(s.start_time)[:5] if s.start_time else None,
                "end": str(s.end_time)[:5] if s.end_time else None
            })


        return jsonify({
            "success": True,
            "vendor": club_info,
            "tableTypes": types_data,
            "slots": slots_data
        })


    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

@app.route("/api/nightlife/clubs/<int:vendor_id>/availability", methods=["GET"])
def nl_get_table_availability(vendor_id):
    """Get available tables for date/slot"""
    date_str = request.args.get("date", "")
    slot_id = request.args.get("slot_id", type=int)
    
    if not date_str:
        return jsonify({"success": False, "message": "date required"}), 400
    
    try:
        table_types = NightlifeTableType.query.filter_by(vendor_id=vendor_id).all()

        availability = []

        for t in table_types:

            confirmed_bookings = NightlifeBooking.query.filter(
                NightlifeBooking.vendor_id == vendor_id,
                NightlifeBooking.type_id == t.id,
                NightlifeBooking.booking_date == date_str,
                NightlifeBooking.status == "confirmed"
            ).all()

            booked_count = sum(
                len(json.loads(b.table_numbers)) if b.table_numbers else 0
                for b in confirmed_bookings
            )

            if slot_id:
                confirmed_bookings = NightlifeBooking.query.filter(
                    NightlifeBooking.vendor_id == vendor_id,
                    NightlifeBooking.type_id == t.id,
                    NightlifeBooking.slot_id == slot_id,
                    NightlifeBooking.booking_date == date_str,
                    NightlifeBooking.status == "confirmed"
                ).all()

                booked_count = sum(
                    len(json.loads(b.table_numbers)) if b.table_numbers else 0
                    for b in confirmed_bookings
                )

            available = t.total_tables - booked_count

            if available > 0:
                availability.append({
                    "id": t.id,
                    "name": t.name,
                    "seats": t.seats,
                    "price": t.price,
                    "freeTables": available,
                    "availableTables": available
                })
        
        return jsonify({"success": True, "availability": availability})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/nightlife/availability", methods=["GET"])
def nl_check_availability():
    vendor_id = request.args.get("vendor_id", type=int)
    type_id = request.args.get("type_id", type=int)
    slot_id = request.args.get("slot_id", type=int)
    date_str = request.args.get("date", "")
    
    if not all([vendor_id, type_id, slot_id, date_str]):
        return jsonify({"success": False, "message": "vendor_id, type_id, slot_id, date required"}), 400
    
    available = calculate_nightlife_availability(vendor_id, type_id, slot_id, date_str)
    return jsonify({"success": True, "available": available})


def generate_nightlife_booking_id():
    """Generate unique booking ID: NL-YYYYMMDD-0001"""
    today = datetime.utcnow().strftime("%Y%m%d")
    last_booking = NightlifeBooking.query.filter(
        NightlifeBooking.booking_id.like(f"NL-{today}%")
    ).order_by(NightlifeBooking.id.desc()).first()
    
    if last_booking:
        try:
            last_num = int(last_booking.booking_id.split("-")[-1])
            new_num = last_num + 1
        except:
            new_num = 1
    else:
        new_num = 1
    
    return f"NL-{today}-{new_num:04d}"


@app.route("/api/nightlife/bookings", methods=["POST"])
def nl_create_booking():

    vendor_id = request.args.get("vendor_id", type=int)

    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400

    data = request.get_json() or {}

    type_id = int(data.get("typeId") or data.get("table_type_id") or 0)
    slot_id = int(data.get("slotId") or data.get("slot_id") or 0)
    date_str = (data.get("date") or "").strip()

    customer_name = (data.get("customer_name") or data.get("customer") or "Guest").strip()
    customer_phone = (data.get("customer_phone") or data.get("phone") or "").strip()
    customer_email = (data.get("customer_email") or data.get("email") or "").strip()

    table_count = int(data.get("table_count") or data.get("tables") or 1)

    if not type_id or not slot_id or not date_str:
        return jsonify({
            "success": False,
            "message": "Missing booking fields"
        }), 400

    # check if vendor closed that date
    if is_nightlife_date_closed(vendor_id, date_str):
        return jsonify({
            "success": False,
            "message": "Selected date is not available"
        }), 400

    # parse booking date
    try:
        booking_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except:
        return jsonify({
            "success": False,
            "message": "Invalid date format"
        }), 400

    today = datetime.utcnow().date()

    # prevent booking yesterday
    if booking_date < today:
        return jsonify({
            "success": False,
            "message": "Cannot book past dates"
        }), 400

    if booking_date > today + timedelta(days=365):
        return jsonify({
            "success": False,
            "message": "Booking too far in advance"
        }), 400

    # get table type
    t = NightlifeTableType.query.filter_by(
        id=type_id,
        vendor_id=vendor_id
    ).first()

    # get slot
    s = NightlifeSlot.query.filter_by(
        id=slot_id,
        vendor_id=vendor_id
    ).first()

    if not t or not s:
        return jsonify({
            "success": False,
            "message": "Type or slot not found"
        }), 404

    # prevent booking past slot today
    now = datetime.utcnow()

    if booking_date == today:

        slot_start = s.start_time

        if isinstance(slot_start, str):
            slot_start = datetime.strptime(slot_start, "%H:%M").time()

        slot_datetime = datetime.combine(today, slot_start)

        if slot_datetime <= now:
            return jsonify({
                "success": False,
                "message": "Cannot book past time slot"
            }), 400

    # check availability
    available = calculate_nightlife_availability(
        vendor_id,
        type_id,
        slot_id,
        date_str
    )

    if available < table_count:
        return jsonify({
            "success": False,
            "message": "Not enough tables available"
        }), 400

    booking_id = generate_nightlife_booking_id()

    otp_code = generate_otp()
    otp_expiry = datetime.utcnow() + timedelta(minutes=10)

    table_numbers = json.dumps([
        f"Table {i+1}" for i in range(table_count)
    ])

    total_price = t.price * table_count

    booking = NightlifeBooking(
        booking_id=booking_id,
        vendor_id=vendor_id,
        type_id=type_id,
        slot_id=slot_id,
        booking_date=date_str,
        customer_name=customer_name,
        customer_email=customer_email,
        customer_phone=customer_phone,
        table_numbers=table_numbers,
        total_price=total_price,
        status="pending",
        otp_code=otp_code,
        otp_expiry=otp_expiry
    )

    db.session.add(booking)
    db.session.commit()

    # send OTP email
    if customer_email:
        send_email(
            customer_email,
            "Verify your nightlife booking",
            f"Your booking OTP is: {otp_code}"
        )

    return jsonify({
        "success": True,
        "booking": {
            "booking_id": booking.booking_id,
            "customer": booking.customer_name,
            "phone": booking.customer_phone,
            "date": booking.booking_date
        }
    })

@app.route("/api/nightlife/bookings/verify", methods=["POST"])
def nl_verify_booking_by_id():
    """Verify booking by booking_id string"""
    data = request.get_json() or {}
    booking_id = data.get("booking_id", "")
    otp_code = data.get("otp", "").strip()
    
    if not booking_id or not otp_code:
        return jsonify({"success": False, "message": "booking_id and otp required"}), 400
    
    b = NightlifeBooking.query.filter_by(booking_id=booking_id).first()
    if not b:
        return jsonify({"success": False, "message": "Booking not found"}), 404
    
    if b.status == "confirmed":
        return jsonify({"success": True, "message": "Already confirmed", "booking": {"id": b.id, "booking_id": b.booking_id, "status": b.status}})
    
    if b.otp_expiry and b.otp_expiry < datetime.utcnow():
        b.status = "cancelled"
        db.session.commit()
        return jsonify({"success": False, "message": "OTP expired, booking cancelled"}), 400
    
    if b.otp_code != otp_code:
        return jsonify({"success": False, "message": "Incorrect OTP"}), 400
    
    b.status = "confirmed"
    db.session.commit()
    
    return jsonify({"success": True, "message": "Booking confirmed!", "booking": {"id": b.id, "booking_id": b.booking_id, "status": b.status, "date": b.date}})

@app.route("/api/vendor/restaurants/<int:vendor_id>", methods=["GET"])
def get_vendor_restaurants(vendor_id):

    restaurants = Restaurant.query.filter_by(
        vendor_id=vendor_id,
        is_nightlife=False,
        active=True
    ).all()

    data = []

    for r in restaurants:
        data.append({
            "id": r.id,
            "name": r.name,
            "city": r.city,
            "address": r.address,
            "banner": r.banner_image
        })

    return jsonify({
        "success": True,
        "data": data
    })

@app.route("/api/vendor/restaurants/<int:vendor_id>", methods=["DELETE"])
def delete_vendor_restaurant(vendor_id):

    restaurant = Restaurant.query.filter_by(vendor_id=vendor_id).first()

    if not restaurant:
        return jsonify({
            "success": False,
            "message": "Restaurant not found"
        }), 404

    db.session.delete(restaurant)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Restaurant deleted"
    })

@app.route("/api/rest/vendor/<int:vendor_id>/upi", methods=["PUT"])
def update_restaurant_upi(vendor_id):

    data = request.get_json() or {}
    upi_id = data.get("upi_id")

    vendor = Vendor.query.get(vendor_id)

    if not vendor:
        return jsonify({"success": False, "message": "Vendor not found"}), 404

    vendor.upi_id = upi_id

    db.session.commit()

    return jsonify({
        "success": True,
        "upi_id": vendor.upi_id
    })

@app.route("/api/nightlife/restaurants")
def nightlife_restaurants():

    restaurants = Restaurant.query.filter_by(
        is_nightlife=True,
        active=True
    ).all()

    data = []

    for r in restaurants:
        data.append({
            "id": r.id,
            "name": r.name,
            "city": r.city,
            "address": r.address,
            "banner": r.banner_image
        })

    return jsonify({
        "success": True,
        "data": data
    })

@app.route("/api/nightlife/bookings/<int:booking_id>/verify-otp", methods=["POST"])
def nl_verify_booking_otp(booking_id):
    data = request.get_json() or {}
    otp_code = (data.get("otp") or "").strip()
    
    b = NightlifeBooking.query.get(booking_id)
    if not b:
        return jsonify({"success": False, "message": "Booking not found"}), 404
    
    if b.status == "confirmed":
        return jsonify({"success": True, "message": "Already confirmed"})
    
    if b.otp_expiry and b.otp_expiry < datetime.utcnow():
        b.status = "cancelled"
        db.session.commit()
        return jsonify({"success": False, "message": "OTP expired, booking cancelled"}), 400
    
    if b.otp_code != otp_code:
        return jsonify({"success": False, "message": "Incorrect OTP"}), 400
    
    b.status = "confirmed"
    db.session.commit()
    
    return jsonify({"success": True, "message": "Booking confirmed!", "booking": {"id": b.id, "booking_id": b.booking_id, "status": b.status, "date": b.date}})





@app.route("/api/nightlife/closed-dates", methods=["GET"])
def nl_get_closed_dates():
    vendor_id = request.args.get("vendor_id", type=int)
    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400
    closed = NightlifeClosedDate.query.filter_by(vendor_id=vendor_id).all()
    return jsonify({"success": True, "dates": [{"id": c.id, "date": c.closed_date, "reason": c.reason} for c in closed]})

@app.route("/api/nightlife/orders/<int:vendor_id>")
def nightlife_orders(vendor_id):

    orders = db.session.execute(
        text("SELECT * FROM nightlife_orders WHERE vendor_id=:id"),
        {"id": vendor_id}
    ).fetchall()

    return jsonify({"orders": []})

@app.route("/api/nightlife/closed-dates", methods=["POST"])
def nl_add_closed_date():
    vendor_id = request.args.get("vendor_id", type=int)
    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400
    data = request.get_json() or {}
    closed_date = (data.get("date") or "").strip()
    reason = (data.get("reason") or "").strip()
    if not closed_date:
        return jsonify({"success": False, "message": "date required"}), 400
    cd = NightlifeClosedDate(vendor_id=vendor_id, closed_date=closed_date, reason=reason)
    db.session.add(cd)
    db.session.commit()
    return jsonify({"success": True, "message": "Closed date added"})


# ========================
# NIGHTLIFE BOOKING API - VENDOR FACING
# ========================
@app.route("/api/nightlife/types", methods=["GET"])
def nl_get_types():

    vendor_id = request.args.get("vendor_id", type=int)

    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400

    types = NightlifeTableType.query.filter_by(vendor_id=vendor_id).all()

    result = []

    for t in types:

        free_tables = NightlifeTable.query.filter_by(
            vendor_id=vendor_id,
            type_id=t.id,
            status="free"
        ).count()

        result.append({
            "id": t.id,
            "name": t.name,
            "seats": t.seats,
            "total": t.total_tables,
            "price": t.price,
            "start_time": t.start_time,
            "end_time": t.end_time,
            "freeCount": free_tables
        })

    return jsonify({
        "success": True,
        "types": result
    })

@app.route("/api/nightlife/types", methods=["POST"])
def nl_save_type():

    vendor_id = request.args.get("vendor_id", type=int)

    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400

    data = request.get_json() or {}

    try:

        type_id = data.get("id")

        name = (data.get("name") or "").strip()
        seats = int(data.get("seats") or 0)
        total_tables = int(data.get("total_tables") or 0)
        price = int(data.get("price") or 0)
        cancel_hours = int(data.get("cancel_hours") or 2)

        # time values from frontend
        start_time = data.get("start_time") or data.get("start") or data.get("timeStart")
        end_time = data.get("end_time") or data.get("end") or data.get("timeEnd")

        free_tables = int(data.get("freeTables") or 0)

        if free_tables > total_tables:
            free_tables = total_tables

        if not name or seats <= 0 or total_tables <= 0:
            return jsonify({
                "success": False,
                "message": "Invalid type data"
            }), 400


        # ================================
        # UPDATE OR CREATE TYPE
        # ================================

        if type_id:

            t = NightlifeTableType.query.filter_by(
                id=int(type_id),
                vendor_id=vendor_id
            ).first()

            if not t:
                return jsonify({
                    "success": False,
                    "message": "Type not found"
                }), 404

        else:

            t = NightlifeTableType(vendor_id=vendor_id)
            db.session.add(t)


        # ================================
        # SAVE DATA
        # ================================

        t.name = name
        t.seats = seats
        t.total_tables = total_tables
        t.price = price
        t.cancel_hours = cancel_hours

        # ✅ FIXED PART (save time)
        t.start_time = start_time
        t.end_time = end_time

        db.session.commit()


        # ================================
        # CREATE TABLES IF NONE EXIST
        # ================================

        existing = NightlifeTable.query.filter_by(type_id=t.id).count()

        if existing == 0:

            for i in range(total_tables):
                status = "reserved"
                if i < free_tables:
                    status = "free"

                table = NightlifeTable(
                    vendor_id=vendor_id,
                    type_id=t.id,
                    table_number=i + 1,
                    status=status
                )

                db.session.add(table)

            db.session.commit()


        return jsonify({
            "success": True,
            "id": t.id
        })


    except Exception as e:

        print("SAVE TYPE ERROR:", str(e))

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

@app.route("/api/nightlife/types/<int:type_id>/tables", methods=["GET"])
def nl_get_type_tables(type_id):

    vendor_id = request.args.get("vendor_id", type=int)

    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400

    tables = NightlifeTable.query.filter_by(
        vendor_id=vendor_id,
        type_id=type_id
    ).all()

    result = []

    for t in tables:
        result.append({
            "id": t.id,
            "num": t.table_number,
            "status": t.status
        })

    return jsonify({
        "success": True,
        "tables": result
    })

@app.route("/api/nightlife/types/<int:type_id>", methods=["DELETE"])
def nl_delete_type(type_id):

    vendor_id = request.args.get("vendor_id", type=int)

    if not vendor_id:
        return jsonify({
            "success": False,
            "message": "vendor_id required"
        }), 400

    try:

        t = NightlifeTableType.query.filter_by(
            id=type_id,
            vendor_id=vendor_id
        ).first()

        if not t:
            return jsonify({
                "success": False,
                "message": "Type not found"
            }), 404

        # delete tables of this type
        NightlifeTable.query.filter_by(type_id=type_id).delete()

        db.session.delete(t)
        db.session.commit()

        return jsonify({
            "success": True
        })

    except Exception as e:
        print("DELETE TYPE ERROR:", e)

        return jsonify({
            "success": False,
            "message": "Server error"
        }), 500

@app.route("/api/nightlife/tables/mark_all_free", methods=["POST"])
def nl_mark_all_free():

    vendor_id = request.args.get("vendor_id", type=int)
    data = request.get_json() or {}
    print("TYPE DATA RECEIVED:", data)
    type_id = data.get("typeId")

    if not vendor_id or not type_id:
        return jsonify({
            "success": False,
            "message": "vendor_id and typeId required"
        }), 400

    try:

        tables = NightlifeTable.query.filter_by(
            vendor_id=vendor_id,
            type_id=type_id
        ).all()

        for t in tables:
            t.status = "free"

        db.session.commit()

        return jsonify({
            "success": True
        })

    except Exception as e:

        print("MARK FREE ERROR:", e)

        return jsonify({
            "success": False,
            "message": "Server error"
        }), 500

@app.route("/api/nightlife/slots", methods=["GET"])
def nl_get_slots():
    vendor_id = request.args.get("vendor_id", type=int)
    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400
    slots = NightlifeSlot.query.filter_by(vendor_id=vendor_id).all()
    return jsonify({"success": True, "slots": [{"id": s.id, "name": s.name, "start_time": s.start_time, "end_time": s.end_time} for s in slots]})


@app.route("/api/nightlife/slots", methods=["POST"])
def nl_save_slot():
    vendor_id = request.args.get("vendor_id", type=int)
    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400
    data = request.get_json() or {}
    slot_id = data.get("id")
    name = (data.get("name") or "").strip()
    start_time = (data.get("start_time") or "").strip()[:5]
    end_time = (data.get("end_time") or "").strip()[:5]
    if slot_id:
        s = NightlifeSlot.query.filter_by(id=int(slot_id), vendor_id=vendor_id).first()
        if not s:
            return jsonify({"success": False, "message": "Slot not found"}), 404
    else:
        s = NightlifeSlot(vendor_id=vendor_id)
        db.session.add(s)
    s.name = name
    s.start_time = start_time
    s.end_time = end_time
    db.session.commit()
    return jsonify({"success": True, "id": s.id})


@app.route("/api/nightlife/vendor/me")
def nl_vendor_me():
    vendor_id = request.args.get("vendor_id", type=int)
    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400
    v = Vendor.query.get(vendor_id)
    if not v:
        return jsonify({"success": False, "message": "Vendor not found"}), 404
    s = _get_or_create_nightlife_config(vendor_id)
    upcoming = NightlifeBooking.query.filter_by(vendor_id=vendor_id, status="confirmed").count()
    return jsonify({"success": True, "vendor": {"id": v.id, "restaurant_name": v.restaurant_name, "owner_name": v.owner_name, "email": v.email, "phone": v.phone, "address": v.address}, "settings": {"maxAdvanceDays": s.max_advance_days, "cancelBeforeHrs": s.cancel_before_hrs}, "venue_name": s.venue_name, "location": {"addr1": s.addr1, "city": s.city, "state": s.state, "pincode": s.pincode}, "banner": s.banner_url, "stats": {"upcomingBookings": upcoming}})


# Get nightlife vendor menu/items (for restaurant_detail.html)
@app.route("/api/nightlife/vendor/<int:vendor_id>/menu", methods=["GET"])
def nl_vendor_menu(vendor_id):
    """Get menu items for a nightlife vendor"""
    try:
        items = NightlifeItem.query.filter_by(vendor_id=vendor_id).all()
        result = []
        for item in items:
            result.append({
                "id": item.id,
                "item_name": item.item_name,
                "description": item.description,
                "price": item.price,
                "category": item.category,
                "image_url": item.image_url,
                "availability": item.availability
            })
        return jsonify({"success": True, "menu": result})
    except Exception as e:
        print(f"[ERROR] nl_vendor_menu: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/nightlife/analytics", methods=["GET"])
def nightlife_analytics():
    """Return nightlife analytics for vendor dashboard"""

    vendor_id = request.args.get("vendor_id", type=int)

    if not vendor_id:
        return jsonify({
            "success": True,
            "todayOrders": 0,
            "todayRevenue": 0,
            "totalOrders": 0,
            "totalRevenue": 0
        })

    try:

        orders = NightlifeOrder.query.filter_by(vendor_id=vendor_id).all()

        total_orders = len(orders)
        total_revenue = sum(o.total or 0 for o in orders)

        return jsonify({
            "success": True,
            "todayOrders": total_orders,
            "todayRevenue": total_revenue,
            "totalOrders": total_orders,
            "totalRevenue": total_revenue
        })

    except Exception as e:

        print("Nightlife analytics error:", e)

        return jsonify({
            "success": True,
            "todayOrders": 0,
            "todayRevenue": 0,
            "totalOrders": 0,
            "totalRevenue": 0
        })

# Create nightlife order (for restaurant_detail.html)
@app.route("/api/nightlife/order/create", methods=["POST"])
def create_nightlife_order():
    """Create a new nightlife/delivery order"""
    try:
        data = request.get_json() or {}
        vendor_id = data.get("vendor_id")
        items = data.get("items", [])
        
        if not vendor_id or not items:
            return jsonify({"success": False, "message": "vendor_id and items required"}), 400
        
        # Calculate totals
        subtotal = sum(int(item.get("price", 0)) * int(item.get("qty", 1)) for item in items)
        delivery_charge = data.get("delivery_charge", 0)
        packing_charge = data.get("packing_charge", 20)
        total = subtotal + delivery_charge + packing_charge
        
        # Generate order ID
        order_id = f"NL-ORD-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}"
        
        # Create order in online_orders table
        order = NightlifeOrder(
            order_id=order_id,
            vendor_id=vendor_id,
            club_id=data.get("club_id"),
            items_json=json.dumps(items),
            subtotal=subtotal,
            delivery_charge=delivery_charge,
            packing_charge=packing_charge,
            coupon_discount=0,
            total=total,
            payment_method=data.get("payment_method", "COD"),
            payment_status="PENDING",
            coupon_code=None,
            customer_name=data.get("user_name", "Guest"),
            customer_phone=data.get("user_phone", ""),
            customer_email=data.get("user_email", ""),
            delivery_address=data.get("delivery_address", ""),
            status="PENDING"
        )
        db.session.add(order)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "order_id": order.id,
            "order_number": order.order_id,
            "total": total,
            "message": "Order placed successfully"
        })
    except Exception as e:
        db.session.rollback()
        import traceback
        print(f"[ERROR] create_nightlife_order: {e}")
        print(traceback.format_exc())
        return jsonify({"success": False, "message": str(e)}), 500


# ========================
# ORDER CREATE ENDPOINT (New - Step 1)
# ========================
@app.route("/api/orders/create", methods=["POST"])
def create_order():
    """Create a new order with full details"""
    try:
        data = request.get_json() or {}
        
        restaurant_id = data.get("restaurant_id")
        customer_name = data.get("customer_name")
        items = data.get("items")  # array of items
        total = data.get("total")
        payment_status = data.get("payment_status", "paid")
        
        if not restaurant_id or not items:
            return jsonify({"success": False, "message": "restaurant_id and items required"}), 400
        
        # Get vendor_id from restaurant
        restaurant = Restaurant.query.get(restaurant_id)
        vendor_id = restaurant.vendor_id if restaurant else None
        
        # Generate order ID
        order_id = f"ORD-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}"
        
        # Calculate subtotal from items
        subtotal = sum(int(item.get("price", 0)) * int(item.get("qty", 1)) for item in items)
        
        # Create order
        # Create order
        order = OnlineOrder(
            order_id=order_id,
            vendor_id=vendor_id,
            restaurant_id=restaurant_id,
            items_json=json.dumps(items),
            total=total or subtotal,
            payment_status=payment_status.upper(),
            customer_name=customer_name or "Guest",
            status="PENDING"
        )
        
        db.session.add(order)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "order_id": order.id
        })
    except Exception as e:
        db.session.rollback()
        import traceback
        print(f"[ERROR] create_order: {e}")
        print(traceback.format_exc())
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/nightlife/settings", methods=["POST"])
def nl_save_settings():
    vendor_id = request.args.get("vendor_id", type=int)
    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400
    s = _get_or_create_nightlife_config(vendor_id)
    data = request.get_json() or {}
    s.max_advance_days = int(data.get("maxAdvanceDays") or 365)
    s.cancel_before_hrs = int(data.get("cancelBeforeHrs") or 2)
    s.venue_name = (data.get("venue_name") or "").strip()
    db.session.commit()
    return jsonify({"success": True})

@app.route("/api/nightlife/location/auto", methods=["POST"])
def nightlife_location_auto():

    vendor_id = request.args.get("vendor_id", type=int)

    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400

    return jsonify({
        "success": True,
        "message": "Auto location saved"
    })

@app.route("/api/nightlife/location", methods=["POST"])
def nl_save_location():
    vendor_id = request.args.get("vendor_id", type=int)
    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400
    s = _get_or_create_nightlife_config(vendor_id)
    data = request.get_json() or {}
    s.addr1 = (data.get("addr1") or "").strip()
    s.addr2 = (data.get("addr2") or "").strip()
    s.city = (data.get("city") or "").strip()
    s.state = (data.get("state") or "").strip()
    s.pincode = (data.get("pincode") or "").strip()
    db.session.commit()
    return jsonify({"success": True})


@app.route("/api/nightlife/banner", methods=["POST"])
def nl_upload_banner():
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
    new_name = f"nl_banner_{vendor_id}_{int(datetime.utcnow().timestamp())}_{filename}".replace(" ", "_")
    path = os.path.join(app.config["UPLOAD_FOLDER"], new_name)
    file.save(path)
    s = _get_or_create_nightlife_config(vendor_id)
    s.banner_url = f"/uploads/{new_name}"
    db.session.commit()
    return jsonify({"success": True, "bannerUrl": s.banner_url})


# ========================
# ANALYTICS
# ========================
@app.route("/api/vendor/analytics/<int:vendor_id>", methods=["GET"])
def vendor_analytics(vendor_id):
    vendor = Vendor.query.get(vendor_id)
    if not vendor:
        return jsonify({"success": False, "message": "Vendor not found"}), 404
    
    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    if vendor.vendor_type == "nightlife":
        bookings_query = NightlifeBooking
    else:
        bookings_query = RestBooking
    
    daily_revenue = db.session.query(func.sum(bookings_query.price)).filter(
        bookings_query.vendor_id == vendor_id,
        bookings_query.status == "confirmed",
        bookings_query.created_at >= datetime.combine(today, datetime.min.time())
    ).scalar() or 0
    
    weekly_revenue = db.session.query(func.sum(bookings_query.price)).filter(
        bookings_query.vendor_id == vendor_id,
        bookings_query.status == "confirmed",
        bookings_query.created_at >= datetime.combine(week_ago, datetime.min.time())
    ).scalar() or 0
    
    monthly_revenue = db.session.query(func.sum(bookings_query.price)).filter(
        bookings_query.vendor_id == vendor_id,
        bookings_query.status == "confirmed",
        bookings_query.created_at >= datetime.combine(month_ago, datetime.min.time())
    ).scalar() or 0
    
    total_revenue = db.session.query(func.sum(bookings_query.price)).filter(
        bookings_query.vendor_id == vendor_id,
        bookings_query.status == "confirmed"
    ).scalar() or 0
    
    upcoming_bookings = bookings_query.filter(
        bookings_query.vendor_id == vendor_id,
        bookings_query.status == "confirmed",
        bookings_query.date >= today.strftime("%Y-%m-%d")
    ).count()
    
    graph_data = []
    for i in range(30):
        d = today - timedelta(days=29-i)
        day_revenue = db.session.query(func.sum(bookings_query.price)).filter(
            bookings_query.vendor_id == vendor_id,
            bookings_query.status == "confirmed",
            bookings_query.created_at >= datetime.combine(d, datetime.min.time()),
            bookings_query.created_at < datetime.combine(d + timedelta(days=1), datetime.min.time())
        ).scalar() or 0
        graph_data.append({"date": d.strftime("%Y-%m-%d"), "revenue": day_revenue})
    
    return jsonify({"success": True, "analytics": {
        "daily_revenue": daily_revenue,
        "weekly_revenue": weekly_revenue,
        "monthly_revenue": monthly_revenue,
        "total_revenue": total_revenue,
        "upcoming_bookings": upcoming_bookings,
        "graph_data": graph_data,
        "vendor_type": vendor.vendor_type
    }})


# ========================
# ADMIN
# ========================
@app.route("/api/admin/overview")
def admin_overview():
    try:
        users_count = User.query.count()
    except:
        users_count = 0
    try:
        vendors_count = Vendor.query.count()
    except:
        vendors_count = 0
    try:
        rest_bookings_count = RestBooking.query.count()
    except:
        rest_bookings_count = 0
    try:
        nightlife_bookings_count = NightlifeBooking.query.count()
    except:
        nightlife_bookings_count = 0
    return jsonify({
        "users": users_count, 
        "vendors": vendors_count, 
        "rest_bookings": rest_bookings_count, 
        "nightlife_bookings": nightlife_bookings_count
    })


@app.route("/api/admin/nightlife/analytics")
def admin_nightlife_analytics():
    """Admin analytics for nightlife"""
    try:
        total_bookings = NightlifeBooking.query.count()
        confirmed_bookings = NightlifeBooking.query.filter_by(status="confirmed").count()
        total_revenue = db.session.query(func.sum(NightlifeBooking.total_price)).filter(
            NightlifeBooking.status == "confirmed"
        ).scalar() or 0
        active_vendors = Vendor.query.filter_by(vendor_type="nightlife").count()
        
        today = datetime.utcnow().date()
        daily_data = []
        for i in range(30):
            d = today - timedelta(days=29-i)
            count = NightlifeBooking.query.filter(
                NightlifeBooking.created_at >= datetime.combine(d, datetime.min.time()),
                NightlifeBooking.created_at < datetime.combine(d + timedelta(days=1), datetime.min.time())
            ).count()
            daily_data.append({"date": d.strftime("%Y-%m-%d"), "bookings": count})
        
        return jsonify({
            "success": True,
            "total_bookings": total_bookings,
            "confirmed_bookings": confirmed_bookings,
            "total_revenue": total_revenue,
            "active_vendors": active_vendors,
            "daily_bookings": daily_data
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ========================
# RESTAURANT/CLUB LEGACY ROUTES
# ========================
@app.route("/food/restaurants", methods=["GET"])
def food_restaurants():
    restaurants = Restaurant.query.filter_by(active=True).all()
    result = []
    for r in restaurants:
        cfg = RestaurantConfig.query.filter_by(restaurant_id=r.id).first()
        result.append({"id": r.id, "vendor_id": r.vendor_id, "name": r.name, "address": r.address, "description": r.description, "banner_image": r.banner_image, "delivery_charge": cfg.delivery_charge if cfg else 0, "packing_charge": cfg.packing_charge if cfg else 0})
    return jsonify(result)

@app.route("/api/restaurant/<int:restaurant_id>")
def get_single_restaurant(restaurant_id):
    r = Restaurant.query.get(restaurant_id)
    if not r:
        return jsonify({"success": False, "message": "Restaurant not found"}), 404
    cfg = RestaurantConfig.query.filter_by(restaurant_id=r.id).first()
    return jsonify({"success": True, "restaurant": {"id": r.id, "vendor_id": r.vendor_id, "name": r.name, "address": r.address, "description": r.description, "banner_image": r.banner_image, "delivery_charge": cfg.delivery_charge if cfg else 0, "packing_charge": cfg.packing_charge if cfg else 0}})

@app.route("/api/vendor/restaurants", methods=["POST"])
def create_or_update_restaurant():
    data = request.get_json() or {}
    vendor_id = data.get("vendor_id")
    try:
        vendor_id = int(vendor_id)
    except:
        return jsonify({"success": False, "message": "Invalid vendor_id"}), 400
    name = (data.get("name") or "").strip()
    address = (data.get("address") or "").strip()
    if not name or not address:
        return jsonify({"success": False, "message": "name & address required"}), 400
    rest_id = data.get("restaurant_id")
    if rest_id:
        r = Restaurant.query.get(int(rest_id))
        if not r or r.vendor_id != vendor_id:
            return jsonify({"success": False, "message": "Restaurant not found"}), 404
    else:
        r = Restaurant(vendor_id=vendor_id, name=name, address=address)
        db.session.add(r)
        db.session.commit()
    if "banner_image" in data and data["banner_image"]:
        r.banner_image = data["banner_image"]
    r.description = data.get("description", "")
    r.is_nightlife = data.get("is_nightlife", False)
    db.session.commit()
    return jsonify({"success": True, "restaurant_id": r.id})

# PUT endpoint to update existing restaurant
@app.route("/api/vendors/<int:vendor_id>", methods=["PUT"])
def update_vendor(vendor_id):

    data = request.get_json()

    vendor = Vendor.query.get(vendor_id)

    if not vendor:
        return jsonify({"success":False,"message":"Vendor not found"}),404

    vendor.restaurant_name = data.get("restaurant_name",vendor.restaurant_name)
    vendor.owner_name = data.get("owner_name",vendor.owner_name)
    vendor.email = data.get("email",vendor.email)
    vendor.phone = data.get("phone",vendor.phone)
    vendor.address = data.get("address",vendor.address)
    vendor.upi_id = data.get("upi_id",vendor.upi_id)

    db.session.commit()

    return jsonify({"success":True})

@app.route("/api/vendor/restaurants/<int:restaurant_id>", methods=["DELETE"])
def delete_restaurant(restaurant_id):
    '''
    Delete a restaurant.
    Verifies vendor owns the restaurant before deleting.
    '''
    data = request.get_json() or {}
    vendor_id = data.get("vendor_id")
    
    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400
    
    try:
        vendor_id = int(vendor_id)
    except:
        return jsonify({"success": False, "message": "Invalid vendor_id"}), 400
    
    # Find the restaurant
    r = Restaurant.query.get(restaurant_id)
    if not r:
        return jsonify({"success": False, "message": "Restaurant not found"}), 404
    
    # Verify vendor owns the restaurant
    if r.vendor_id != vendor_id:
        return jsonify({"success": False, "message": "Not authorized to delete this restaurant"}), 403
    
    try:
        # Soft delete - set active to False
        r.active = False
        db.session.commit()
        return jsonify({
            "success": True,
            "message": "Restaurant deleted successfully"
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/vendor/restaurants/create", methods=["POST"])
def create_restaurant():

    data = request.json

    vendor_id = data.get("vendor_id")
    name = data.get("name")
    city = data.get("city")
    address = data.get("address")

    r = Restaurant(
        vendor_id=vendor_id,
        name=name,
        city=city,
        address=address
    )

    db.session.add(r)
    db.session.commit()

    return jsonify({
        "success": True,
        "restaurant_id": r.id
    })

@app.route("/api/vendor/restaurants/<int:restaurant_id>", methods=["PUT"])
def update_restaurant(restaurant_id):
    '''
    Update an existing restaurant.
    Verifies vendor owns the restaurant before updating.
    '''
    data = request.get_json() or {}
    vendor_id = data.get("vendor_id")
    
    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400
    
    try:
        vendor_id = int(vendor_id)
    except:
        return jsonify({"success": False, "message": "Invalid vendor_id"}), 400
    
    # Find the restaurant
    r = Restaurant.query.get(restaurant_id)
    if not r:
        return jsonify({"success": False, "message": "Restaurant not found"}), 404
    
    # Verify vendor owns the restaurant
    if r.vendor_id != vendor_id:
        return jsonify({"success": False, "message": "Not authorized to update this restaurant"}), 403
    
    # Update fields
    if "name" in data and data["name"]:
        r.name = data["name"]
    if "address" in data:
        r.address = data["address"]
    if "description" in data:
        r.description = data["description"]
    if "banner_image" in data:
        r.banner_image = data["banner_image"]
    if "is_nightlife" in data:
        r.is_nightlife = data["is_nightlife"]
    
    try:
        db.session.commit()
        return jsonify({
            "success": True,
            "message": "Restaurant updated successfully",
            "restaurant_id": r.id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/vendor/restaurants", methods=["GET"])
def list_vendor_restaurants():
    """Get all restaurants for a vendor by vendor_id query param"""
    vendor_id = request.args.get("vendor_id", type=int)
    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400
    
    restaurants = Restaurant.query.filter_by(
        vendor_id=vendor_id,
        active=True,
        is_nightlife=False
    ).all()
    result = []
    for r in restaurants:
        cfg = RestaurantConfig.query.filter_by(restaurant_id=r.id).first()
        result.append({
            "id": r.id, 
            "vendor_id": r.vendor_id,
            "name": r.name, 
            "address": r.address, 
            "description": r.description,
            "banner_image": r.banner_image, 
            "delivery_charge": cfg.delivery_charge if cfg else 0, 
            "packing_charge": cfg.packing_charge if cfg else 0,
            "is_nightlife": r.is_nightlife
        })
    return jsonify({"success": True, "data": result})

@app.route("/api/vendor/restaurants/<int:restaurant_id>/menu-item", methods=["POST"])
def add_menu_item(restaurant_id):
    data = get_data()
    r = Restaurant.query.get(restaurant_id)
    if not r:
        # Check if this is actually a vendor_id
        vendor = Vendor.query.get(restaurant_id)
        if vendor:
            # Create a restaurant for this vendor
            r = Restaurant(
                vendor_id=vendor.id,
                name=vendor.restaurant_name,
                address=vendor.address,
                is_nightlife=(vendor.vendor_type == "nightlife")
            )
            db.session.add(r)
            db.session.commit()
        else:
            return jsonify({"success": False, "message": "Restaurant not found"}), 404
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"success": False, "message": "name required"}), 400
    try:
        price = int(str(data.get("price")))
    except:
        return jsonify({"success": False, "message": "Invalid price"}), 400
    
    # Handle image upload if file is present in request
    image_url = (data.get("image_url") or "").strip() or None
    
    item = MenuItem(restaurant_id=r.id, name=name, description=(data.get("description") or "").strip(), price=price, category=(data.get("category") or "").strip(), food_type=(data.get("food_type") or "").strip(), available=bool(data.get("available")) if data.get("available") is not None else True, image_url=image_url)
    db.session.add(item)
    db.session.commit()
    return jsonify({"success": True, "item_id": item.id})

# Menu Item Image Upload Endpoint
@app.route("/api/vendor/menu-item/upload-image", methods=["POST"])
def upload_menu_item_image():
    '''
    Upload an image for a menu item.
    Saves to /uploads/ folder and returns the file path.
    '''
    try:
        vendor_id = request.args.get("vendor_id")
        if not vendor_id:
            return jsonify({"success": False, "message": "vendor_id required"}), 400
        
        if "image" not in request.files:
            return jsonify({"success": False, "message": "No image file"}), 400
        
        file = request.files["image"]
        if not file or file.filename == "":
            return jsonify({"success": False, "message": "Empty file"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({"success": False, "message": "Invalid file type"}), 400
        
        filename = secure_filename(file.filename)
        # Generate unique filename: menu_{vendor_id}_{timestamp}_{original_name}
        new_name = f"menu_{vendor_id}_{int(datetime.utcnow().timestamp())}_{filename}".replace(" ", "_")
        path = os.path.join(app.config["UPLOAD_FOLDER"], new_name)
        file.save(path)
        
        # Return the path that can be stored in DB
        return jsonify({
            "success": True,
            "image_url": f"/uploads/{new_name}",
            "filename": new_name,
            "message": "Image uploaded successfully"
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/vendor/restaurants/<int:restaurant_id>/menu", methods=["GET"])
def list_menu_items(restaurant_id):
    items = MenuItem.query.filter_by(restaurant_id=restaurant_id).all()
    result = []
    for i in items:
        result.append({"id": i.id, "name": i.name, "description": i.description, "price": i.price, "category": i.category, "food_type": i.food_type, "available": i.available, "image_url": i.image_url})
    return jsonify(result)

# ========================
# NEW: MENU ITEM PUT/DELETE APIs
# ========================

@app.route("/api/vendor/menu-item/<int:item_id>", methods=["PUT"])
def update_menu_item(item_id):

    data = get_data()

    vendor_id = data.get("vendor_id") or request.args.get("vendor_id")

    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400

    try:
        vendor_id = int(vendor_id)
    except:
        return jsonify({"success": False, "message": "Invalid vendor_id"}), 400


    # Get menu item
    item = MenuItem.query.get(item_id)

    if not item:
        return jsonify({"success": False, "message": "Item not found"}), 404


    # Get restaurant
    restaurant = Restaurant.query.get(item.restaurant_id)

    if not restaurant or restaurant.vendor_id != vendor_id:
        return jsonify({"success": False, "message": "Unauthorized"}), 403


    # Update fields safely
    if "name" in data:
        item.name = data["name"]

    if "price" in data:
        item.price = data["price"]

    if "description" in data:
        item.description = data["description"]

    if "category" in data:
        item.category = data["category"]

    if "food_type" in data:
        item.food_type = data["food_type"]

    if "image_url" in data:
        item.image_url = data["image_url"]

    if "offer_percent" in data:
        item.offer_percent = data["offer_percent"]

    if "available" in data:
        item.available = data["available"]

    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Menu item updated"
    })

@app.route("/api/vendor/menu-item", methods=["POST"])
def add_nightlife_item():

    data = request.get_json() or {}

    vendor_id = data.get("vendor_id")

    vendor = Vendor.query.get(vendor_id)

    # SECURITY CHECK
    if not vendor or vendor.vendor_type != "nightlife":
        return jsonify({
            "success": False,
            "message": "Only nightlife vendors can add drinks"
        }), 403

    item = NightlifeItem(
        vendor_id=vendor_id,
        item_name=data.get("name"),
        description=data.get("description"),
        price=data.get("price"),
        category=data.get("category"),
        image_url=data.get("image_url"),
        availability="Available"
    )

    db.session.add(item)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Nightlife item added"
    })

@app.route("/api/vendor/menu-item/<int:item_id>", methods=["DELETE"])
def delete_menu_item(item_id):

    try:
        vendor_id = request.args.get("vendor_id")

        if not vendor_id:
            return jsonify({
                "success": False,
                "message": "vendor_id required"
            }), 400

        item = MenuItem.query.get(item_id)

        if not item:
            return jsonify({
                "success": False,
                "message": "Item not found"
            }), 404

        db.session.delete(item)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Item deleted"
        })

    except Exception as e:
        print("DELETE ITEM ERROR:", e)
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@app.route("/api/order/place", methods=["POST"])
def place_delivery_order():
    try:
        data = request.get_json(force=True)

        restaurant_id = data.get("restaurant_id")
        vendor_id = data.get("vendor_id")
        items = data.get("items", [])

        if not items:
            return jsonify({"success": False, "message": "No items"}), 400

        items_json = json.dumps(items)

        address = data.get("address", {})

        # safer extraction
        customer_name = data.get("customer_name") or address.get("name")
        customer_phone = data.get("customer_phone") or address.get("phone")

        order = DeliveryOrder(
            vendor_id=vendor_id,
            restaurant_id=restaurant_id,
            items_json=items_json,
            subtotal=data.get("subtotal", 0),
            delivery_charge=data.get("delivery_charge", 0),
            packing_charge=data.get("packing_charge", 0),
            total=data.get("total", 0),

            user_name=customer_name,
            user_phone=customer_phone,

            address_line1=address.get("line1"),
            address_line2=address.get("line2"),
            landmark=address.get("landmark"),
            city=address.get("city"),
            state=address.get("state"),
            pincode=address.get("pincode"),

            payment_method=data.get("payment_method"),
            payment_status=data.get("payment_status", "UNPAID"),
            status="PENDING"
        )

        db.session.add(order)
        db.session.commit()

        return jsonify({
            "success": True,
            "order_id": order.id
        })

    except Exception as e:
        print("ORDER ERROR:", e)
        return jsonify({"success": False, "message": str(e)}), 500

@app.get("/api/orders/user/<phone>")
def get_user_orders(phone):
    """
    Get all orders for a user (combines DeliveryOrder and OnlineOrder).
    """
    phone = (phone or "").strip()
    result = []
    
    # Get DeliveryOrder items
    delivery_orders = DeliveryOrder.query.filter_by(user_phone=phone).order_by(DeliveryOrder.id.desc()).all()
    for o in delivery_orders:
        r = Restaurant.query.get(o.restaurant_id)
        result.append({
            "id": o.id,
            "order_id": o.id,
            "order_number": f"DEL-{o.id}",
            "order_type": "delivery",
            "restaurant_name": r.name if r else "Unknown",
            "restaurant_id": o.restaurant_id,
            "items": json.loads(o.items_json) if o.items_json else [],
            "subtotal": o.subtotal,
            "delivery_charge": o.delivery_charge,
            "packing_charge": o.packing_charge,
            "total": o.total,
            "payment_method": o.payment_method,
            "payment_status": o.payment_status,
            "status": o.status,
            "created_at": o.created_at.isoformat() if o.created_at else None
        })
    
    # Get OnlineOrder items
    online_orders = OnlineOrder.query.filter_by(customer_phone=phone).order_by(OnlineOrder.id.desc()).all()
    for o in online_orders:
        v = Vendor.query.get(o.vendor_id)
        result.append({
            "id": o.id,
            "order_id": o.id,
            "order_number": o.order_id,
            "order_type": "online",
            "restaurant_name": v.restaurant_name if v else "Unknown",
            "restaurant_id": o.vendor_id,
            "items": json.loads(o.items_json) if o.items_json else [],
            "subtotal": o.subtotal,
            "delivery_charge": o.delivery_charge,
            "packing_charge": o.packing_charge,
            "total": o.total,
            "payment_method": o.payment_method,
            "payment_status": o.payment_status,
            "status": o.status,
            "created_at": o.created_at.isoformat() if o.created_at else None
        })
    
    # Sort by created_at descending
    result.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return jsonify({"success": True, "data": result})

@app.route("/api/vendor/delivery-orders/<int:vendor_id>")
def get_vendor_delivery_orders(vendor_id):

    orders = DeliveryOrder.query.filter_by(vendor_id=vendor_id).all()

    result = []

    for o in orders:
        result.append({
            "id": o.id,
            "vendor_id": o.vendor_id,
            "restaurant_id": o.restaurant_id,
            "status": o.status,
            "total": o.total,
            "payment_status": o.payment_status,
            "created_at": o.created_at
        })

    return jsonify({
        "success": True,
        "orders": result
    })

@app.route("/api/vendor/delivery-orders/<int:vendor_id>")
def vendor_delivery_orders(vendor_id):

    orders = OnlineOrder.query.filter_by(
        vendor_id=vendor_id
    ).order_by(OnlineOrder.created_at.desc()).all()

    result = []

    for o in orders:
        result.append({
            "id": o.id,
            "vendor_id": o.vendor_id,
            "restaurant_id": o.restaurant_id,
            "items": json.loads(o.items_json or "[]"),
            "total": o.total,
            "status": o.status,
            "payment_status": o.payment_status,
            "customer_name": o.customer_name,
            "customer_phone": o.customer_phone,
            "delivery_address": o.delivery_address,
            "created_at": o.created_at.isoformat() if o.created_at else None
        })

    return jsonify({
        "success": True,
        "orders": result
    })

@app.post("/api/vendor/delivery-orders/<int:order_id>/status")
def update_delivery_status(order_id):

    data = get_data()
    status = (data.get("status") or "").strip().upper()

    allowed = ["PENDING","PREPARING","OUT_FOR_DELIVERY","DELIVERED","CANCELLED"]

    if status not in allowed:
        return jsonify({"success": False, "message": "Invalid status"}), 400


    order = DeliveryOrder.query.get(order_id)

    if not order:
        return jsonify({"success": False, "message": "Order not found"}), 404


    order.status = status
    db.session.commit()

    return jsonify({"success": True})
    
@app.route("/nightlife/clubs")
def nightlife_club_list():
    clubs = Club.query.all()
    result = []
    for c in clubs:
        img = ClubImage.query.filter_by(club_id=c.id).first()
        thumb = img.image_url if img else "/Images/default.jpg"
        result.append({"club_id": c.id, "vendor_id": c.vendor_id, "club_name": c.club_name, "location": c.location, "music": c.music, "image": thumb})
    return jsonify(result)

@app.route("/user/club/<int:club_id>")
def user_club(club_id):
    c = Club.query.get(club_id)
    if not c:
        return jsonify({"error": "Club not found"}), 404
    imgs = ClubImage.query.filter_by(club_id=club_id).all()
    return jsonify({"club": {"id": c.id, "vendor_id": c.vendor_id, "name": c.club_name, "location": c.location, "music": c.music, "dress": c.dress, "description": c.description, "images": [i.image_url for i in imgs]}})

@app.route("/rating/add", methods=["POST"])
def add_rating():
    data = get_data()
    try:
        club_id = int(data.get("club_id"))
        stars = int(data.get("stars"))
    except:
        return jsonify({"ok": False, "error": "Invalid data"}), 400
    r = Rating(club_id=club_id, user_name=(data.get("name") or "Anonymous").strip(), stars=stars, comment=(data.get("comment") or "").strip())
    db.session.add(r)
    db.session.commit()
    return jsonify({"ok": True})

@app.route("/rating/club/<int:club_id>")
def get_ratings(club_id):
    ratings = Rating.query.filter_by(club_id=club_id).all()
    if not ratings:
        return jsonify({"avg": 0, "count": 0, "items": []})
    avg = round(sum([r.stars for r in ratings]) / len(ratings), 1)
    return jsonify({"avg": avg, "count": len(ratings), "items": [{"name": r.user_name, "stars": r.stars, "comment": r.comment} for r in ratings]})

@app.get("/vendor/find/<int:vendor_id>")
def legacy_vendor_find(vendor_id):
    v = Vendor.query.get(vendor_id)
    if not v:
        return jsonify({"ok": False, "message": "Vendor not found"}), 404
    return jsonify({"ok": True, "vendor": {"id": v.id, "restaurant_name": v.restaurant_name, "owner_name": v.owner_name, "email": v.email, "phone": v.phone, "address": v.address, "vendor_type": v.vendor_type}})

# ========================
# VENDOR ONLINE ORDERING APIs (For vendor_order_online.html)
# ========================

# Get vendor's clubs/restaurants
@app.route("/vendor/getClubs/<int:vendorId>", methods=["GET"])
def get_vendor_clubs(vendorId):
    """Get all clubs/restaurants for a vendor"""
    try:
        restaurants = Restaurant.query.filter_by(vendor_id=vendorId, active=True).all()
        result = []
        for r in restaurants:
            cfg = RestaurantConfig.query.filter_by(restaurant_id=r.id).first()
            result.append({
                "id": r.id,
                "vendor_id": r.vendor_id,
                "name": r.name,
                "address": r.address,
                "description": r.description,
                "banner_image": r.banner_image,
                "delivery_charge": cfg.delivery_charge if cfg else 0,
                "packing_charge": cfg.packing_charge if cfg else 0,
                "is_nightlife": r.is_nightlife
            })
        return jsonify({"success": True, "clubs": result})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# Create new club/restaurant
@app.route("/vendor/addClub", methods=["POST"])
def add_club():
    """Create a new club/restaurant"""
    try:
        data = request.get_json() or {}
        vendor_id = data.get("vendor_id")
        name = data.get("club_name") or data.get("name", "")
        address = data.get("location") or data.get("address", "")
        description = data.get("description", "")
        music = data.get("music", "")
        dress = data.get("dress", "")
        
        if not vendor_id or not name or not address:
            return jsonify({"success": False, "message": "vendor_id, name, address required"}), 400
        
        # Check if it's a nightlife venue
        is_nightlife = data.get("is_nightlife", False)
        
        restaurant = Restaurant(
            vendor_id=vendor_id,
            name=name,
            address=address,
            description=description,
            is_nightlife=is_nightlife,
            banner_image=data.get("banner_image"),
            active=True
        )
        db.session.add(restaurant)
        db.session.commit()
        
        # Create restaurant config
        cfg = RestaurantConfig(
            restaurant_id=restaurant.id,
            delivery_charge=data.get("delivery_charge", 0),
            packing_charge=data.get("packing_charge", 0)
        )
        db.session.add(cfg)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "club_id": restaurant.id,
            "message": "Club created successfully"
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500
@app.route("/api/restaurants/<int:restaurant_id>", methods=["GET"])
def get_restaurant(restaurant_id):
    try:
        rest = Restaurant.query.get(restaurant_id)

        if not rest:
            return jsonify({"success": False, "message": "Restaurant not found"}), 404

        return jsonify({
            "success": True,
            "restaurant": {
                "id": rest.id,
                "name": rest.name,
                "address": rest.address,
                "vendor_id": rest.vendor_id,   # ← THIS MUST EXIST
                "delivery_charge": rest.delivery_charge,
                "packing_charge": rest.packing_charge,
                "banner_image": rest.banner_image
            }
        })

    except Exception as e:
        print("Restaurant API error:", e)
        return jsonify({"success": False, "message": str(e)}), 500
# Update club/restaurant
@app.route("/vendor/updateClub/<int:clubId>", methods=["PUT"])
def update_club(clubId):
    """Update club/restaurant details"""
    try:
        data = request.get_json() or {}
        restaurant = Restaurant.query.get(clubId)
        if not restaurant:
            return jsonify({"success": False, "message": "Club not found"}), 404
        
        if data.get("club_name"):
            restaurant.name = data["club_name"]
        if data.get("location") or data.get("address"):
            restaurant.address = data.get("location") or data["address"]
        if data.get("description"):
            restaurant.description = data["description"]
        if data.get("banner_image"):
            restaurant.banner_image = data["banner_image"]
        
        db.session.commit()
        
        # Update config if provided
        if "delivery_charge" in data or "packing_charge" in data:
            cfg = RestaurantConfig.query.filter_by(restaurant_id=clubId).first()
            if cfg:
                if "delivery_charge" in data:
                    cfg.delivery_charge = data["delivery_charge"]
                if "packing_charge" in data:
                    cfg.packing_charge = data["packing_charge"]
                db.session.commit()
        
        return jsonify({"success": True, "message": "Club updated successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

# Upload club images
@app.route("/vendor/uploadClubImages/<int:clubId>", methods=["POST"])
def upload_club_images(clubId):
    """Upload images for a club"""
    try:
        restaurant = Restaurant.query.get(clubId)
        if not restaurant:
            return jsonify({"success": False, "message": "Club not found"}), 404
        
        if "image" not in request.files:
            return jsonify({"success": False, "message": "No image file"}), 400
        
        file = request.files["image"]
        if not file or file.filename == "":
            return jsonify({"success": False, "message": "Empty file"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({"success": False, "message": "Invalid file type"}), 400
        
        filename = secure_filename(file.filename)
        new_name = f"club_{clubId}_{int(datetime.utcnow().timestamp())}_{filename}".replace(" ", "_")
        path = os.path.join(app.config["UPLOAD_FOLDER"], new_name)
        file.save(path)
        
        # Update restaurant banner
        restaurant.banner_image = f"/uploads/{new_name}"
        db.session.commit()
        
        return jsonify({
            "success": True,
            "image_url": f"/uploads/{new_name}",
            "message": "Image uploaded successfully"
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
# ==========================
# USER NIGHTLIFE BOOKINGS
# ==========================

@app.route("/nightlife/user/bookings/<int:user_id>", methods=["GET"])
def get_user_nightlife_bookings(user_id):
    try:
        # Check if user exists
        user = User.query.filter_by(id=user_id).first()

        if not user:
            return jsonify({
                "success": False,
                "message": "User not found"
            }), 404

        # Fetch bookings using user's phone
        bookings = NightlifeBooking.query.filter_by(
            customer_phone=user.phone
        ).order_by(NightlifeBooking.created_at.desc()).all()

        results = []

        for booking in bookings:
            vendor = Vendor.query.filter_by(id=booking.vendor_id).first()

            results.append({
                "booking_id": booking.booking_id,
                "vendor_id": booking.vendor_id,
                "club_name": vendor.restaurant_name if vendor else "Unknown Club",
                "booking_date": booking.booking_date,
                "slot_id": booking.slot_id,
                "tables": booking.table_numbers,
                "total_price": booking.total_price,
                "status": booking.status
            })

        return jsonify({
            "success": True,
            "data": results
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500
# Get nightlife items for a vendor

@app.route("/vendor/getNightlifeItems/<int:vendorId>", methods=["GET"])
def get_nightlife_items(vendorId):

    try:
        vendor = Vendor.query.get(vendorId)

        if not vendor:
            return jsonify({
                "success": False,
                "message": "Vendor not found",
                "items": []
            }), 404

        if vendor.vendor_type != "nightlife":
            return jsonify({
                "success": False,
                "message": "Not a nightlife vendor",
                "items": []
            }), 403

        items = NightlifeItem.query.filter_by(vendor_id=vendorId).order_by(
            NightlifeItem.created_at.desc()
        ).all()

        result = []

        for item in items:
            result.append({
                "id": item.id,
                "vendor_id": item.vendor_id,
                "club_id": item.club_id,
                "item_name": item.item_name,
                "description": item.description,
                "price": item.price,
                "category": item.category,
                "image_url": item.image_url,
                "availability": item.availability,
                "created_at": item.created_at.isoformat() if item.created_at else None
            })

        return jsonify({
            "success": True,
            "items": result
        })

    except Exception as e:
        import traceback
        print("[ERROR] get_nightlife_items:", e)
        print(traceback.format_exc())

        return jsonify({
            "success": False,
            "items": []
        }), 500
# Add nightlife item
@app.route("/api/nightlife/items", methods=["POST"])
def create_nightlife_item():

    

    try:
        data = request.json

        vendor_id = session.get("vendor_id")

        item = NightlifeItem(
            vendor_id=vendor_id,
            club_id=data.get("club_id"),
            item_name=data.get("name"),
            description=data.get("description"),
            price=data.get("price"),
            category=data.get("category"),
            image_url=data.get("image_url"),
            availability="Available"
        )

        db.session.add(item)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Item added successfully",
            "item_id": item.id
        })

    except Exception as e:
        import traceback
        print("[ERROR] create_nightlife_item:", e)
        print(traceback.format_exc())

        return jsonify({
            "success": False,
            "message": "Failed to create item"
        }), 500
# Edit nightlife item
@app.route("/vendor/editNightlifeItem/<int:itemId>", methods=["PUT"])
def edit_nightlife_item(itemId):
    """Edit a nightlife item"""
    try:
        data = request.get_json() or {}
        item = NightlifeItem.query.get(itemId)
        if not item:
            return jsonify({"success": False, "message": "Item not found"}), 404
        
        if data.get("item_name"):
            item.item_name = data["item_name"]
        if data.get("description") is not None:
            item.description = data["description"]
        if data.get("price") is not None:
            item.price = int(data["price"])
        if data.get("category"):
            item.category = data["category"]
        if data.get("image_url"):
            item.image_url = data["image_url"]
        if data.get("availability"):
            item.availability = data["availability"]
        
        db.session.commit()
        
        return jsonify({"success": True, "message": "Item updated successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

# Delete nightlife item
@app.route("/vendor/deleteNightlifeItem/<int:itemId>", methods=["DELETE"])
def delete_nightlife_item(itemId):
    """Delete a nightlife item"""
    try:
        item = NightlifeItem.query.get(itemId)
        if not item:
            return jsonify({"success": False, "message": "Item not found"}), 404
        
        db.session.delete(item)
        db.session.commit()
        
        return jsonify({"success": True, "message": "Item deleted successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

# Get vendor online orders
@app.route("/api/vendor/orders/<int:vendorId>", methods=["GET"])
def get_vendor_online_orders(vendorId):
    """Get all online orders for a vendor"""
    try:
        orders = OnlineOrder.query.filter_by(vendor_id=vendorId).order_by(OnlineOrder.created_at.desc()).all()
        result = []

        for order in orders:

            # Safely parse items_json
            try:
                items = json.loads(order.items_json) if order.items_json else []
            except Exception:
                items = []

            result.append({
                "id": order.id,
                "order_id": order.order_id,
                "vendor_id": order.vendor_id,
                "restaurant_id": order.restaurant_id,
                "items": items,
                "subtotal": order.subtotal,
                "delivery_charge": order.delivery_charge,
                "packing_charge": order.packing_charge,
                "coupon_discount": order.coupon_discount,
                "total": order.total,
                "payment_method": order.payment_method,
                "payment_status": order.payment_status,
                "customer_name": order.customer_name,
                "customer_phone": order.customer_phone,
                "customer_email": order.customer_email,
                "delivery_address": order.delivery_address,
                "status": order.status,
                "created_at": order.created_at.isoformat() if order.created_at else None
            })

        return jsonify({
            "success": True,
            "orders": result
        })

    except Exception as e:
        print("VENDOR ORDERS ERROR:", e)
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# ========================
# VENDOR ORDERS BY RESTAURANT (New - Step 2)
# ========================
# NOTE: The duplicate route /api/vendor/orders/<int:vendor_id> was removed
# to fix Flask conflicts. Use /api/vendor/orders/<int:vendorId> instead.
@app.route("/api/vendor/orders/<int:orderId>/status", methods=["PUT", "POST"])
def update_order_status(orderId):
    """Update order status"""
    try:
        data = get_data()
        status = data.get("status")
        
        if not status:
            return jsonify({"success": False, "message": "status required"}), 400
        
        order = OnlineOrder.query.get(orderId)
        if not order:
            return jsonify({"success": False, "message": "Order not found"}), 404
        
        order.status = str(status).upper()
        db.session.commit()
        
        return jsonify({"success": True, "message": "Order status updated"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

# Place online order
@app.route("/api/vendor/orders/place", methods=["POST"])
def place_online_order():
    """Place a new online order"""
    try:
        data = request.get_json() or {}
        vendor_id = data.get("vendor_id")
        items = data.get("items", [])
        
        if not vendor_id or not items:
            return jsonify({"success": False, "message": "vendor_id and items required"}), 400
        
        # Calculate totals
        subtotal = sum(int(item.get("price", 0)) * int(item.get("qty", 1)) for item in items)
        delivery_charge = data.get("delivery_charge", 0)
        packing_charge = data.get("packing_charge", 0)
        
        # Apply coupon if provided
        coupon_discount = 0
        coupon_code = data.get("coupon_code")
        if coupon_code:
            coupon = Coupon.query.filter_by(vendor_id=vendor_id, code=coupon_code, is_active=True).first()
            if coupon and subtotal >= coupon.min_order:
                if coupon.discount_type == "percent":
                    coupon_discount = int(subtotal * coupon.discount_value / 100)
                else:
                    coupon_discount = coupon.discount_value
        
        total = subtotal + delivery_charge + packing_charge - coupon_discount
        
        # Generate order ID
        order_id = f"ORD-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}"
        order = OnlineOrder(
            order_id=order_id,
            vendor_id=vendor_id,
            restaurant_id=data.get("restaurant_id"),
            items_json=json.dumps(items),
            total=total,
            payment_status="PENDING",
            customer_name=data.get("customer_name", "Guest"),
            status="PENDING"
        )
        
        db.session.add(order)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "order_id": order.id,
            "order_number": order.order_id,
            "total": total,
            "message": "Order placed successfully"
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

# Get customer orders (for tracking)
@app.route("/api/orders/track/<phone>", methods=["GET"])
def track_customer_orders(phone):
    """Track orders by phone number"""
    try:
        orders = OnlineOrder.query.filter_by(customer_phone=phone).order_by(OnlineOrder.created_at.desc()).all()
        result = []
        for order in orders:
            vendor = Vendor.query.get(order.vendor_id)
            result.append({
                "id": order.id,
                "order_id": order.order_id,
                "vendor_name": vendor.restaurant_name if vendor else "Unknown",
                "items": json.loads(order.items_json) if order.items_json else [],
                "total": order.total,
                "payment_method": order.payment_method,
                "payment_status": order.payment_status,
                "status": order.status,
                "created_at": order.created_at.isoformat() if order.created_at else None
            })
        return jsonify({"success": True, "orders": result})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# Vendor coupon management
@app.route("/vendor/coupons/<int:vendorId>", methods=["GET"])
def get_vendor_coupons(vendorId):
    """Get all coupons for a vendor"""
    try:
        coupons = Coupon.query.filter_by(vendor_id=vendorId).all()
        result = []
        for c in coupons:
            result.append({
                "id": c.id,
                "code": c.code,
                "discount_type": c.discount_type,
                "discount_value": c.discount_value,
                "min_order": c.min_order,
                "is_active": c.is_active,
                "created_at": c.created_at.isoformat() if c.created_at else None
            })
        return jsonify({"success": True, "coupons": result})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/vendor/coupons", methods=["POST"])
def create_coupon():
    """Create a new coupon"""
    try:
        data = request.get_json() or {}
        vendor_id = data.get("vendor_id")
        code = data.get("code", "").upper()
        
        if not vendor_id or not code:
            return jsonify({"success": False, "message": "vendor_id and code required"}), 400
        
        # Check if code already exists
        existing = Coupon.query.filter_by(code=code).first()
        if existing:
            return jsonify({"success": False, "message": "Coupon code already exists"}), 400
        
        coupon = Coupon(
            vendor_id=vendor_id,
            code=code,
            discount_type=data.get("discount_type", "percent"),
            discount_value=int(data.get("discount_value", 0)),
            min_order=int(data.get("min_order", 0)),
            is_active=data.get("is_active", True)
        )
        db.session.add(coupon)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "coupon_id": coupon.id,
            "message": "Coupon created successfully"
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

# Update vendor UPI
@app.route("/vendor/updateUpi/<int:vendorId>", methods=["PUT"])
def update_vendor_upi(vendorId):
    """Update vendor UPI ID"""
    try:
        data = request.get_json() or {}
        upi_id = data.get("upi_id", "")
        
        vendor = Vendor.query.get(vendorId)
        if not vendor:
            return jsonify({"success": False, "message": "Vendor not found"}), 404
        
        vendor.upi_id = upi_id
        db.session.commit()
        
        return jsonify({"success": True, "message": "UPI updated successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

# Get vendor analytics (enhanced)
@app.route("/api/vendor/online-analytics/<int:vendorId>", methods=["GET"])
def vendor_online_analytics(vendorId):
    """Get analytics for online orders"""
    try:
        vendor = Vendor.query.get(vendorId)
        if not vendor:
            return jsonify({"success": False, "message": "Vendor not found"}), 404
        
        today = datetime.utcnow().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        year_ago = today - timedelta(days=365)
        
        # Daily revenue
        daily_revenue = db.session.query(func.sum(OnlineOrder.total)).filter(
            OnlineOrder.vendor_id == vendorId,
            OnlineOrder.status.in_(["ACCEPTED", "PREPARING", "READY", "OUT_FOR_DELIVERY", "DELIVERED"]),
            OnlineOrder.created_at >= datetime.combine(today, datetime.min.time())
        ).scalar() or 0
        
        # Weekly revenue
        weekly_revenue = db.session.query(func.sum(OnlineOrder.total)).filter(
            OnlineOrder.vendor_id == vendorId,
            OnlineOrder.status.in_(["ACCEPTED", "PREPARING", "READY", "OUT_FOR_DELIVERY", "DELIVERED"]),
            OnlineOrder.created_at >= datetime.combine(week_ago, datetime.min.time())
        ).scalar() or 0
        
        # Monthly revenue
        monthly_revenue = db.session.query(func.sum(OnlineOrder.total)).filter(
            OnlineOrder.vendor_id == vendorId,
            OnlineOrder.status.in_(["ACCEPTED", "PREPARING", "READY", "OUT_FOR_DELIVERY", "DELIVERED"]),
            OnlineOrder.created_at >= datetime.combine(month_ago, datetime.min.time())
        ).scalar() or 0
        
        # Yearly revenue
        yearly_revenue = db.session.query(func.sum(OnlineOrder.total)).filter(
            OnlineOrder.vendor_id == vendorId,
            OnlineOrder.status.in_(["ACCEPTED", "PREPARING", "READY", "OUT_FOR_DELIVERY", "DELIVERED"]),
            OnlineOrder.created_at >= datetime.combine(year_ago, datetime.min.time())
        ).scalar() or 0
        
        # Total revenue
        total_revenue = db.session.query(func.sum(OnlineOrder.total)).filter(
            OnlineOrder.vendor_id == vendorId,
            OnlineOrder.status.in_(["ACCEPTED", "PREPARING", "READY", "OUT_FOR_DELIVERY", "DELIVERED"])
        ).scalar() or 0
        
        # Order counts
        total_orders = OnlineOrder.query.filter_by(vendor_id=vendorId).count()
        pending_orders = OnlineOrder.query.filter_by(vendor_id=vendorId, status="PENDING").count()
        delivered_orders = OnlineOrder.query.filter_by(vendor_id=vendorId, status="DELIVERED").count()
        
        # Average order value
        avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
        
        # Daily graph data (last 30 days)
        graph_data = []
        for i in range(30):
            d = today - timedelta(days=29-i)
            day_revenue = db.session.query(func.sum(OnlineOrder.total)).filter(
                OnlineOrder.vendor_id == vendorId,
                OnlineOrder.status.in_(["ACCEPTED", "PREPARING", "READY", "OUT_FOR_DELIVERY", "DELIVERED"]),
                OnlineOrder.created_at >= datetime.combine(d, datetime.min.time()),
                OnlineOrder.created_at < datetime.combine(d + timedelta(days=1), datetime.min.time())
            ).scalar() or 0
            day_orders = OnlineOrder.query.filter(
                OnlineOrder.vendor_id == vendorId,
                OnlineOrder.created_at >= datetime.combine(d, datetime.min.time()),
                OnlineOrder.created_at < datetime.combine(d + timedelta(days=1), datetime.min.time())
            ).count()
            graph_data.append({
                "date": d.strftime("%Y-%m-%d"),
                "revenue": day_revenue,
                "orders": day_orders
            })
        
        # Payment method breakdown
        cod_orders = OnlineOrder.query.filter_by(vendor_id=vendorId, payment_method="COD").count()
        upi_orders = OnlineOrder.query.filter_by(vendor_id=vendorId, payment_method="UPI").count()
        
        return jsonify({
            "success": True,
            "analytics": {
                "daily_revenue": daily_revenue,
                "weekly_revenue": weekly_revenue,
                "monthly_revenue": monthly_revenue,
                "yearly_revenue": yearly_revenue,
                "total_revenue": total_revenue,
                "total_orders": total_orders,
                "pending_orders": pending_orders,
                "delivered_orders": delivered_orders,
                "avg_order_value": round(avg_order_value, 2),
                "cod_orders": cod_orders,
                "upi_orders": upi_orders,
                "graph_data": graph_data
            }
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ========================
# RESTAURANT/MENU PUBLIC APIs (for nightlife_order.html & restaurant_detail.html)
# ========================


@app.route("/api/menus", methods=["GET"])
def get_menus():
    """Get menu items for a restaurant - for restaurant_detail.html"""
    restaurant_id = request.args.get("restaurant_id")
    vendor_id = request.args.get("vendor_id")
    
    if not restaurant_id and not vendor_id:
        return jsonify({"success": False, "message": "restaurant_id or vendor_id required"}), 400
    
    items = []
    
    # First try NightlifeItem for vendor_id
    if vendor_id:
        items = NightlifeItem.query.filter_by(vendor_id=int(vendor_id), availability="Available").all()
        result = []
        for item in items:
            result.append({
                "id": item.id,
                "restaurant_id": item.club_id,
                "vendor_id": item.vendor_id,
                "name": item.item_name,
                "description": item.description,
                "price": item.price,
                "category": item.category,
                "image": item.image_url,
                "available": item.availability == "Available"
            })
        return jsonify({"success": True, "menu": result})
    
    # Then try MenuItem for restaurant_id
    if restaurant_id:
        items = MenuItem.query.filter_by(restaurant_id=int(restaurant_id), available=True).all()
        result = []
        for item in items:
            result.append({
                "id": item.id,
                "restaurant_id": item.restaurant_id,
                "vendor_id": None,
                "name": item.name,
                "description": item.description,
                "price": item.price,
                "category": item.category,
                "image": item.image_url,
                "available": item.available
            })
        return jsonify({"success": True, "menu": result})
    
    return jsonify({"success": True, "menu": []})


# ========================
# VENDOR MENUS API - Dedicated endpoint for vendor dashboard (STEP 3)
# ========================

# Nightlife restaurants API for nightlife_order.html
@app.route("/api/nightlife/restaurants", methods=["GET"])
def get_nightlife_restaurants():
    """Get nightlife venues with their menu items for online ordering"""
    try:
        # Get all nightlife vendors
        vendors = Vendor.query.filter_by(vendor_type="nightlife").all()
        result = []
        
        for v in vendors:
            # Get nightlife config
            config = NightlifeVendorConfig.query.filter_by(vendor_id=v.id).first()
            
            # Get menu items for this vendor
            items = NightlifeItem.query.filter_by(vendor_id=v.id, availability="Available").all()
            menu_items = []
            for item in items:
                menu_items.append({
                    "id": item.id,
                    "name": item.item_name,
                    "description": item.description,
                    "price": item.price,
                    "category": item.category,
                    "image": item.image_url
                })
            
            result.append({
                "id": v.id,
                "name": v.restaurant_name,
                "address": v.address,
                "banner": config.banner_url if config else None,
                "city": config.city if config else '',
                "state": config.state if config else '',
                "menu": menu_items
            })
        
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/rest/vendor/<int:vendor_id>/upi", methods=["PUT"])
def update_rest_upi(vendor_id):

    data = request.get_json() or {}

    upi_id = data.get("upi_id")

    vendor = Vendor.query.get(vendor_id)

    if not vendor:
        return jsonify({"success": False, "message": "Vendor not found"}), 404

    vendor.upi_id = upi_id

    db.session.commit()

    return jsonify({
        "success": True,
        "upi_id": upi_id
    })

@app.route("/api/nightlife/vendor/<int:vendor_id>/upi", methods=["PUT"])
def update_nightlife_upi(vendor_id):

    data = request.get_json() or {}
    upi_id = data.get("upi_id")

    vendor = Vendor.query.get(vendor_id)

    if not vendor:
        return jsonify({"success": False, "message": "Vendor not found"}), 404

    vendor.upi_id = upi_id

    db.session.commit()

    return jsonify({
        "success": True,
        "upi_id": vendor.upi_id
    })

# ========================
# ALIAS ROUTES FOR VENDOR DASHBOARDS
# Alias /api/rest/* -> /api/restaurant/* for vendor_table.html compatibility
# Only add routes that don't already exist
# ========================

# /api/rest/types alias (GET and POST)
@app.route("/api/rest/types", methods=["GET"])
def rest_types_alias():
    return rest_get_types()

@app.route("/api/rest/types", methods=["POST"])
def rest_types_post_alias():
    return rest_save_type()

# /api/rest/slots alias (GET and POST)
@app.route("/api/rest/slots", methods=["GET"])
def rest_slots_alias():
    return rest_get_slots()

@app.route("/api/rest/slots", methods=["POST"])
def rest_slots_post_alias():
    return rest_save_slot()

# /api/rest/bookings alias (GET and POST)
@app.route("/api/rest/bookings", methods=["GET"])
def rest_bookings_alias():
    return rest_get_bookings()

@app.route("/api/rest/bookings", methods=["POST"])
def rest_bookings_post_alias():
    return rest_create_booking()

# /api/rest/bookings/<id>/toggle alias (for vendor_table.html)
@app.route("/api/rest/bookings/<int:booking_id>/toggle", methods=["POST"])
def rest_bookings_toggle_alias(booking_id):
    """Toggle booking status - alias for vendor_table.html"""
    b = RestBooking.query.get(booking_id)
    if not b:
        return jsonify({"success": False, "message": "Booking not found"}), 404
    
    if b.status == "confirmed":
        b.status = "cancelled"
    else:
        b.status = "confirmed"
    
    db.session.commit()
    return jsonify({"success": True, "status": b.status})

# /api/rest/settings alias
@app.route("/api/rest/settings", methods=["POST"])
def rest_settings_alias():
    return rest_save_settings()

# /api/rest/location alias
@app.route("/api/rest/location", methods=["POST"])
def rest_location_alias():
    return rest_save_location()

# /api/rest/banner alias
@app.route("/api/rest/banner", methods=["POST"])
def rest_banner_alias():
    return rest_upload_banner()

@app.route("/api/rest/banner", methods=["DELETE"])
def rest_banner_delete_alias():
    return jsonify({"success": True})

# /api/rest/vendor/by_email - for vendor_table.html login (POST)
@app.route("/api/rest/vendor/by_email", methods=["POST"])
def rest_vendor_by_email():
    """Get vendor by email for vendor_table.html"""
    data = get_data()
    email = (data.get("email") or "").strip().lower()
    restaurant_name = (data.get("restaurant_name") or "").strip()
    
    if not email:
        return jsonify({"success": False, "message": "email required"}), 400
    
    vendor = Vendor.query.filter_by(email=email).first()
    if not vendor:
        if restaurant_name:
            vendor = Vendor(
                restaurant_name=restaurant_name,
                owner_name="Owner",
                email=email,
                phone="",
                address="",
                vendor_type="restaurant"
            )
            db.session.add(vendor)
            db.session.commit()
        else:
            return jsonify({"success": False, "message": "Vendor not found"}), 404
    
    cfg = RestVendorConfig.query.filter_by(vendor_id=vendor.id).first()
    if not cfg:
        cfg = RestVendorConfig(vendor_id=vendor.id)
        db.session.add(cfg)
        db.session.commit()
    
    return jsonify({
        "success": True,
        "vendor": {
            "id": vendor.id,
            "restaurant_name": vendor.restaurant_name,
            "owner_name": vendor.owner_name,
            "email": vendor.email,
            "phone": vendor.phone,
            "address": vendor.address,
            "upi_id": vendor.upi_id
        },
        "settings": {
            "maxAdvanceDays": cfg.max_advance_days,
            "cancelBeforeHrs": cfg.cancel_before_hrs
        }
    })

# /api/rest/tables/<id>/toggle alias
@app.route("/api/rest/tables/<int:table_id>/toggle", methods=["POST"])
def rest_table_toggle_alias(table_id):
    """Toggle table status - alias for vendor_table.html"""
    table = RestTableSeat.query.get(table_id)
    if not table:
        return jsonify({"success": False, "message": "Table not found"}), 404
    
    if table.status == "free":
        table.status = "reserved"
    else:
        table.status = "free"
    
    db.session.commit()
    return jsonify({"success": True})

# /api/rest/tables/mark_all_free alias
@app.route("/api/rest/tables/mark_all_free", methods=["POST"])
def rest_tables_mark_all_free_alias():
    """Mark all tables as free for a type - alias for vendor_table.html"""
    data = get_data()
    type_id = data.get("typeId")
    
    if not type_id:
        return jsonify({"success": False, "message": "typeId required"}), 400
    
    tables = RestTableSeat.query.filter_by(type_id=type_id).all()
    for table in tables:
        table.status = "free"
    
    db.session.commit()
    return jsonify({"success": True})

# /api/rest/types/<id>/tables alias
@app.route("/api/rest/types/<int:type_id>/tables", methods=["GET"])
def rest_type_tables_alias(type_id):
    """Get tables for a type - alias for vendor_table.html"""
    tables = RestTableSeat.query.filter_by(type_id=type_id).all()
    
    result = []
    for t in tables:
        result.append({
            "id": t.id,
            "num": t.num,
            "status": t.status
        })
    
    return jsonify({"success": True, "tables": result})

# /api/rest/types/<id> DELETE alias
@app.route("/api/rest/types/<int:type_id>", methods=["DELETE"])
def rest_type_delete_alias(type_id):
    """Delete a table type - alias for vendor_table.html"""
    t = RestTableType.query.get(type_id)
    if not t:
        return jsonify({"success": False, "message": "Type not found"}), 404
    
    RestTableSeat.query.filter_by(type_id=type_id).delete()
    
    db.session.delete(t)
    db.session.commit()
    
    return jsonify({"success": True})

# /api/rest/slots/<id> DELETE alias
@app.route("/api/rest/slots/<int:slot_id>", methods=["DELETE"])
def rest_slot_delete_alias(slot_id):
    """Delete a slot - alias for vendor_table.html"""
    s = RestSlot.query.get(slot_id)
    if not s:
        return jsonify({"success": False, "message": "Slot not found"}), 404
    
    db.session.delete(s)
    db.session.commit()
    
    return jsonify({"success": True})

# ========================
# PLACEHOLDER APIS
# ========================

@app.route("/api/rest/types/placeholder")
def rest_types_placeholder():
    return jsonify({"success": True, "data": []})

@app.route("/api/rest/slots/placeholder")
def rest_slots_placeholder():
    return jsonify({"success": True, "data": []})

@app.route("/api/rest/bookings/placeholder")
def rest_bookings_placeholder():
    return jsonify({"success": True, "data": []})


# ========================
# RUN SERVER
# ========================
# Nightlife Item APIs
@app.route("/api/nightlife/add-item", methods=["POST"])
def add_nightlife_items():
    data = request.json
    vendor_id = data.get("vendor_id")
    name = data.get("name")
    price = data.get("price")
    image = data.get("image")
    
    if not vendor_id or not name or not price:
        return jsonify({"success": False, "message": "vendor_id, name, price required"}), 400
    
    item = NightlifeItem(
        vendor_id=vendor_id,
        item_name=name,
        price=price,
        image_url=image,
        category=data.get("category", "General"),
        availability="Available"
    )
    db.session.add(item)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "data": {
            "id": item.id,
            "name": item.item_name,
            "price": item.price
        }
    })

@app.route("/api/nightlife/items")
def get_nightlife_items_list():
    vendor_id = request.args.get("vendor_id")
    if not vendor_id:
        return jsonify({"success": False, "message": "vendor_id required"}), 400
    
    items = NightlifeItem.query.filter_by(vendor_id=int(vendor_id)).all()
    result = []
    for i in items:
        result.append({
            "id": i.id,
            "name": i.item_name,
            "price": i.price,
            "image": i.image_url
        })
    
    return jsonify({
        "success": True,
        "data": result
    })

@app.route("/api/restaurants/<int:restaurant_id>/menu", methods=["GET"])
def get_restaurant_menu(restaurant_id):

    try:
        items = MenuItem.query.filter_by(restaurant_id=restaurant_id).all()

        menu = []

        for item in items:
            menu.append({
                "id": item.id,
                "name": item.name,
                "price": item.price,
                "category": item.category,
                "food_type": item.food_type,
                "image_url": item.image_url,
                "available": item.available
            })

        return jsonify({
            "success": True,
            "menu": menu
        })

    except Exception as e:
        print("MENU API ERROR:", e)
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/api/vendor/orders/qr/<int:vendor_id>", methods=["GET"])
def get_vendor_qr_orders(vendor_id):

    try:
        orders = QROrder.query.filter_by(vendor_id=vendor_id).all()

        result = []

        for o in orders:
            result.append({
                "id": o.id,
                "table_label": o.table_label,
                "items": json.loads(o.items_json),
                "total": o.total,
                "status": o.status,
                "payment_status": o.payment_status
            })

        return jsonify(result)

    except Exception as e:
        print("QR ORDER ERROR:", e)
        return jsonify([])

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/api/upload-image", methods=["POST"])
def upload_image():

    if "image" not in request.files:
        return jsonify({"success": False, "message": "No image file"}), 400

    file = request.files["image"]

    if file.filename == "":
        return jsonify({"success": False, "message": "Empty file"}), 400

    if not allowed_file(file.filename):
        return jsonify({"success": False, "message": "Invalid file type"}), 400

    filename = secure_filename(file.filename)
    new_name = f"{int(datetime.utcnow().timestamp())}_{filename}"

    path = os.path.join(app.config["UPLOAD_FOLDER"], new_name)
    file.save(path)

    return jsonify({
        "success": True,
        "image_url": f"/uploads/{new_name}"
    })

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory("uploads", filename)

@app.route("/api/admin/settings", methods=["GET"])
def get_admin_settings():
    try:

        settings = {
            "restaurant": {
                "gst_percent": 5,
                "platform_fee_percent": 2
            },
            "nightlife": {
                "handling_fee": 29
            }
        }

        return jsonify(settings)

    except Exception as e:
        print("ADMIN SETTINGS ERROR:", e)
        return jsonify({"success": False, "message": str(e)})
@app.route("/api/admin/settings", methods=["POST"])
def update_admin_settings():
    data = request.json

    if not data:
        return jsonify({"success": False, "message": "No data provided"}), 400

    # Get or create admin settings
    settings = AdminSettings.query.first()
    
    if not settings:
        # Create new settings with defaults
        settings = AdminSettings(
            restaurant_gst=5,
            restaurant_delivery_fee=0,
            restaurant_packing_fee=0,
            restaurant_platform_commission=25,
            nightlife_platform_commission=20,
            nightlife_service_fee=0
        )
        db.session.add(settings)
    
    # Update restaurant settings (validate numeric inputs)
    try:
        if "restaurant_gst" in data:
            settings.restaurant_gst = float(data.get("restaurant_gst", settings.restaurant_gst))
    except (ValueError, TypeError):
        pass
    
    try:
        if "restaurant_delivery_fee" in data:
            settings.restaurant_delivery_fee = float(data.get("restaurant_delivery_fee", settings.restaurant_delivery_fee))
    except (ValueError, TypeError):
        pass
    
    try:
        if "restaurant_packing_fee" in data:
            settings.restaurant_packing_fee = float(data.get("restaurant_packing_fee", settings.restaurant_packing_fee))
    except (ValueError, TypeError):
        pass
    
    try:
        if "restaurant_platform_commission" in data:
            settings.restaurant_platform_commission = float(data.get("restaurant_platform_commission", settings.restaurant_platform_commission))
    except (ValueError, TypeError):
        pass
    
    # Update nightlife settings
    try:
        if "nightlife_platform_commission" in data:
            settings.nightlife_platform_commission = float(data.get("nightlife_platform_commission", settings.nightlife_platform_commission))
    except (ValueError, TypeError):
        pass
    
    try:
        if "nightlife_service_fee" in data:
            settings.nightlife_service_fee = float(data.get("nightlife_service_fee", settings.nightlife_service_fee))
    except (ValueError, TypeError):
        pass
    
    # Also support legacy field names for backward compatibility
    try:
        if "gst" in data:
            settings.restaurant_gst = float(data.get("gst", settings.restaurant_gst))
    except (ValueError, TypeError):
        pass
    
    try:
        if "delivery_fee" in data:
            settings.restaurant_delivery_fee = float(data.get("delivery_fee", settings.restaurant_delivery_fee))
    except (ValueError, TypeError):
        pass
    
    try:
        if "packing_fee" in data:
            settings.restaurant_packing_fee = float(data.get("packing_fee", settings.restaurant_packing_fee))
    except (ValueError, TypeError):
        pass

    db.session.commit()

    return jsonify({
        "success": True,
        "message": "Settings updated successfully",
        "restaurant": {
            "gst": settings.restaurant_gst,
            "delivery_fee": settings.restaurant_delivery_fee,
            "packing_fee": settings.restaurant_packing_fee,
            "platform_commission": settings.restaurant_platform_commission
        },
        "nightlife": {
            "platform_commission": settings.nightlife_platform_commission,
            "service_fee": settings.nightlife_service_fee
        }
    })

if __name__ == "__main__":
    with app.app_context():
        try:
            with db.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                print("\n" + "="*60)
                print(f" Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
                print("="*60 + "\n")
        except Exception as e:
            print("\n" + "="*60)
            print(" PostgreSQL connection failed!")
            print(f"Error: {e}")
            print("="*60 + "\n")
            # sys.exit(1)  # Commented out to allow SQLite fallback
        db.create_all()
        print("All database tables created")
        
        # Seed demo data
        try:
            from seed_data import seed_demo_data
            seed_demo_data(db)
        except Exception as e:
            print(f"Seed data skipped: {e}")
    
    print("\n" + "="*60)
    print("ZomaClone Backend Starting")
    print("Server: http://127.0.0.1:5000")
    print("Database: PostgreSQL - neondb")
    print("Auth: OTP-based")
    print("Restaurant & Nightlife booking SEPARATED")
    print("="*60 + "\n")
    
    app.run(debug=True)
