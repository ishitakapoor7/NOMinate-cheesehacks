"""Profile CRUD. Replaces the session ``profile`` blob and in-memory dict."""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import db
from app.models import Profile

bp = Blueprint("profile", __name__, url_prefix="/api")

LIST_FIELDS = ("cuisines", "dietary_restrictions", "allergies", "available_ingredients")
SCALAR_FIELDS = ("skill_level", "weight_goal", "budget", "location")


def _as_list(value) -> list[str]:
    """Accept a list of strings or a comma-separated string."""
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(item).strip() for item in value if str(item).strip()]


def profile_payload(profile: Profile) -> dict:
    return {
        "cuisines": profile.cuisines,
        "dietary_restrictions": profile.dietary_restrictions,
        "allergies": profile.allergies,
        "available_ingredients": profile.available_ingredients,
        "skill_level": profile.skill_level,
        "weight_goal": profile.weight_goal,
        "budget": profile.budget,
        "location": profile.location,
        "updated_at": profile.updated_at.isoformat(),
    }


@bp.route("/profile", methods=["GET"])
@jwt_required()
def get_profile():
    profile = Profile.query.filter_by(user_id=int(get_jwt_identity())).first()
    if not profile:
        return jsonify({"error": "No profile found. Please complete profile setup."}), 404
    return jsonify({"profile": profile_payload(profile)}), 200


@bp.route("/profile", methods=["PUT", "POST"])
@jwt_required()
def upsert_profile():
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}

    profile = Profile.query.filter_by(user_id=user_id).first()
    created = profile is None
    if created:
        profile = Profile(user_id=user_id)
        db.session.add(profile)

    for field in LIST_FIELDS:
        if field in data:
            setattr(profile, field, _as_list(data[field]))
    for field in SCALAR_FIELDS:
        if field in data:
            setattr(profile, field, str(data[field] or "").strip())

    db.session.commit()
    return jsonify({"profile": profile_payload(profile)}), 201 if created else 200
