"""Flask extension instances.

Kept separate from the app factory so models and blueprints can import them
without creating a circular import.
"""
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate = Migrate()
