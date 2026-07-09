"""Auth endpoints: email/password signup + login, Google sign-in, JWT refresh.

Every successful auth response has the same shape:
{"user": {...}, "access_token": "...", "refresh_token": "..."}
"""
from flask import current_app, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    jwt_required,
)
from werkzeug.security import check_password_hash, generate_password_hash

from app.auth import bp
from app.auth.google import GoogleAuthError, verify_google_id_token
from app.extensions import db
from app.models import User


def _user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "has_profile": user.profile is not None,
    }


def _auth_response(user: User, status: int = 200):
    return (
        jsonify(
            {
                "user": _user_payload(user),
                "access_token": create_access_token(identity=str(user.id)),
                "refresh_token": create_refresh_token(identity=str(user.id)),
            }
        ),
        status,
    )


@bp.route("/signup", methods=["POST"])
def signup():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not username or not email or not password:
        return jsonify({"error": "All fields are required"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "User already exists"}), 409

    user = User(
        username=username,
        email=email,
        password_hash=generate_password_hash(password, method="pbkdf2:sha256"),
    )
    db.session.add(user)
    db.session.commit()
    return _auth_response(user, 201)


@bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = User.query.filter_by(email=email).first()
    if not user or not user.password_hash or not check_password_hash(
        user.password_hash, password
    ):
        return jsonify({"error": "Invalid credentials"}), 401
    return _auth_response(user)


@bp.route("/google", methods=["POST"])
def google_sign_in():
    client_id = current_app.config["GOOGLE_CLIENT_ID"]
    if not client_id:
        return jsonify({"error": "Google sign-in is not configured"}), 503

    data = request.get_json(silent=True) or {}
    credential = data.get("credential")
    if not credential:
        return jsonify({"error": "Missing Google credential"}), 400

    try:
        claims = verify_google_id_token(credential, client_id)
    except GoogleAuthError:
        return jsonify({"error": "Invalid Google credential"}), 401

    sub = claims["sub"]
    email = (claims.get("email") or "").lower()

    user = User.query.filter_by(google_sub=sub).first()
    if not user and email:
        # Existing email/password account signing in with Google: link it.
        user = User.query.filter_by(email=email).first()
        if user:
            user.google_sub = sub
    if not user:
        if not email:
            return jsonify({"error": "Google account has no email"}), 400
        user = User(
            email=email,
            username=claims.get("name") or email.split("@")[0],
            google_sub=sub,
            password_hash=None,
        )
        db.session.add(user)
    db.session.commit()
    return _auth_response(user)


@bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    return jsonify({"access_token": create_access_token(identity=identity)}), 200


@bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"user": _user_payload(user)}), 200
