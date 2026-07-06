from app.extensions import db


class Dish(db.Model):
    """The recommendable catalog, seeded from ml/data/dishes.csv.

    Pipe-delimited fields (dietary_tags, ingredients) are kept as text to match
    what the recommender currently expects; they get split on read.
    """

    __tablename__ = "dishes"

    id = db.Column(db.Integer, primary_key=True)  # mirrors CSV dish_id
    dish_name = db.Column(db.String(255), nullable=False, index=True)
    cuisine = db.Column(db.String(80), nullable=False, default="")
    category = db.Column(db.String(80), nullable=False, default="")
    dietary_tags = db.Column(db.Text, nullable=False, default="")
    difficulty = db.Column(db.String(20), nullable=False, default="beginner")
    calorie_tier = db.Column(db.String(20), nullable=False, default="medium")
    cost_tier = db.Column(db.String(20), nullable=False, default="moderate")
    ingredients = db.Column(db.Text, nullable=False, default="")

    def __repr__(self) -> str:
        return f"<Dish {self.id} {self.dish_name}>"
