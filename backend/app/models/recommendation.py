from datetime import datetime

from app.extensions import db


class Recommendation(db.Model):
    """A dish shown to a user. Provides history and the persistent
    "recently shown / don't repeat" memory that used to live in the session.
    """

    __tablename__ = "recommendations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    dish_id = db.Column(db.Integer, db.ForeignKey("dishes.id"), nullable=False, index=True)
    score = db.Column(db.Float, nullable=True)
    shown_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    # null = shown but no action yet; otherwise cooked | takeout | rejected
    action = db.Column(db.String(20), nullable=True)

    user = db.relationship("User", back_populates="recommendations")
    dish = db.relationship("Dish")

    def __repr__(self) -> str:
        return f"<Recommendation user={self.user_id} dish={self.dish_id}>"
