from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# USER TABLE
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    email = db.Column(db.String(200), unique=True)
    phone = db.Column(db.String(20), unique=True)
    password = db.Column(db.String(200))

with app.app_context():
    db.create_all()


# REGISTER USER AFTER OTP
@app.route("/auth/register", methods=["POST"])
def register():
    data = request.json
    name = data.get("name")
    email = data.get("email")
    phone = data.get("phone")
    password = data.get("password")

    if User.query.filter((User.email == email) | (User.phone == phone)).first():
        return jsonify({"success": False, "error": "Account already exists"}), 400

    u = User(name=name, email=email, phone=phone, password=password)
    db.session.add(u)
    db.session.commit()

    return jsonify({"success": True})


# LOGIN USER
@app.route("/auth/login", methods=["POST"])
def login():
    data = request.json
    email_or_phone = data.get("email")
    password = data.get("password")

    u = User.query.filter(
        (User.email == email_or_phone) | (User.phone == email_or_phone)
    ).first()

    if not u:
        return jsonify({"success": False, "error": "Account not found"}), 404

    if u.password != password:
        return jsonify({"success": False, "error": "Incorrect password"}), 400

    return jsonify({
        "success": True,
        "user": {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "phone": u.phone
        }
    })


if __name__ == "__main__":
    app.run(port=5001, debug=True)
