"""DB-driven retraining.

Blends the real ratings accumulating in Postgres with the synthetic dataset,
retrains the model into a versioned checkpoint directory, and repoints the
``latest`` marker so the serving engine picks it up (see services/recommender).

Real users are namespaced as "real_<db id>" in the embedding table so they can
never collide with synthetic ids; after a retrain, returning users get their
genuinely learned embedding instead of the cold-start average.
"""
import os
from datetime import datetime

import pandas as pd

from app.extensions import db
from app.models import Dish, Profile, Rating
from app.services.recommender import CHECKPOINTS, LATEST_POINTER

ML_DATA = os.path.join(os.path.dirname(CHECKPOINTS), "data")

# Each real rating is duplicated this many times so a handful of real users
# isn't drowned out by ~89k synthetic ratings.
REAL_RATING_WEIGHT = 10


def real_user_key(user_id: int) -> str:
    return f"real_{user_id}"


def build_training_frames(real_rating_weight: int = REAL_RATING_WEIGHT):
    """Return (ratings, dishes, users) DataFrames blending synthetic CSVs with
    real rows from the database."""
    ratings = pd.read_csv(os.path.join(ML_DATA, "ratings.csv"))
    users = pd.read_csv(os.path.join(ML_DATA, "users.csv"))

    # Dish catalog from the DB — the source of truth since Phase 1 seeding.
    dishes = pd.DataFrame(
        [
            {
                "dish_id": d.id,
                "dish_name": d.dish_name,
                "cuisine": d.cuisine,
                "category": d.category,
                "dietary_tags": d.dietary_tags,
                "difficulty": d.difficulty,
                "calorie_tier": d.calorie_tier,
                "cost_tier": d.cost_tier,
                "ingredients": d.ingredients,
            }
            for d in Dish.query.all()
        ]
    )

    real_ratings = Rating.query.all()
    if real_ratings:
        real_df = pd.DataFrame(
            [
                {
                    "user_id": real_user_key(r.user_id),
                    "dish_id": r.dish_id,
                    "rating": r.value,
                }
                for r in real_ratings
            ]
        )
        real_df = pd.concat([real_df] * max(1, real_rating_weight), ignore_index=True)
        ratings = pd.concat([ratings, real_df], ignore_index=True)

        rated_user_ids = {r.user_id for r in real_ratings}
        profiles = {
            p.user_id: p
            for p in Profile.query.filter(Profile.user_id.in_(rated_user_ids)).all()
        }
        real_users = pd.DataFrame(
            [
                {
                    "user_id": real_user_key(uid),
                    "preferred_cuisines": "|".join(p.cuisines) if p else "",
                    "skill": p.skill_level if p else "beginner",
                    "health_goal": p.weight_goal if p else "maintain",
                    "budget": p.budget if p else "<$50",
                    "dietary_restrictions": "|".join(p.dietary_restrictions) if p else "",
                }
                for uid in sorted(rated_user_ids)
                for p in [profiles.get(uid)]
            ]
        )
        users = pd.concat([users, real_users], ignore_index=True)

    return ratings, dishes, users


def retrain(epochs: int = 50, real_rating_weight: int = REAL_RATING_WEIGHT, log=print) -> dict:
    """Retrain on blended data into checkpoints/v<timestamp>/ and repoint latest."""
    from ml.train import train_model

    ratings, dishes, users = build_training_frames(real_rating_weight)
    real_count = db.session.query(Rating).count()
    log(f"Retraining on {len(ratings)} ratings ({real_count} real, weighted x{real_rating_weight})")

    version = "v" + datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    out_dir = os.path.join(CHECKPOINTS, version)
    metrics = train_model(ratings, dishes, users, out_dir, epochs=epochs, log=log)

    with open(LATEST_POINTER, "w") as f:
        f.write(version + "\n")
    log(f"Checkpoint {version} is now live (pointer: {LATEST_POINTER})")

    return {"version": version, "out_dir": out_dir, **metrics}
