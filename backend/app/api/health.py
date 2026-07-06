from flask import Blueprint, jsonify

bp = Blueprint("health", __name__)


@bp.route("/", methods=["GET"])
def index():
    return jsonify({"message": "NOMinate API is running."}), 200


@bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200
