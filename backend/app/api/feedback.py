"""Feedback endpoint: turns rejection reasons into persistent rating signal.

Replaces the append-only feedback_log.jsonl and the session excluded_dishes
list. A dislike (value <= 2) excludes the dish permanently; anything else is
excluded only by the recent-recommendation window in /api/recommend.
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.api.recommend import latest_recommendation
from app.extensions import db
from app.models import Rating

bp = Blueprint("feedback", __name__, url_prefix="/api")

# reason -> (rating value, rating source)
REASON_SIGNAL = {
    "I just don't like it": (1.0, "disliked"),
    "Recently Eaten": (3.0, "explicit_feedback"),
}
DEFAULT_SIGNAL = (2.5, "explicit_feedback")  # free-text "Other" — mild negative


@bp.route("/feedback", methods=["POST"])
@jwt_required()
def feedback():
    user_id = int(get_jwt_identity())
    rec = latest_recommendation(user_id)
    if not rec:
        return jsonify({"error": "No active recommendation"}), 404

    data = request.get_json(silent=True) or {}
    reason = (data.get("feedback_reason") or "").strip()
    value, source = REASON_SIGNAL.get(reason, DEFAULT_SIGNAL)

    rec.action = "rejected"
    db.session.add(
        Rating(user_id=user_id, dish_id=rec.dish_id, value=value, source=source)
    )
    db.session.commit()

    return jsonify({"message": "Feedback recorded"}), 200
