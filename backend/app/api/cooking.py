"""Cooking endpoint: ingredient checklist for the last recommendation.

Choosing to cook a dish is a strong positive signal, so it also marks the
recommendation and writes a rating for retraining.
"""
from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.api.recommend import latest_recommendation
from app.extensions import db
from app.models import Profile, Rating

bp = Blueprint("cooking", __name__, url_prefix="/api")

COOKED_RATING = 5.0


@bp.route("/cooking", methods=["POST"])
@jwt_required()
def cooking():
    user_id = int(get_jwt_identity())
    rec = latest_recommendation(user_id)
    if not rec:
        return jsonify({"error": "No recommendation found"}), 404

    profile = Profile.query.filter_by(user_id=user_id).first()
    available = {
        ing.strip().lower() for ing in (profile.available_ingredients if profile else [])
    }
    ingredients = [
        {"name": ing.strip(), "available": ing.strip().lower() in available}
        for ing in rec.dish.ingredients.split("|")
        if ing.strip()
    ]

    rec.action = "cooked"
    db.session.add(
        Rating(user_id=user_id, dish_id=rec.dish_id, value=COOKED_RATING, source="cooked")
    )
    db.session.commit()

    return jsonify({"dish": rec.dish.dish_name, "ingredients": ingredients}), 200
