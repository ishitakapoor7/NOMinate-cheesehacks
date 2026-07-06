from datetime import datetime

from sqlalchemy.dialects.postgresql import ARRAY

from app.extensions import db


class Profile(db.Model):
    """A user's editable food preferences. One row per user.

    Replaces both the old in-memory ``profiles`` dict and the Flask session
    ``profile`` blob.
    """

    __tablename__ = "profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False
    )

    cuisines = db.Column(ARRAY(db.String), nullable=False, default=list)
    dietary_restrictions = db.Column(ARRAY(db.String), nullable=False, default=list)
    allergies = db.Column(ARRAY(db.String), nullable=False, default=list)
    available_ingredients = db.Column(ARRAY(db.String), nullable=False, default=list)

    skill_level = db.Column(db.String(20), nullable=False, default="beginner")
    weight_goal = db.Column(db.String(20), nullable=False, default="maintain")
    budget = db.Column(db.String(20), nullable=False, default="<$50")
    location = db.Column(db.String(255), nullable=False, default="")

    updated_at = db.Column(
        db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user = db.relationship("User", back_populates="profile")

    def __repr__(self) -> str:
        return f"<Profile user_id={self.user_id}>"
