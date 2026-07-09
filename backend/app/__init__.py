"""Application factory.

Creates and wires the Flask app: config, extensions (db, migrate, CORS),
models, and blueprints. The single-file What2Eat.py prototype is replaced by
this package; its route logic is ported into blueprints over the coming phases.
"""
from flask import Flask
from flask_cors import CORS

from app.config import Config, get_config
from app.extensions import db, jwt, migrate


def create_app(config_class: type[Config] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class or get_config())

    # Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    CORS(
        app,
        resources={r"/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=True,
    )

    # Import models so they're registered on db.metadata for migrations.
    from app import models  # noqa: F401

    # Blueprints
    from app.api.cooking import bp as cooking_bp
    from app.api.feedback import bp as feedback_bp
    from app.api.health import bp as health_bp
    from app.api.profile import bp as profile_bp
    from app.api.recommend import bp as recommend_bp
    from app.api.takeout import bp as takeout_bp
    from app.auth import bp as auth_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(recommend_bp)
    app.register_blueprint(cooking_bp)
    app.register_blueprint(takeout_bp)
    app.register_blueprint(feedback_bp)

    return app
