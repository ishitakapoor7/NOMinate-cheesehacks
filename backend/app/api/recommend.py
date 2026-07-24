"""Recommendation endpoint.

Exclusions now come from the database instead of the session:
- dishes the user rated 2 or below are excluded permanently (dislikes)
- dishes shown within the last EXCLUSION_WINDOW_DAYS are excluded so
  consecutive requests yield variety
Every recommendation shown is logged to the recommendations table.
"""
from datetime import datetime, timedelta

from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import func

from app.extensions import db
from app.models import Dish, Profile, Rating, Recommendation
from app.services import recommender

bp = Blueprint("recommend", __name__, url_prefix="/api")

EXCLUSION_WINDOW_DAYS = 14
DISLIKE_THRESHOLD = 2.0


def _engine_profile(profile: Profile) -> dict:
    return {
        "cuisines": profile.cuisines,
        "dietary_restrictions": profile.dietary_restrictions,
        "allergies": profile.allergies,
        "skill_level": profile.skill_level,
        "weight_goal": profile.weight_goal,
        "budget": profile.budget,
    }


def _excluded_dish_names(user_id: int) -> list[str]:
    disliked = (
        db.session.query(Dish.dish_name)
        .join(Rating, Rating.dish_id == Dish.id)
        .filter(Rating.user_id == user_id, Rating.value <= DISLIKE_THRESHOLD)
    )
    cutoff = datetime.utcnow() - timedelta(days=EXCLUSION_WINDOW_DAYS)
    recently_shown = (
        db.session.query(Dish.dish_name)
        .join(Recommendation, Recommendation.dish_id == Dish.id)
        .filter(Recommendation.user_id == user_id, Recommendation.shown_at >= cutoff)
    )
    return sorted({name for (name,) in disliked.union(recently_shown).all()})


@bp.route("/recommend", methods=["GET"])
@jwt_required()
def recommend():
    user_id = int(get_jwt_identity())
    profile = Profile.query.filter_by(user_id=user_id).first()
    if not profile:
        return jsonify({"error": "No profile found. Please complete profile setup."}), 404

    try:
        result = recommender.get_engine().recommend(
            user_profile=_engine_profile(profile),
            available_ingredients=profile.available_ingredients,
            excluded_dishes=_excluded_dish_names(user_id),
            user_id=user_id,
        )
    except Exception as exc:  # engine can fail on unseen categories, missing files
        return jsonify({"error": f"Recommendation failed: {exc}"}), 500

    dish = Dish.query.filter(
        func.lower(Dish.dish_name) == result["dish_name"].lower()
    ).first()
    if dish:
        db.session.add(
            Recommendation(user_id=user_id, dish_id=dish.id, score=result["score"])
        )
        db.session.commit()

    return (
        jsonify(
            {
                "recommendation": result["dish_name"],
                "cuisine": result["cuisine"],
                "score": result["score"],
            }
        ),
        200,
    )


@bp.route("/recommend/latest", methods=["GET"])
@jwt_required()
def latest():
    """The current dish without generating a new one — lets the takeout and
    feedback screens name the dish they're acting on."""
    rec = latest_recommendation(int(get_jwt_identity()))
    if not rec:
        return jsonify({"error": "No recommendation yet"}), 404
    return (
        jsonify({"recommendation": rec.dish.dish_name, "cuisine": rec.dish.cuisine}),
        200,
    )


def latest_recommendation(user_id: int) -> Recommendation | None:
    """The most recent dish shown to this user — shared by cooking/takeout/feedback."""
    return (
        Recommendation.query.filter_by(user_id=user_id)
        .order_by(Recommendation.shown_at.desc(), Recommendation.id.desc())
        .first()
    )
