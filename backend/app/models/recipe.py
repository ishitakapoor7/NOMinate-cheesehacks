from datetime import datetime

from app.extensions import db


class Recipe(db.Model):
    """A dish's full recipe, fetched from Spoonacular once and cached forever.

    A row with empty ``steps`` records a lookup miss so we never spend quota
    re-asking about a dish Spoonacular doesn't know.
    """

    __tablename__ = "recipes"

    id = db.Column(db.Integer, primary_key=True)
    dish_id = db.Column(
        db.Integer, db.ForeignKey("dishes.id"), unique=True, nullable=False
    )

    title = db.Column(db.String(255), nullable=False, default="")
    image_url = db.Column(db.Text, nullable=False, default="")
    servings = db.Column(db.Integer, nullable=True)
    ready_minutes = db.Column(db.Integer, nullable=True)
    prep_minutes = db.Column(db.Integer, nullable=True)
    cook_minutes = db.Column(db.Integer, nullable=True)
    source_name = db.Column(db.String(255), nullable=False, default="")
    source_url = db.Column(db.Text, nullable=False, default="")
    ingredients = db.Column(db.JSON, nullable=False, default=list)  # [{name, amount}]
    steps = db.Column(db.JSON, nullable=False, default=list)  # [str]

    fetched_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    dish = db.relationship("Dish", backref=db.backref("recipe", uselist=False))

    @property
    def found(self) -> bool:
        return bool(self.steps)

    def __repr__(self) -> str:
        return f"<Recipe dish_id={self.dish_id} {'found' if self.found else 'miss'}>"
