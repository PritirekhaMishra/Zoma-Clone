import os
import random
import datetime
import smtplib
from email.message import EmailMessage

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from twilio.rest import Client
from dotenv import load_dotenv

# --------------------- SETUP ---------------------
app = Flask(__name__)
CORS(app)


app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
load_dotenv()

# --------------------- TWILIO ---------------------
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE")

twilio_client = Client(TWILIO_SID, TWILIO_TOKEN)

# --------------------- EMAIL ----------------------
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASS = os.getenv("GMAIL_PASS")


# --------------------- MODEL ----------------------
class OTP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(50))            # user / vendor / admin
    email = db.Column(db.String(200))
    phone = db.Column(db.String(20))
    code = db.Column(db.String(10))
    expires_at = db.Column(db.DateTime)
    used = db.Column(db.Boolean, default=False)


with app.app_context():
    db.create_all()


# ----------------- HELPERS ------------------------
def generate_otp():
    return str(random.randint(1000, 9999))


def send_sms(phone, code):
    if not phone:
        return
    try:
        twilio_client.messages.create(
            from_=TWILIO_PHONE,
            to=phone,
            body=f"Your ZomaClone OTP is {code}. Valid for 5 minutes."
        )
    except Exception as e:
        print("SMS error:", e)


def send_email(email, code):
    if not email:
        return
    try:
        msg = EmailMessage()
        msg["Subject"] = "Your ZomaClone OTP"
        msg["From"] = GMAIL_USER
        msg["To"] = email
        msg.set_content(f"Your OTP is {code}")

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_USER, GMAIL_PASS)
            smtp.send_message(msg)

    except Exception as e:
        print("Email error:", e)


# ------------------ SEND OTP -----------------------
@app.route("/otp/send", methods=["POST"])
def send_otp():
    data = request.json

    role = data.get("role")      # user/vendor/admin
    email = data.get("email")
    phone = data.get("phone")

    if not role:
        return jsonify({"error": "role missing"}), 400

    code = generate_otp()
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=5)

    otp = OTP(role=role, email=email, phone=phone, code=code, expires_at=expires_at)
    db.session.add(otp)
    db.session.commit()

    send_sms(phone, code)
    send_email(email, code)

    return jsonify({"message": "OTP sent"})


# ------------------ VERIFY OTP ----------------------
@app.route("/otp/verify", methods=["POST"])
def verify_otp():
    data = request.json

    role = data.get("role")
    email = data.get("email")
    phone = data.get("phone")
    code = data.get("code")

    otp = OTP.query.filter_by(role=role, code=code, used=False).order_by(OTP.id.desc()).first()

    if not otp:
        return jsonify({"valid": False, "error": "Invalid OTP"}), 400

    if otp.expires_at < datetime.datetime.utcnow():
        return jsonify({"valid": False, "error": "OTP expired"}), 400

    otp.used = True
    db.session.commit()

    return jsonify({"valid": True, "message": "OTP verified"})


# ------------------ RUN SERVER ---------------------
if __name__ == "__main__":
    app.run(debug=True)
