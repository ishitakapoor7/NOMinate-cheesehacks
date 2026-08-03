"""Live per-user taste learning — the online layer on top of the CF embedding.

The offline model only relearns a user's embedding on a full retrain
(``flask retrain``). Between retrains, this reads the ratings a user has already
generated — including the *implicit* ones (cooking a dish writes 5.0, ordering
it writes 4.0) so it learns even from people who never fill a feedback card — and
turns them into per-cuisine and per-ingredient affinities the recommender folds
into scoring on every request.
"""
import re
from datetime import datetime

from app.extensions import db
from app.models import Dish, Rating

# Ratings are on a 1-5 scale; 3 is neutral, so (value - 3) is the signed signal.
_NEUTRAL = 3.0
# Older signals matter less: weight halves roughly every this-many days.
_HALFLIFE_DAYS = 60.0
_WORD_RE = re.compile(r"[a-z]+")


def _recency_weight(created_at: datetime) -> float:
    if not created_at:
        return 1.0
    age_days = max((datetime.utcnow() - created_at).total_seconds() / 86400.0, 0.0)
    return 0.5 ** (age_days / _HALFLIFE_DAYS)


def _clip(x: float) -> float:
    return max(-1.0, min(1.0, x))


def learned_affinity(user_id: int) -> dict:
    """Aggregate a user's own ratings into taste affinities.

    Returns ``{"cuisines": {name: score}, "ingredients": {word: score}}`` with
    scores in [-1, 1] (positive = liked). Empty dicts for users with no ratings,
    so a brand-new account behaves exactly as before (pure cold start)."""
    rows = (
        db.session.query(Rating.value, Rating.created_at, Dish.cuisine, Dish.ingredients)
        .join(Dish, Dish.id == Rating.dish_id)
        .filter(Rating.user_id == user_id)
        .all()
    )
    if not rows:
        return {"cuisines": {}, "ingredients": {}}

    cuisine_num, cuisine_den = {}, {}
    ing_num, ing_den = {}, {}
    for value, created_at, cuisine, ingredients in rows:
        weight = _recency_weight(created_at)
        signal = (float(value) - _NEUTRAL) * weight
        if cuisine:
            key = cuisine.strip().lower()
            cuisine_num[key] = cuisine_num.get(key, 0.0) + signal
            cuisine_den[key] = cuisine_den.get(key, 0.0) + weight
        for word in {w for w in _WORD_RE.findall((ingredients or "").lower())}:
            ing_num[word] = ing_num.get(word, 0.0) + signal
            ing_den[word] = ing_den.get(word, 0.0) + weight

    cuisines = {k: _clip(cuisine_num[k] / cuisine_den[k]) for k in cuisine_num if cuisine_den[k]}
    ingredients = {k: _clip(ing_num[k] / ing_den[k]) for k in ing_num if ing_den[k]}
    return {"cuisines": cuisines, "ingredients": ingredients}
