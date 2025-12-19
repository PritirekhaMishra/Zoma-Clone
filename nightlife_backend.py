# nightlife_backend.py
import os
import hmac
import hashlib
import traceback
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import json
import sqlite3

# ================== BASIC SETUP ==================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "nightlife.db")
UPLOAD_ROOT = os.path.join(BASE_DIR, "uploads")
CLUB_UPLOAD = os.path.join(UPLOAD_ROOT, "clubs")
ITEM_UPLOAD = os.path.join(UPLOAD_ROOT, "nightlife_items")

os.makedirs(CLUB_UPLOAD, exist_ok=True)
os.makedirs(ITEM_UPLOAD, exist_ok=True)

app = Flask(__name__, static_url_path="", static_folder=".")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + DB_PATH
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Allow CORS for dev. In production restrict origins.
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# Optional: Razorpay secret (for signature verification). Set as environment variable if you want server-side verification.
RAZORPAY_SECRET = os.environ.get("RAZORPAY_SECRET")


# ================== MODELS ==================

class Vendor(db.Model):
    __tablename__ = "vendors"
    id = db.Column(db.Integer, primary_key=True)
    restaurant_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(255), nullable=True)

    platform_fee = db.Column(db.Float, nullable=False, default=10.0)
    delivery_fee = db.Column(db.Float, nullable=False, default=25.0)
    packing_fee = db.Column(db.Float, nullable=False, default=5.0)
    tax_percent = db.Column(db.Float, nullable=False, default=5.0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Club(db.Model):
    __tablename__ = "clubs"
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"), nullable=False)
    club_name = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(255), nullable=True)
    music = db.Column(db.String(120), nullable=True)
    dress = db.Column(db.String(120), nullable=True)
    description = db.Column(db.Text, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    image_path = db.Column(db.String(255), nullable=True)

    # NEW: flag to distinguish nightlife (table booking) clubs from food/order clubs
    is_nightlife = db.Column(db.Boolean, default=True, nullable=False)


class NightlifeItem(db.Model):
    __tablename__ = "nightlife_items"
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"), nullable=False)
    club_id = db.Column(db.Integer, db.ForeignKey("clubs.id"), nullable=False)
    item_name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(80), nullable=True)
    price = db.Column(db.Float, nullable=False, default=0.0)
    description = db.Column(db.Text, nullable=True)
    availability = db.Column(db.String(20), nullable=False, default="Available")
    image_path = db.Column(db.String(255), nullable=True)


class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"), nullable=False)
    club_id = db.Column(db.Integer, db.ForeignKey("clubs.id"), nullable=True)
    user_id = db.Column(db.Integer, nullable=True)
    user_name = db.Column(db.String(120), nullable=True)
    user_phone = db.Column(db.String(30), nullable=True)
    user_address = db.Column(db.Text, nullable=True)

    subtotal = db.Column(db.Float, default=0.0)
    platform_fee = db.Column(db.Float, default=0.0)
    delivery_fee = db.Column(db.Float, default=0.0)
    packing_fee = db.Column(db.Float, default=0.0)
    tax_amount = db.Column(db.Float, default=0.0)
    discount = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)

    payment_method = db.Column(db.String(40), default="COD")
    payment_id = db.Column(db.String(200), nullable=True)
    payment_meta = db.Column(db.Text, nullable=True)

    status = db.Column(db.String(40), default="PENDING")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class OrderItem(db.Model):
    __tablename__ = "order_items"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    item_id = db.Column(db.Integer, nullable=True)
    name = db.Column(db.String(120), nullable=False)
    qty = db.Column(db.Integer, default=1)
    price = db.Column(db.Float, nullable=False, default=0.0)


class Rating(db.Model):
    __tablename__ = "ratings"
    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, db.ForeignKey("clubs.id"), nullable=False)
    name = db.Column(db.String(120), nullable=True)
    stars = db.Column(db.Integer, default=0)
    comment = db.Column(db.Text, nullable=True)
    date = db.Column(db.String(40), nullable=True)


class NightlifeCoupon(db.Model):
    __tablename__ = "nightlife_coupons"
    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, db.ForeignKey("clubs.id"), nullable=False)
    code = db.Column(db.String(40), nullable=False, unique=False)
    type = db.Column(db.String(20), nullable=False, default="percent")
    value = db.Column(db.Float, nullable=False, default=0.0)
    min_order = db.Column(db.Float, nullable=False, default=0.0)
    max_discount = db.Column(db.Float, nullable=True)
    active = db.Column(db.Boolean, default=True)


class NightlifeTable(db.Model):
    __tablename__ = "nightlife_tables"
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"), nullable=False)
    club_id = db.Column(db.Integer, db.ForeignKey("clubs.id"), nullable=False)
    category = db.Column(db.String(120), nullable=False)
    capacity = db.Column(db.String(40), nullable=True)
    price = db.Column(db.Float, default=0.0)
    feature = db.Column(db.String(120), nullable=True)
    total_tables = db.Column(db.Integer, default=0)
    free_tables = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class NightlifeEvent(db.Model):
    __tablename__ = "nightlife_events"
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"), nullable=False)
    club_id = db.Column(db.Integer, db.ForeignKey("clubs.id"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    date = db.Column(db.String(80), nullable=True)
    fee = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ================== HELPERS / SERIALIZERS ==================

def vendor_to_dict(v: Vendor):
    return {
        "id": v.id,
        "restaurant_name": v.restaurant_name,
        "email": v.email or "",
        "phone": v.phone or "",
        "address": v.address or "",
        "platform_fee": float(v.platform_fee or 0),
        "delivery_fee": float(v.delivery_fee or 0),
        "packing_fee": float(v.packing_fee or 0),
        "tax_percent": float(v.tax_percent or 0),
        "created_at": v.created_at.isoformat() if v.created_at else None,
    }


def club_to_dict(c: Club):
    img = f"/uploads/{c.image_path}" if c.image_path else None
    return {
        "id": c.id,
        "club_id": c.id,
        "vendor_id": c.vendor_id,
        "club_name": c.club_name,
        "location": c.location or "",
        "music": c.music or "",
        "dress": c.dress or "",
        "description": c.description or "",
        "phone": c.phone or "",
        "email": c.email or "",
        "image": img,
        "main_image": img,
        "is_nightlife": bool(c.is_nightlife),
    }


def item_to_dict(i: NightlifeItem):
    img = f"/uploads/{i.image_path}" if i.image_path else None
    return {
        "id": i.id,
        "item_id": i.id,
        "vendor_id": i.vendor_id,
        "club_id": i.club_id,
        "name": i.item_name,
        "item_name": i.item_name,
        "category": i.category or "",
        "price": float(i.price or 0),
        "description": i.description or "",
        "availability": i.availability,
        "image_url": img,
    }


def order_to_dict(o: Order):
    items = OrderItem.query.filter_by(order_id=o.id).all()
    return {
        "id": o.id,
        "vendor_id": o.vendor_id,
        "club_id": o.club_id,
        "user_id": o.user_id,
        "user_name": o.user_name,
        "user_phone": o.user_phone,
        "user_address": o.user_address,
        "subtotal": float(o.subtotal or 0),
        "platform_fee": float(o.platform_fee or 0),
        "delivery_fee": float(o.delivery_fee or 0),
        "packing_fee": float(o.packing_fee or 0),
        "tax_amount": float(o.tax_amount or 0),
        "discount": float(o.discount or 0),
        "total": float(o.total or 0),
        "payment_method": o.payment_method,
        "payment_id": o.payment_id,
        "status": o.status,
        "created_at": o.created_at.isoformat() if o.created_at else None,
        "items": [{"item_id": it.item_id, "name": it.name, "qty": it.qty, "price": float(it.price)} for it in items],
    }


def rating_summary(club_id: int):
    ratings = Rating.query.filter_by(club_id=club_id).all()
    items = []
    total = 0
    for r in ratings:
        total += r.stars or 0
        items.append(
            {
                "name": r.name or "",
                "stars": r.stars or 0,
                "comment": r.comment or "",
                "date": r.date or "",
            }
        )
    count = len(ratings)
    avg = (total / count) if count else 0.0
    return {"avg": avg, "count": count, "items": items}


def coupon_to_dict(c: NightlifeCoupon):
    return {
        "id": c.id,
        "club_id": c.club_id,
        "code": c.code,
        "type": c.type,
        "value": c.value,
        "min_order": c.min_order,
        "max_discount": c.max_discount,
        "active": c.active,
    }


def table_to_dict(t: NightlifeTable):
    return {
        "id": t.id,
        "vendor_id": t.vendor_id,
        "club_id": t.club_id,
        "category": t.category,
        "capacity": t.capacity,
        "price": float(t.price or 0),
        "feature": t.feature or "",
        "total_tables": int(t.total_tables or 0),
        "free_tables": int(t.free_tables or 0),
    }


def event_to_dict(e: NightlifeEvent):
    return {
        "id": e.id,
        "vendor_id": e.vendor_id,
        "club_id": e.club_id,
        "name": e.name,
        "date": e.date or "",
        "fee": float(e.fee or 0),
    }


# ================== STATIC: UPLOADS ==================

@app.route("/uploads/<path:filename>")
def serve_uploads(filename):
    return send_from_directory(UPLOAD_ROOT, filename)


# ================== GLOBAL ERROR & OPTIONS HANDLERS ==================

@app.errorhandler(Exception)
def handle_exception(e):
    # Print stack trace to terminal for debugging
    traceback.print_exc()
    resp = jsonify({"ok": False, "message": "Internal server error", "detail": str(e)})
    resp.status_code = 500
    # ensure CORS headers on error responses
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization,Accept,Origin"
    return resp


# Generic OPTIONS handler — helpful for preflight
@app.route("/", defaults={"path": ""}, methods=["OPTIONS"])
@app.route("/<path:path>", methods=["OPTIONS"])
def handle_options(path):
    from flask import make_response
    resp = make_response()
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization,Accept,Origin"
    return resp


# ================== VENDOR / CLUB / MENU ENDPOINTS ==================

@app.get("/vendor/find/<int:vendor_id>")
def vendor_find(vendor_id):
    v = Vendor.query.get(vendor_id)
    if not v:
        return jsonify({"ok": False, "message": "Vendor not found"}), 404
    return jsonify({"ok": True, "vendor": vendor_to_dict(v)})



@app.get("/vendor/getClubs/<int:vendor_id>")
def vendor_get_clubs(vendor_id):
    """
    Returns only nightlife (table-booking) clubs by default.
    Optional query param `all=1` will return all clubs (both nightlife and non-nightlife).
    Defensive: works if is_nightlife column is INTEGER (1/0), TEXT ("1"/"true"), boolean, or missing.
    """
    include_all = request.args.get("all", "0") in ("1", "true", "True")
    try:
        # If include_all requested just return everything for vendor
        if include_all:
            clubs_q = Club.query.filter_by(vendor_id=vendor_id).all()
        else:
            # Defensive filter: accept boolean True, integer 1, or textual '1'/'true'
            # Using SQL expression to cover numeric stored values too.
            from sqlalchemy import or_, and_, text
            # prefer column object if exists
            if hasattr(Club, "is_nightlife"):
                col = getattr(Club, "is_nightlife")
                clubs_q = Club.query.filter(
                    Club.vendor_id == vendor_id,
                    or_(
                        col == True,           # boolean
                        col == 1,              # integer 1
                        col == "1",            # text '1'
                        text("lower(COALESCE(is_nightlife, '')) = 'true'")  # text 'true'
                    )
                ).all()
            else:
                # column missing: fallback to basic vendor clubs
                clubs_q = Club.query.filter_by(vendor_id=vendor_id).all()
    except Exception:
        # Fallback: don't crash — return vendor clubs (will be logged by global handler)
        clubs_q = Club.query.filter_by(vendor_id=vendor_id).all()

    return jsonify([club_to_dict(c) for c in clubs_q])


@app.post("/vendor/addClub")
def vendor_add_club():
    data = request.get_json(force=True) or {}
    try:
        vendor_id = int(data.get("vendor_id"))
    except Exception:
        return jsonify({"ok": False, "message": "vendor_id is required and must be integer"}), 400

    # allow caller to specify whether this club is nightlife or food
    is_nightlife = True
    if "is_nightlife" in data:
        try:
            is_nightlife = bool(data.get("is_nightlife"))
        except Exception:
            is_nightlife = True

    club = Club(
        vendor_id=vendor_id,
        club_name=data.get("club_name") or "My Club",
        location=data.get("location") or "",
        music=data.get("music") or "",
        dress=data.get("dress") or "",
        description=data.get("description") or "",
        phone=data.get("phone") or "",
        email=data.get("email") or "",
        is_nightlife=is_nightlife,
    )
    db.session.add(club)
    db.session.commit()
    return jsonify({"ok": True, "club_id": club.id})


@app.put("/vendor/updateClub/<int:club_id>")
def vendor_update_club(club_id):
    c = Club.query.get(club_id)
    if not c:
        return jsonify({"ok": False, "message": "Club not found"}), 404

    data = request.get_json(force=True)
    c.club_name = data.get("club_name", c.club_name)
    c.location = data.get("location", c.location)
    c.music = data.get("music", c.music)
    c.dress = data.get("dress", c.dress)
    c.description = data.get("description", c.description)
    c.phone = data.get("phone", c.phone)
    c.email = data.get("email", c.email)
    # update is_nightlife flag if present
    if "is_nightlife" in data:
        try:
            c.is_nightlife = bool(data.get("is_nightlife"))
        except Exception:
            pass
    db.session.commit()
    return jsonify({"ok": True})


@app.post("/vendor/uploadClubImages/<int:club_id>")
def vendor_upload_club_images(club_id):
    c = Club.query.get(club_id)
    if not c:
        return jsonify({"ok": False, "message": "Club not found"}), 404

    files = request.files.getlist("images")
    if not files:
        return jsonify({"ok": False, "message": "No files"}), 400

    saved_paths = []
    allowed_ext = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    for f in files:
        ext = os.path.splitext(f.filename)[1].lower()
        if ext not in allowed_ext:
            continue
        filename = f"clubs/{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}{ext}"
        abs_path = os.path.join(UPLOAD_ROOT, filename)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        f.save(abs_path)
        saved_paths.append(filename)

    if not saved_paths:
        return jsonify({"ok": False, "message": "No valid image files uploaded"}), 400

    c.image_path = saved_paths[0]
    db.session.commit()
    return jsonify({"ok": True, "images": [f"/uploads/{p}" for p in saved_paths]})


@app.get("/vendor/getNightlifeItems/<int:vendor_id>")
def vendor_get_nightlife_items(vendor_id):
    items = NightlifeItem.query.filter_by(vendor_id=vendor_id).all()
    return jsonify([item_to_dict(i) for i in items])


@app.post("/vendor/addNightlifeItem")
def vendor_add_nightlife_item():
    form = request.form
    vendor_id = form.get("vendor_id")
    club_id = form.get("club_id")
    item_name = form.get("item_name")
    category = form.get("category")
    price = form.get("price")
    description = form.get("description")
    availability = form.get("availability") or "Available"

    if not (vendor_id and club_id and item_name and price):
        return jsonify({"success": False, "message": "Missing required fields"}), 400

    image = request.files.get("image")
    image_rel_path = None
    if image:
        ext = os.path.splitext(image.filename)[1]
        filename = f"nightlife_items/{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}{ext}"
        abs_path = os.path.join(UPLOAD_ROOT, filename)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        image.save(abs_path)
        image_rel_path = filename

    item = NightlifeItem(
        vendor_id=int(vendor_id),
        club_id=int(club_id),
        item_name=item_name,
        category=category,
        price=float(price),
        description=description,
        availability=availability,
        image_path=image_rel_path,
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({"success": True, "item_id": item.id})


@app.put("/vendor/editNightlifeItem/<int:item_id>")
def vendor_edit_nightlife_item(item_id):
    item = NightlifeItem.query.get(item_id)
    if not item:
        return jsonify({"success": False, "message": "Item not found"}), 404

    data = request.get_json(force=True)
    if "item_name" in data:
        item.item_name = data["item_name"]
    if "category" in data:
        item.category = data["category"]
    if "price" in data:
        item.price = float(data["price"])
    if "description" in data:
        item.description = data["description"]
    if "availability" in data:
        item.availability = data["availability"]

    db.session.commit()
    return jsonify({"success": True})


@app.delete("/vendor/deleteNightlifeItem/<int:item_id>")
def vendor_delete_nightlife_item(item_id):
    item = NightlifeItem.query.get(item_id)
    if not item:
        return jsonify({"success": False, "message": "Item not found"}), 404

    if item.image_path:
        abs_path = os.path.join(UPLOAD_ROOT, item.image_path)
        if os.path.exists(abs_path):
            try:
                os.remove(abs_path)
            except Exception:
                pass

    db.session.delete(item)
    db.session.commit()
    return jsonify({"success": True})


# Tables endpoints
@app.post("/vendor/addTable")
def vendor_add_table():
    data = request.get_json(force=True) or {}
    try:
        vendor_id = int(data.get("vendor_id"))
        club_id = int(data.get("club_id"))
    except Exception:
        return jsonify({"ok": False, "message": "vendor_id and club_id required"}), 400

    category = data.get("category") or ""
    capacity = str(data.get("capacity") or "")
    price = float(data.get("price") or 0)
    feature = data.get("feature") or ""
    total_tables = int(data.get("total_tables") or 0)
    free_tables = int(data.get("free_tables") or 0)

    t = NightlifeTable(
        vendor_id=vendor_id,
        club_id=club_id,
        category=category,
        capacity=capacity,
        price=price,
        feature=feature,
        total_tables=total_tables,
        free_tables=free_tables,
    )
    db.session.add(t)
    db.session.commit()
    return jsonify({"ok": True, "table_id": t.id})


@app.get("/vendor/getTables/<int:club_id>")
def vendor_get_tables(club_id):
    tables = NightlifeTable.query.filter_by(club_id=club_id).all()
    return jsonify([table_to_dict(t) for t in tables])


@app.delete("/vendor/deleteTable/<int:table_id>")
def vendor_delete_table(table_id):
    t = NightlifeTable.query.get(table_id)
    if not t:
        return jsonify({"ok": False, "message": "Table not found"}), 404
    db.session.delete(t)
    db.session.commit()
    return jsonify({"ok": True})


# Events endpoints
@app.post("/vendor/addEvent")
def vendor_add_event():
    data = request.get_json(force=True) or {}
    try:
        vendor_id = int(data.get("vendor_id"))
        club_id = int(data.get("club_id"))
    except Exception:
        return jsonify({"ok": False, "message": "vendor_id and club_id required"}), 400

    name = data.get("name") or ""
    date = data.get("date") or ""
    fee = float(data.get("fee") or 0)

    e = NightlifeEvent(vendor_id=vendor_id, club_id=club_id, name=name, date=date, fee=fee)
    db.session.add(e)
    db.session.commit()
    return jsonify({"ok": True, "event_id": e.id})


@app.get("/vendor/getEvents/<int:club_id>")
def vendor_get_events(club_id):
    events = NightlifeEvent.query.filter_by(club_id=club_id).all()
    return jsonify([event_to_dict(e) for e in events])


# Bookings for vendor: return Orders for vendor with table_type and user_email where possible

@app.get("/vendor/bookings/<int:vendor_id>")
def vendor_bookings(vendor_id):
    """
    Return a JSON array of bookings for a vendor.
    This function is defensive: on any internal error it logs the traceback and
    returns {"ok": False, "bookings": []} (instead of a 500 HTML response).
    """
    try:
        orders = Order.query.filter_by(vendor_id=vendor_id).order_by(Order.created_at.desc()).limit(200).all()
        out = []
        for o in orders:
            items = OrderItem.query.filter_by(order_id=o.id).all()
            table_name = items[0].name if items else ""
            qty = sum((it.qty or 0) for it in items) or 1

            user_email = None
            if o.payment_meta:
                # try JSON first, then fallback to literal_eval, otherwise ignore
                try:
                    pm = json.loads(o.payment_meta)
                    if isinstance(pm, dict):
                        user_email = pm.get("email") or pm.get("user_email") or pm.get("buyer_email")
                except Exception:
                    try:
                        import ast
                        pm2 = ast.literal_eval(o.payment_meta)
                        if isinstance(pm2, dict):
                            user_email = pm2.get("email") or pm2.get("user_email") or pm2.get("buyer_email")
                    except Exception:
                        user_email = None

            out.append({
                "id": o.id,
                "club_id": o.club_id,
                "user_name": o.user_name or "",
                "user_phone": o.user_phone or "",
                "user_email": user_email,
                "amount": float(o.total or 0),
                "payment_id": o.payment_id or "",
                "status": o.status,
                "quantity": qty,
                "table_type": table_name,
            })

        # Always return an array (and an ok flag)
        return jsonify({"ok": True, "bookings": out})
    except Exception as ex:
        # Log detailed error server-side for debugging
        import traceback
        traceback.print_exc()
        # Return a non-error response to client (prevents frontend from crashing)
        return jsonify({"ok": False, "message": "Internal error reading bookings", "bookings": []})


# ================== ORDERS ==================
def calculate_pricing_for_order(vendor_id, club_id, items_payload, coupon_id=None):
    vendor = Vendor.query.get(vendor_id)
    if not vendor:
        raise ValueError("Vendor not found")

    subtotal = 0.0
    item_records = []
    for it in items_payload:
        item_id = it.get("item_id")
        qty = int(it.get("qty") or 0)
        if qty <= 0:
            continue
        menu_item = NightlifeItem.query.filter_by(id=item_id, club_id=club_id, vendor_id=vendor_id).first()
        if not menu_item:
            continue
        price = float(menu_item.price or 0.0)
        subtotal += price * qty
        item_records.append({"item_id": menu_item.id, "name": menu_item.item_name, "price": price, "qty": qty})

    platform_fee = float(vendor.platform_fee or 0.0)
    delivery_fee = float(vendor.delivery_fee or 0.0)
    packing_fee  = float(vendor.packing_fee or 0.0)
    tax_percent  = float(vendor.tax_percent or 0.0)

    taxable_base = subtotal + platform_fee + delivery_fee + packing_fee
    tax_amount = taxable_base * (tax_percent / 100.0) if taxable_base > 0 else 0.0

    discount = 0.0
    applied_coupon = None
    if coupon_id:
        coup = NightlifeCoupon.query.filter_by(id=coupon_id, club_id=club_id, active=True).first()
        if coup:
            if subtotal >= float(coup.min_order or 0):
                if coup.type == "percent":
                    discount_calc = subtotal * (float(coup.value or 0) / 100.0)
                else:
                    discount_calc = float(coup.value or 0)
                if coup.max_discount is not None:
                    discount_calc = min(discount_calc, float(coup.max_discount))
                discount = float(round(discount_calc, 2))
                applied_coupon = coup.code

    gross = subtotal + platform_fee + delivery_fee + packing_fee + tax_amount
    if discount > gross:
        discount = gross
    total = round(gross - discount, 2)

    return {
        "subtotal": round(subtotal, 2),
        "platform_fee": round(platform_fee, 2),
        "delivery_fee": round(delivery_fee, 2),
        "packing_fee": round(packing_fee, 2),
        "tax_amount": round(tax_amount, 2),
        "discount": round(discount, 2),
        "total": round(total, 2),
        "items": item_records,
        "coupon_code": applied_coupon,
    }


@app.post("/nightlife/order/cod")
def nightlife_order_cod():
    data = request.get_json(force=True) or {}
    try:
        club_id = int(data.get("club_id"))
        vendor_id = int(data.get("vendor_id"))
    except Exception:
        return jsonify({"success": False, "message": "club_id and vendor_id required"}), 400

    items = data.get("items") or []
    if not items:
        return jsonify({"success": False, "message": "items required"}), 400

    coupon_id = data.get("coupon_id")

    try:
        pricing = calculate_pricing_for_order(vendor_id, club_id, items, coupon_id=coupon_id)
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400

    order = Order(
        vendor_id=vendor_id,
        club_id=club_id,
        user_id=data.get("user_id"),
        user_name=data.get("user_name") or "",
        user_phone=data.get("user_phone") or "",
        user_address=data.get("user_address") or "",
        subtotal=pricing["subtotal"],
        platform_fee=pricing["platform_fee"],
        delivery_fee=pricing["delivery_fee"],
        packing_fee=pricing["packing_fee"],
        tax_amount=pricing["tax_amount"],
        discount=pricing["discount"],
        total=pricing["total"],
        payment_method="COD",
        payment_id=None,
        status="PENDING",
    )
    db.session.add(order)
    db.session.flush()

    for it in pricing["items"]:
        oi = OrderItem(
            order_id=order.id,
            item_id=it["item_id"],
            name=it["name"],
            qty=it["qty"],
            price=it["price"],
        )
        db.session.add(oi)

    db.session.commit()
    return jsonify({"success": True, "order": order_to_dict(order)})


@app.post("/nightlife/order/online/create")
def nightlife_order_online_create():
    data = request.get_json(force=True) or {}
    try:
        club_id = int(data.get("club_id"))
        vendor_id = int(data.get("vendor_id"))
    except Exception:
        return jsonify({"success": False, "message": "club_id and vendor_id required"}), 400

    items = data.get("items") or []
    if not items:
        return jsonify({"success": False, "message": "items required"}), 400

    coupon_id = data.get("coupon_id")

    try:
        pricing = calculate_pricing_for_order(vendor_id, club_id, items, coupon_id=coupon_id)
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400

    order = Order(
        vendor_id=vendor_id,
        club_id=club_id,
        user_id=data.get("user_id"),
        user_name=data.get("user_name") or "",
        user_phone=data.get("user_phone") or "",
        user_address=data.get("user_address") or "",
        subtotal=pricing["subtotal"],
        platform_fee=pricing["platform_fee"],
        delivery_fee=pricing["delivery_fee"],
        packing_fee=pricing["packing_fee"],
        tax_amount=pricing["tax_amount"],
        discount=pricing["discount"],
        total=pricing["total"],
        payment_method="ONLINE",
        payment_id=None,
        status="INITIATED",
    )
    db.session.add(order)
    db.session.flush()

    for it in pricing["items"]:
        oi = OrderItem(
            order_id=order.id,
            item_id=it["item_id"],
            name=it["name"],
            qty=it["qty"],
            price=it["price"],
        )
        db.session.add(oi)

    db.session.commit()

    amount_paise = int(round(pricing["total"] * 100))
    return jsonify({"success": True, "order": order_to_dict(order), "amount_paise": amount_paise})


@app.post("/nightlife/order/online/confirm")
def nightlife_order_online_confirm():
    data = request.get_json(force=True) or {}
    order_id = data.get("order_id")
    if not order_id:
        return jsonify({"success": False, "message": "order_id required"}), 400

    order = Order.query.get(order_id)
    if not order:
        return jsonify({"success": False, "message": "Order not found"}), 404

    razorpay_order_id = data.get("razorpay_order_id")
    razorpay_payment_id = data.get("razorpay_payment_id")
    razorpay_signature = data.get("razorpay_signature")
    payment_meta = data.get("payment_meta") or {}

    if RAZORPAY_SECRET and razorpay_order_id and razorpay_payment_id and razorpay_signature:
        payload = f"{razorpay_order_id}|{razorpay_payment_id}"
        computed = hmac.new(bytes(RAZORPAY_SECRET, "utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
        if computed != razorpay_signature:
            return jsonify({"success": False, "message": "Invalid payment signature"}), 400

    order.payment_id = razorpay_payment_id or None
    try:
        order.payment_meta = json.dumps(payment_meta) if isinstance(payment_meta, dict) else str(payment_meta)
    except Exception:
        order.payment_meta = str(payment_meta)
    order.status = "PAID"
    db.session.commit()

    return jsonify({"success": True, "order": order_to_dict(order)})


# Ratings and user-facing APIs
@app.get("/rating/club/<int:club_id>")
def get_rating_for_club(club_id):
    return jsonify(rating_summary(club_id))


@app.post("/rating/add")
def rating_add():
    data = request.get_json(force=True) or {}
    club_id = data.get("club_id")
    stars = int(data.get("stars") or 0)
    name = data.get("name") or ""
    comment = data.get("comment") or ""

    if not club_id or stars <= 0:
        return jsonify({"success": False, "message": "club_id and stars are required"}), 400

    r = Rating(
        club_id=int(club_id),
        name=name,
        stars=stars,
        comment=comment,
        date=datetime.utcnow().strftime("%Y-%m-%d"),
    )
    db.session.add(r)
    db.session.commit()
    return jsonify({"success": True})


@app.get("/nightlife/getClubs")
def nightlife_get_clubs():
    # Return only nightlife clubs intended for table booking
    clubs_q = Club.query.filter_by(is_nightlife=True).all()
    return jsonify([club_to_dict(c) for c in clubs_q])


@app.get("/nightlife/club/<int:club_id>")
def nightlife_get_club(club_id):
    c = Club.query.get(club_id)
    if not c:
        return jsonify({"success": False, "message": "Club not found"}), 404

    rating = rating_summary(club_id)
    club_data = club_to_dict(c)
    club_data["rating_avg"] = rating["avg"]
    club_data["rating_count"] = rating["count"]

    vendor = Vendor.query.get(c.vendor_id)
    if vendor:
        club_data["platform_fee"] = float(vendor.platform_fee or 0)
        club_data["delivery_fee"] = float(vendor.delivery_fee or 0)
        club_data["packing_fee"]  = float(vendor.packing_fee or 0)
        club_data["tax_percent"]  = float(vendor.tax_percent or 0)
    else:
        club_data["platform_fee"] = 10.0
        club_data["delivery_fee"] = 25.0
        club_data["packing_fee"]  = 5.0
        club_data["tax_percent"]  = 5.0

    # include tables and events for nightlife club
    tables = NightlifeTable.query.filter_by(club_id=club_id).all()
    events = NightlifeEvent.query.filter_by(club_id=club_id).all()
    return jsonify({
        "success": True,
        "club": club_data,
        "tables": [table_to_dict(t) for t in tables],
        "events": [event_to_dict(e) for e in events],
    })


@app.get("/nightlife/menu/<int:club_id>")
def nightlife_menu(club_id):
    items = NightlifeItem.query.filter_by(club_id=club_id).all()
    out = []
    for i in items:
        out.append({
            "id": i.id,
            "name": i.item_name,
            "price": float(i.price),
            "description": i.description or "",
            "category": i.category or "",
            "image_url": f"/uploads/{i.image_path}" if i.image_path else None,
        })
    return jsonify(out)


@app.get("/nightlife/coupons/<int:club_id>")
def nightlife_get_coupons(club_id):
    coupons = NightlifeCoupon.query.filter_by(club_id=club_id, active=True).all()
    return jsonify({"success": True, "coupons": [coupon_to_dict(c) for c in coupons]})


@app.post("/nightlife/coupon/validate")
def nightlife_validate_coupon():
    data = request.get_json(force=True) or {}
    club_id = data.get("club_id")
    coupon_id = data.get("coupon_id")
    subtotal = float(data.get("subtotal") or 0)

    if not club_id or not coupon_id:
        return jsonify({"success": False, "message": "club_id and coupon_id required"}), 400

    c = NightlifeCoupon.query.filter_by(id=coupon_id, club_id=club_id, active=True).first()
    if not c:
        return jsonify({"success": False, "message": "Coupon not found"}), 404

    if subtotal < c.min_order:
        return jsonify({"success": False, "message": f"Minimum order ₹{c.min_order:.0f} for this coupon"})

    if c.type == "percent":
        discount = subtotal * (c.value / 100.0)
    else:
        discount = c.value

    if c.max_discount is not None and discount > c.max_discount:
        discount = c.max_discount

    return jsonify({"success": True, "discount": float(f"{discount:.2f}"), "coupon": coupon_to_dict(c)})


# ================== SMALL EXTRA ENDPOINTS FRONTEND USES ==================

@app.get("/api/orders/user/<string:phone>")
def api_orders_by_phone(phone):
    # simple endpoint used by track page (returns orders array)
    try:
        phone = str(phone).strip()
        orders = Order.query.filter((Order.user_phone == phone) | (Order.user_phone == ("+91" + phone))).order_by(Order.created_at.desc()).all()
        return jsonify({"ok": True, "orders": [order_to_dict(o) for o in orders]})
    except Exception as e:
        raise


# ================ DB init & migration helper ==================
def ensure_column_exists():
    """
    For deployments that already have an existing sqlite DB,
    add the 'is_nightlife' column if it is missing. SQLite allows ALTER TABLE ADD COLUMN.
    """
    try:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute("PRAGMA table_info(clubs);")
        cols = [r[1] for r in cur.fetchall()]  # second column is name
        if "is_nightlife" not in cols:
            # add column with default 1 (true). SQLite doesn't have boolean type; use INTEGER 0/1.
            cur.execute("ALTER TABLE clubs ADD COLUMN is_nightlife INTEGER DEFAULT 1;")
            con.commit()
        cur.close()
        con.close()
    except Exception as ex:
        # If DB file doesn't exist yet or alter fails, ignore — will be created by SQLAlchemy create_all later.
        print("ensure_column_exists error (non-fatal):", ex)


def init_db():
    # If DB file exists, ensure column compatibility first
    if os.path.exists(DB_PATH):
        ensure_column_exists()

    db.create_all()

    # Seed vendors/clubs/tables/coupons if empty
    if Vendor.query.count() == 0:
        v = Vendor(restaurant_name="My Nightlife Vendor", email="vendor@example.com", phone="", address="")
        db.session.add(v)
        db.session.commit()

    if Club.query.count() == 0:
        v = Vendor.query.first()
        # create one nightlife club and one food-order club to demonstrate separation
        c1 = Club(
            vendor_id=v.id,
            club_name="Demo Night Club",
            location="City Center",
            music="Bollywood / EDM",
            description="Sample nightlife club created automatically.",
            is_nightlife=True
        )
        c2 = Club(
            vendor_id=v.id,
            club_name="Demo Food Place",
            location="Market Street",
            music="",
            description="Sample food ordering restaurant (not for table booking).",
            is_nightlife=False
        )
        db.session.add_all([c1, c2])
        db.session.commit()

    if NightlifeCoupon.query.count() == 0:
        club = Club.query.filter_by(is_nightlife=True).first()
        if club:
            coup1 = NightlifeCoupon(club_id=club.id, code="NIGHT50", type="percent", value=50, min_order=200, max_discount=150, active=True)
            db.session.add(coup1)
            db.session.commit()

    demo_club = Club.query.filter_by(is_nightlife=True).first()
    demo_vendor = Vendor.query.first()
    if demo_club and NightlifeTable.query.filter_by(club_id=demo_club.id).count() == 0:
        t = NightlifeTable(vendor_id=demo_vendor.id, club_id=demo_club.id, category="VIP Table", capacity="4", price=1500, feature="Near Bar", total_tables=5, free_tables=5)
        db.session.add(t)
        db.session.commit()
    if demo_club and NightlifeEvent.query.filter_by(club_id=demo_club.id).count() == 0:
        e = NightlifeEvent(vendor_id=demo_vendor.id, club_id=demo_club.id, name="Demo EDM Night", date=(datetime.utcnow().strftime("%Y-%m-%d")), fee=200)
        db.session.add(e)
        db.session.commit()


if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(host="127.0.0.1", port=5001, debug=True)
