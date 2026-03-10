"""
Nightlife Main Service Routes
=============================
API endpoints for: Clubs, Menu Items, Ratings, Coupons, Events
"""

from flask import Blueprint, request, jsonify
from . import db
from .models import Club, NightlifeItem, Rating, NightlifeCoupon, NightlifeEvent
from datetime import datetime

main_bp = Blueprint("main", __name__)

# ==================== CLUBS ====================

@main_bp.route("/clubs", methods=["GET"])
def get_clubs():
    try:
        clubs = Club.query.filter_by(status="open").all()

        return jsonify({
            "success": True,
            "data": [c.to_dict() for c in clubs]
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@main_bp.route("/clubs/<int:club_id>", methods=["GET"])
def get_club(club_id):
    try:
        club = Club.query.get(club_id)

        if not club:
            return jsonify({
                "success": False,
                "message": "Club not found"
            }), 404

        return jsonify({
            "success": True,
            "data": club.to_dict()
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@main_bp.route("/clubs", methods=["POST"])
def create_club():
    try:
        data = request.get_json()

        club = Club(
            vendor_id=data.get("vendor_id"),
            club_name=data.get("club_name"),
            description=data.get("description"),
            location=data.get("location"),
            city=data.get("city"),
            image=data.get("image"),
            music=data.get("music"),
            status=data.get("status", "open")
        )

        db.session.add(club)
        db.session.commit()

        return jsonify({
            "success": True,
            "data": club.to_dict(),
            "message": "Club created successfully"
        }), 201

    except Exception as e:
        db.session.rollback()

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# ==================== MENU ITEMS ====================

@main_bp.route("/clubs/<int:club_id>/items", methods=["GET"])
def get_menu_items(club_id):

    try:
        items = NightlifeItem.query.filter_by(
            club_id=club_id,
            is_available=True
        ).all()

        return jsonify({
            "success": True,
            "data": [i.to_dict() for i in items]
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@main_bp.route("/items", methods=["POST"])
def create_menu_item():

    try:
        data = request.get_json()

        item = NightlifeItem(
            club_id=data.get("club_id"),
            name=data.get("name"),
            description=data.get("description"),
            category=data.get("category"),
            price=data.get("price"),
            image_url=data.get("image_url"),
            is_available=data.get("is_available", True)
        )

        db.session.add(item)
        db.session.commit()

        return jsonify({
            "success": True,
            "data": item.to_dict(),
            "message": "Item created successfully"
        }), 201

    except Exception as e:
        db.session.rollback()

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# ==================== VENDOR MENU ====================

@main_bp.route("/nightlife/vendor/<int:vendor_id>/menu", methods=["GET"])
def get_vendor_menu(vendor_id):
    """
    Compatibility API for frontend
    """

    try:
        club = Club.query.filter_by(vendor_id=vendor_id).first()

        if not club:
            return jsonify({
                "success": False,
                "message": "Club not found for this vendor"
            }), 404

        items = NightlifeItem.query.filter_by(
            club_id=club.id,
            is_available=True
        ).all()

        return jsonify({
            "success": True,
            "data": [i.to_dict() for i in items]
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# ==================== RATINGS ====================

@main_bp.route("/clubs/<int:club_id>/ratings", methods=["GET"])
def get_ratings(club_id):

    try:
        ratings = Rating.query.filter_by(
            club_id=club_id
        ).order_by(Rating.created_at.desc()).all()

        avg = sum(r.stars for r in ratings) / len(ratings) if ratings else 0

        return jsonify({
            "success": True,
            "data": {
                "items": [r.to_dict() for r in ratings],
                "avg": round(avg, 1),
                "count": len(ratings)
            }
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# ==================== EVENTS ====================

@main_bp.route("/clubs/<int:club_id>/events", methods=["GET"])
def get_events(club_id):

    try:
        events = NightlifeEvent.query.filter_by(
            club_id=club_id,
            is_active=True
        ).order_by(NightlifeEvent.event_date.asc()).all()

        return jsonify({
            "success": True,
            "data": [e.to_dict() for e in events]
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# ==================== HEALTH ====================

@main_bp.route("/health", methods=["GET"])
def health():

    return jsonify({
        "success": True,
        "service": "nightlife-main",
        "status": "running"
    })