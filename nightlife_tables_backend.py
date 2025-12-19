import os
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.utils import secure_filename

# ======================================
# BASIC CONFIG
# ======================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "nightlife_table.db")

UPLOAD_ROOT = os.path.join(BASE_DIR, "uploads")
BANNER_DIR = os.path.join(UPLOAD_ROOT, "banners")
os.makedirs(BANNER_DIR, exist_ok=True)

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + DB_PATH
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ✅ CORS (FIXED)
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    supports_credentials=True
)

# ======================================
# MODELS
# ======================================
class Vendor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    restaurant_name = db.Column(db.String(120))
    upi_id = db.Column(db.String(120))
    banner = db.Column(db.String(255))

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, unique=True)
    maxAdvanceDays = db.Column(db.Integer, default=365)
    cancelBeforeHrs = db.Column(db.Integer, default=2)

class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, unique=True)
    addr1 = db.Column(db.String(255))
    addr2 = db.Column(db.String(255))
    city = db.Column(db.String(80))
    state = db.Column(db.String(80))
    pincode = db.Column(db.String(20))

class TableType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer)
    name = db.Column(db.String(80))
    seats = db.Column(db.Integer)
    total = db.Column(db.Integer)
    price = db.Column(db.Integer)
    cancel = db.Column(db.Integer)
    timeStart = db.Column(db.String(5))
    timeEnd = db.Column(db.String(5))

class Table(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type_id = db.Column(db.Integer)
    num = db.Column(db.Integer)
    status = db.Column(db.String(20), default="free")

class Slot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer)
    name = db.Column(db.String(80))
    start = db.Column(db.String(5))
    end = db.Column(db.String(5))

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer)
    type_id = db.Column(db.Integer)
    slot_id = db.Column(db.Integer)
    date = db.Column(db.String(20))
    customer = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    tables = db.Column(db.String(255))
    price = db.Column(db.Integer)
    status = db.Column(db.String(20), default="upcoming")
    createdAt = db.Column(db.DateTime, default=datetime.utcnow)

# ======================================
# INIT DB
# ======================================
with app.app_context():
    db.create_all()

# ======================================
# HELPERS
# ======================================
def get_vendor():
    vid = request.args.get("vendor_id", type=int)
    return Vendor.query.get(vid) if vid else None

# ======================================
# VENDOR (EMAIL ONLY)
# ======================================
@app.route("/api/rest/vendor/by_email", methods=["POST"])
def vendor_by_email():
    data = request.get_json(force=True)
    email = data.get("email", "").strip()
    name = data.get("restaurant_name", "").strip()

    if not email:
        return jsonify(success=False, message="Email required"), 400

    vendor = Vendor.query.filter_by(email=email).first()
    if not vendor:
        vendor = Vendor(email=email, restaurant_name=name)
        db.session.add(vendor)
        db.session.commit()
        db.session.add(Settings(vendor_id=vendor.id))
        db.session.commit()

    return jsonify(success=True, vendor={
        "id": vendor.id,
        "email": vendor.email,
        "restaurant_name": vendor.restaurant_name,
        "upi_id": vendor.upi_id
    })

@app.route("/api/rest/vendor/me")
def vendor_me():
    v = get_vendor()
    if not v:
        return jsonify(success=False)

    s = Settings.query.filter_by(vendor_id=v.id).first()
    l = Location.query.filter_by(vendor_id=v.id).first()

    return jsonify(
        success=True,
        vendor={"id": v.id, "email": v.email, "restaurant_name": v.restaurant_name, "upi_id": v.upi_id},
        banner=v.banner,
        settings={"maxAdvanceDays": s.maxAdvanceDays, "cancelBeforeHrs": s.cancelBeforeHrs},
        location=l.__dict__ if l else {}
    )

# ======================================
# BANNER
# ======================================
@app.route("/api/rest/banner", methods=["POST", "DELETE"])
def banner():
    v = get_vendor()
    if not v:
        return jsonify(success=False)

    if request.method == "POST":
        f = request.files["banner"]
        name = secure_filename(f.filename)
        f.save(os.path.join(BANNER_DIR, name))
        v.banner = "/uploads/banners/" + name
        db.session.commit()
        return jsonify(success=True, bannerUrl=v.banner)

    v.banner = ""
    db.session.commit()
    return jsonify(success=True)

@app.route("/uploads/banners/<path:p>")
def banners(p):
    return send_from_directory(BANNER_DIR, p)

# ======================================
# UPI
# ======================================
@app.route("/api/rest/vendor/<int:vid>/upi", methods=["PUT"])
def save_upi(vid):
    v = Vendor.query.get(vid)
    v.upi_id = request.json.get("upi_id")
    db.session.commit()
    return jsonify(success=True)

# ======================================
# TABLE TYPES
# ======================================
@app.route("/api/rest/types", methods=["GET","POST"])
def types():
    v = get_vendor()

    if request.method == "GET":
        out=[]
        for t in TableType.query.filter_by(vendor_id=v.id):
            tables = Table.query.filter_by(type_id=t.id).all()
            out.append({
                "id":t.id,"name":t.name,"seats":t.seats,"total":t.total,
                "price":t.price,"cancel":t.cancel,
                "freeCount":sum(x.status=="free" for x in tables),
                "reservedCount":sum(x.status=="reserved" for x in tables),
                "unavailCount":sum(x.status=="unavailable" for x in tables),
                "timeStart":t.timeStart,"timeEnd":t.timeEnd,
                "displayTime":f"{t.timeStart} - {t.timeEnd}"
            })
        return jsonify(success=True, types=out)

    d=request.json
    t=TableType.query.get(d.get("id")) if d.get("id") else TableType(vendor_id=v.id)
    for k in ["name","seats","total","price","cancel","timeStart","timeEnd"]:
        setattr(t,k,d[k])
    db.session.add(t); db.session.commit()

    if not d.get("id"):
        for i in range(1,t.total+1):
            db.session.add(Table(type_id=t.id,num=i))
        db.session.commit()

    return jsonify(success=True)

@app.route("/api/rest/types/<int:id>", methods=["DELETE"])
def del_type(id):
    Table.query.filter_by(type_id=id).delete()
    TableType.query.filter_by(id=id).delete()
    db.session.commit()
    return jsonify(success=True)

@app.route("/api/rest/types/<int:id>/tables")
def get_tables(id):
    return jsonify(success=True, tables=[
        {"id":t.id,"num":t.num,"status":t.status}
        for t in Table.query.filter_by(type_id=id)
    ])

@app.route("/api/rest/tables/<int:id>/toggle", methods=["POST"])
def toggle_table(id):
    t=Table.query.get(id)
    t.status="unavailable" if t.status=="free" else "free"
    db.session.commit()
    return jsonify(success=True)

@app.route("/api/rest/tables/mark_all_free", methods=["POST"])
def mark_all_free():
    Table.query.filter_by(type_id=request.json["typeId"]).update({"status":"free"})
    db.session.commit()
    return jsonify(success=True)

# ======================================
# SLOTS
# ======================================
@app.route("/api/rest/slots", methods=["GET","POST"])
def slots():
    v=get_vendor()
    if request.method=="GET":
        return jsonify(success=True, slots=[
            {"id":s.id,"name":s.name,"start":s.start,"end":s.end}
            for s in Slot.query.filter_by(vendor_id=v.id)
        ])
    d=request.json
    s=Slot.query.get(d.get("id")) if d.get("id") else Slot(vendor_id=v.id)
    s.name,s.start,s.end=d["name"],d["start"],d["end"]
    db.session.add(s); db.session.commit()
    return jsonify(success=True)

@app.route("/api/rest/slots/<int:id>", methods=["DELETE"])
def del_slot(id):
    Slot.query.filter_by(id=id).delete()
    db.session.commit()
    return jsonify(success=True)

# ======================================
# BOOKINGS
# ======================================
@app.route("/api/rest/bookings", methods=["GET","POST"])
def bookings():
    v=get_vendor()
    if request.method=="GET":
        return jsonify(success=True, bookings=[{
            "id":b.id,"customer":b.customer,"phone":b.phone,
            "typeName":TableType.query.get(b.type_id).name,
            "slotName":Slot.query.get(b.slot_id).name,
            "tables":b.tables.split(","),"price":b.price,
            "status":b.status,"date":b.date,
            "createdAt":b.createdAt.isoformat()
        } for b in Booking.query.filter_by(vendor_id=v.id)])

    d=request.json
    t=TableType.query.get(d["typeId"])
    free=Table.query.filter_by(type_id=t.id,status="free").limit(d["count"]).all()
    for x in free: x.status="reserved"

    b=Booking(
        vendor_id=v.id,type_id=t.id,slot_id=d["slotId"],
        date=d["date"],customer=d["customer"],phone=d["phone"],
        tables=",".join(str(x.num) for x in free),
        price=t.price*d["count"]
    )
    db.session.add(b); db.session.commit()
    return jsonify(success=True)

@app.route("/api/rest/bookings/<int:id>/toggle", methods=["POST"])
def toggle_booking(id):
    b=Booking.query.get(id)
    b.status="cancelled" if b.status!="cancelled" else "upcoming"
    db.session.commit()
    return jsonify(success=True)

# ======================================
# SETTINGS & LOCATION
# ======================================
@app.route("/api/rest/settings", methods=["POST"])
def save_settings():
    v=get_vendor()
    s=Settings.query.filter_by(vendor_id=v.id).first()
    s.maxAdvanceDays=request.json["maxAdvanceDays"]
    s.cancelBeforeHrs=request.json["cancelBeforeHrs"]
    db.session.commit()
    return jsonify(success=True)

@app.route("/api/rest/location", methods=["POST"])
def save_location():
    v=get_vendor()
    l=Location.query.filter_by(vendor_id=v.id).first() or Location(vendor_id=v.id)
    for k,val in request.json.items():
        setattr(l,k,val)
    db.session.add(l); db.session.commit()
    return jsonify(success=True)

# ======================================
if __name__ == "__main__":
    app.run(port=5002, debug=True)
