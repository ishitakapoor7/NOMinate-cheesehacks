"""Takeout endpoint: restaurants serving the last recommended dish.

Backed by the Google Places API (New) via services/places.py. Ordering out is
an implicit positive signal, so it's rated too.
"""
import re

from flask import Blueprint, Response, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.api.recommend import latest_recommendation
from app.extensions import db
from app.models import Profile, Rating
from app.services.places import fetch_photo, search_restaurants

bp = Blueprint("takeout", __name__, url_prefix="/api")

TAKEOUT_RATING = 4.0

PHOTO_NAME_RE = re.compile(r"^places/[^/]+/photos/[^/]+$")


@bp.route("/takeout", methods=["POST"])
@jwt_required()
def takeout():
    user_id = int(get_jwt_identity())
    rec = latest_recommendation(user_id)
    if not rec:
        return jsonify({"error": "No recommendation found"}), 404

    profile = Profile.query.filter_by(user_id=user_id).first()
    if not profile:
        return jsonify({"error": "No profile found"}), 404
    if not profile.location:
        return jsonify({"error": "No location set. Please update your profile."}), 400

    if not current_app.config["GOOGLE_PLACES_API_KEY"]:
        return jsonify({"error": "Takeout search isn't configured yet"}), 503

    try:
        restaurants = search_restaurants(
            rec.dish.dish_name, profile.location, profile.budget
        )
    except Exception:
        restaurants = []

    rec.action = "takeout"
    db.session.add(
        Rating(user_id=user_id, dish_id=rec.dish_id, value=TAKEOUT_RATING, source="takeout")
    )
    db.session.commit()

    return jsonify({"restaurants": restaurants}), 200


@bp.route("/takeout/photo", methods=["GET"])
def takeout_photo():
    """Proxy a Places photo so the API key never reaches the browser.

    No JWT here — <img> tags can't send Authorization headers. Photo resource
    names are opaque IDs and the regex pins this proxy to Places photos only.
    """
    photo_name = request.args.get("name", "")
    if not PHOTO_NAME_RE.match(photo_name):
        return jsonify({"error": "Invalid photo reference"}), 400
    if not current_app.config["GOOGLE_PLACES_API_KEY"]:
        return jsonify({"error": "Takeout search isn't configured yet"}), 503
    try:
        content, content_type = fetch_photo(photo_name)
    except Exception:
        return jsonify({"error": "Photo unavailable"}), 502
    return Response(
        content,
        mimetype=content_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )
