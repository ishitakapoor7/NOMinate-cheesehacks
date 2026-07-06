from datetime import datetime

from app.extensions import db

# Where a rating signal came from. Explicit feedback and like/dislike are direct;
# cooked/takeout are implicit positive signals.
RATING_SOURCES = ("explicit_feedback", "liked", "disliked", "cooked", "takeout")


class Rating(db.Model):
    """A real user's feedback signal for a dish — the ML training signal.

    Replaces the append-only feedback_log.jsonl. ``value`` is on a 1-5 scale.
    """

    __tablename__ = "ratings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    dish_id = db.Column(db.Integer, db.ForeignKey("dishes.id"), nullable=False, index=True)
    value = db.Column(db.Float, nullable=False)
    source = db.Column(db.String(30), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship("User", back_populates="ratings")
    dish = db.relationship("Dish")

    def __repr__(self) -> str:
        return f"<Rating user={self.user_id} dish={self.dish_id} value={self.value}>"
