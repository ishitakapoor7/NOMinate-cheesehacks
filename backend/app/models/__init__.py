"""SQLAlchemy models.

Importing this package registers every model on the shared ``db`` metadata so
Flask-Migrate can autogenerate migrations.
"""
from app.models.dish import Dish
from app.models.profile import Profile
from app.models.rating import Rating
from app.models.recommendation import Recommendation
from app.models.user import User

__all__ = ["User", "Profile", "Dish", "Rating", "Recommendation"]
