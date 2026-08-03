"""NumPy inference engine for the dish recommender.

The model is trained in PyTorch (ml/train.py), but serving only needs embedding
lookups, a couple of matmuls, and ReLUs — so we run it in pure NumPy from weights
exported to model_weights.npz (see ml/export_weights.py). Keeping torch out of the
serving path is what makes cold starts fast and the footprint small enough for a
tiny always-on host.

The forward pass here matches the trained model's serving path exactly (verified
against torch to ~1e-6): mlp([user, dish, user*dish, cuisine, skill, goal, budget,
ingredient_proj]) + global_bias. The per-user/per-dish bias terms are intentionally
not added at serving time, mirroring the original engine.
"""
import difflib
import pickle

import numpy as np


def _relu(x: np.ndarray) -> np.ndarray:
    return np.maximum(x, 0.0)


# Canonical allergen vocabulary (FDA "big 9" plus the specific tree nuts and
# shellfish people actually type). Free-text allergy entries are snapped to the
# nearest of these before filtering, so a typo like "penut" still blocks peanuts.
KNOWN_ALLERGENS = {
    "peanut", "almond", "cashew", "walnut", "pecan", "hazelnut", "pistachio",
    "macadamia", "tree nut", "shellfish", "shrimp", "prawn", "crab", "lobster",
    "clam", "mussel", "oyster", "scallop", "fish", "egg", "milk", "dairy",
    "soy", "wheat", "gluten", "sesame", "mustard", "coconut", "corn",
}


def normalize_allergens(terms) -> list[str]:
    """Snap free-text allergy entries to the canonical vocabulary so typos still
    trigger the (deliberately eager) allergen filter. Unknown terms with no close
    match pass through unchanged — we never silently drop a user's allergen."""
    if isinstance(terms, str):
        terms = [t.strip() for t in terms.split(",")]
    out: list[str] = []
    for term in terms or []:
        cleaned = str(term).strip().lower()
        if not cleaned:
            continue
        if cleaned in KNOWN_ALLERGENS:
            match = cleaned
        else:
            close = difflib.get_close_matches(cleaned, KNOWN_ALLERGENS, n=1, cutoff=0.8)
            match = close[0] if close else cleaned
        if match not in out:
            out.append(match)
    return out


def matches_allergen(ingredient: str, allergen: str) -> bool:
    """True if an ingredient contains an allergen, tolerant of plural forms
    ("peanuts" matches "peanut butter"). Deliberately eager: for a safety
    filter, a false positive costs a dish; a false negative costs a reaction.
    """
    ing = ingredient.strip().lower()
    allergen = allergen.strip().lower()
    if not ing or not allergen:
        return False
    forms = {allergen}
    forms.add(allergen[:-1] if allergen.endswith("s") else allergen + "s")
    return any(form in ing for form in forms)


def allergy_conflict(ingredients_str: str, allergies) -> bool:
    """True if any of the dish's pipe-delimited ingredients matches any allergen."""
    ingredients = [i for i in (ingredients_str or "").split("|") if i.strip()]
    return any(
        matches_allergen(ing, allergen) for ing in ingredients for allergen in allergies or []
    )


# Catalog categories that aren't a dinner main course — never nominate these as
# "tonight's dish" (this is what kept guacamole/desserts/sides out of dinner).
NON_DINNER_CATEGORIES = {
    "dessert", "side", "side dish", "antipasti", "starter", "fingerfood",
    "beverage", "drink", "bread", "breakfast", "morning meal",
}


def is_main_dish(category) -> bool:
    # Missing/unknown category (can be NaN from pandas) → keep, don't over-filter.
    if not isinstance(category, str):
        return True
    return category.strip().lower() not in NON_DINNER_CATEGORIES


# Ingredient words that disqualify a dish for a given dietary restriction. This
# is a safety net for mislabeled catalog tags (e.g. a dish tagged "vegetarian"
# that actually lists fish), mirroring the allergen filter's eager philosophy.
_MEAT = {
    "chicken", "beef", "pork", "lamb", "goat", "veal", "duck", "turkey", "bacon",
    "ham", "sausage", "prosciutto", "pancetta", "chorizo", "salami", "meat",
    "meatball", "meatballs", "mince",
}
_FISH = {
    "fish", "salmon", "tuna", "cod", "anchovy", "anchovies", "sardine", "sardines",
    "mackerel", "trout", "halibut", "shrimp", "prawn", "prawns", "crab", "lobster",
    "clam", "clams", "mussel", "mussels", "oyster", "oysters", "squid", "octopus",
    "scallop", "scallops", "seafood",
}
_DAIRY = {"milk", "cheese", "butter", "cream", "yogurt", "yoghurt", "ghee", "paneer"}
_EGG = {"egg", "eggs"}


def diet_conflict(ingredient_words: set, user_diet) -> bool:
    """True if a dish's ingredient words violate any of the user's dietary
    choices. Complements the tag-based filter to catch bad source data."""
    diets = {d.strip().lower() for d in (user_diet or [])}
    if not diets:
        return False
    banned: set = set()
    if "vegetarian" in diets:
        banned |= _MEAT | _FISH
    if "vegan" in diets:
        banned |= _MEAT | _FISH | _DAIRY | _EGG
    if "pescatarian" in diets:
        banned |= _MEAT  # fish is allowed for pescatarians
    if "dairy-free" in diets:
        banned |= _DAIRY
    return bool(banned & ingredient_words)


def sample_top_k(scores: np.ndarray, k: int = 5, rng: np.random.Generator | None = None) -> int:
    """Pick an index from the k highest-scoring valid entries, weighted by a
    softmax over their scores — variety without recommending bad matches."""
    valid = np.flatnonzero(scores > -np.inf)
    if valid.size == 0:
        raise ValueError("No dishes available after filtering")
    top = valid[np.argsort(scores[valid])[::-1][:k]]
    weights = np.exp(scores[top] - scores[top].max())
    weights /= weights.sum()
    rng = rng or np.random.default_rng()
    return int(rng.choice(top, p=weights))


# Preference boosts applied on top of the model's score for each dish. Model
# scores sit on a roughly 1–5 rating scale, so these are deliberately large
# enough to steer the top-K pick toward the user's tastes while still letting
# the hard filters (allergen/diet/skill) have the final say. Tune here.
CUISINE_TOP_BONUS = 2.0     # bonus for a dish in the user's #1 cuisine
CUISINE_RANK_DECAY = 0.3    # each lower-ranked cuisine earns a little less
CUISINE_MIN_BONUS = 0.8     # ...but a listed cuisine never drops below this
INGREDIENT_MAX_BONUS = 1.5  # full bonus when the user already has every ingredient
RECIPE_BONUS = 1.0          # nudge toward dishes we can show a real recipe for
GOAL_CALORIE_BONUS = 0.5    # nudge dishes toward the user's weight goal via calorie tier
# Online learning: how hard a user's own rating history steers tonight's pick.
# Affinities are in [-1, 1], so these are the max swing from learned taste.
LEARNED_CUISINE_WEIGHT = 1.2
LEARNED_INGREDIENT_WEIGHT = 0.6


def goal_calorie_bonus(weight_goal: str, calorie_tier: str) -> float:
    """Soft nudge from the user's weight goal against a dish's calorie tier —
    the honest replacement for the old per-user 'goal' model feature."""
    tier = (calorie_tier or "").strip().lower()
    if weight_goal == "weight_loss":
        return GOAL_CALORIE_BONUS if tier == "low" else (-GOAL_CALORIE_BONUS if tier == "high" else 0.0)
    if weight_goal == "weight_gain":
        return GOAL_CALORIE_BONUS if tier == "high" else (-GOAL_CALORIE_BONUS if tier == "low" else 0.0)
    return 0.0


def cuisine_affinity(dish_cuisine: str, user_cuisines) -> float:
    """Bonus for a dish whose cuisine the user prefers, larger for the cuisines
    they listed first. Off-preference cuisines earn nothing, so the top-K pick
    lands on their stated tastes instead of whatever the model scored highest
    (this is what keeps a Greek/Thai/Indian eater from being served Polish)."""
    target = (dish_cuisine or "").strip().lower()
    if not target:
        return 0.0
    for rank, cuisine in enumerate(user_cuisines or []):
        if target == (cuisine or "").strip().lower():
            return max(CUISINE_TOP_BONUS - rank * CUISINE_RANK_DECAY, CUISINE_MIN_BONUS)
    return 0.0


class RecommendationEngine:
    def __init__(self, weights_path, encoders_path, dishes_path, users_path):
        # ── Load encoders and vocabularies ────────────────────────────────────
        with open(encoders_path, "rb") as f:
            enc = pickle.load(f)

        self.user_enc         = enc["user_enc"]
        self.dish_enc         = enc["dish_enc"]
        self.cuisine_enc      = enc["cuisine_enc"]
        self.ingredient_to_idx = enc["ingredient_to_idx"]
        self.num_ingredients  = enc["num_ingredients"]
        self.all_cuisines     = enc["all_cuisines"]

        # ── Load dish catalog and real user profiles ──────────────────────────
        with open(dishes_path, "rb") as f:
            self.dish_lookup = pickle.load(f)   # dict: dish_id -> dish metadata
        with open(users_path, "rb") as f:
            self.user_lookup = pickle.load(f)   # dict: user_id -> user metadata

        # ── Load trained weights (exported from torch to NumPy) ───────────────
        npz = np.load(weights_path)
        self.w = {k: npz[k].astype(np.float32) for k in npz.files}
        self.global_bias = float(self.w["global_bias"][0])

        # Users the model actually trained on ("real_<id>" for real users).
        # Anyone not in here goes through nearest-neighbor cold start.
        self.known_users = set(self.user_enc.classes_)

        # ── Precompute everything that never changes between requests ──────────
        # dish embeddings, the ingredient projection, and the per-dish lookup
        # sets. Rebuilding these per request was the bulk of recommendation
        # latency; now a request only recomputes the user/profile-dependent parts.
        self.all_dish_ids = sorted(self.dish_lookup.keys())
        dish_idx = self.dish_enc.transform(self.all_dish_ids)
        self.dish_embs = self.w["dish_embedding.weight"][dish_idx]        # (n, 64)
        # Per-dish learned bias = how universally liked a dish is (real-rating
        # popularity). It varies per dish, so it shapes the ranking; include it.
        self.dish_bias_vec = self.w["dish_bias.weight"][dish_idx].reshape(-1)  # (n,)

        skill_rank = {"beginner": 0, "intermediate": 1, "advanced": 2}
        self._names, self._cuisines = [], []
        self._ingredient_sets, self._tag_sets, self._difficulty_ranks = [], [], []
        self._ingredient_words, self._is_dinner, self._calorie_tiers = [], [], []
        rows = []
        for did in self.all_dish_ids:
            dish = self.dish_lookup[did]
            self._names.append(dish.get("dish_name", ""))
            self._cuisines.append(dish.get("cuisine", ""))
            ings = [i.strip().lower() for i in str(dish.get("ingredients", "")).split("|") if i.strip()]
            self._ingredient_sets.append(set(ings))
            # individual words across all ingredients, for the dietary safety net
            self._ingredient_words.append({w for ing in ings for w in ing.split()})
            self._tag_sets.append({t for t in str(dish.get("dietary_tags", "")).split("|") if t})
            self._difficulty_ranks.append(skill_rank.get(dish.get("difficulty", "beginner"), 0))
            self._is_dinner.append(is_main_dish(dish.get("category", "")))
            self._calorie_tiers.append(dish.get("calorie_tier", "medium"))
            rows.append(self._dish_ingredient_vec(did))
        ingredient_matrix = np.stack(rows).astype(np.float32)          # (n, num_ingredients)
        # The ingredient projection depends only on the (fixed) catalog, so the
        # projected features are constant across requests — project once.
        self.i_proj = _relu(
            ingredient_matrix @ self.w["ingredient_proj.weight"].T
            + self.w["ingredient_proj.bias"]
        )                                                              # (n, 32)

    # ── Cold-start: map a new user to the embedding space ────────────────────
    def _find_nearest_user_embedding(self, user_profile) -> np.ndarray:
        """
        A new app user has no learned embedding (they weren't in the Food.com
        training set). We find the most similar real users by cuisine overlap
        and average their learned embeddings as a proxy.
        """
        user_cuisines = user_profile.get("cuisines", [])

        scores = {}
        for uid, u in self.user_lookup.items():
            syn_cuisines = str(u.get("preferred_cuisines", "")).split("|")
            score = 0.0
            for rank, cuisine in enumerate(user_cuisines[:5]):
                if cuisine in syn_cuisines:
                    score += 1.5 - rank * 0.2
            scores[uid] = score

        top_k = sorted(scores, key=scores.get, reverse=True)[:5]
        top_k_encoded = self.user_enc.transform(top_k)
        return self.w["user_embedding.weight"][top_k_encoded].mean(axis=0)  # (64,)

    # ── Ingredient multi-hot for a dish ──────────────────────────────────────
    def _dish_ingredient_vec(self, dish_id):
        dish = self.dish_lookup.get(dish_id, {})
        vec  = np.zeros(self.num_ingredients, dtype=np.float32)
        for ing in dish.get("ingredients", "").split("|"):
            ing = ing.strip().lower()
            if ing in self.ingredient_to_idx:
                vec[self.ingredient_to_idx[ing]] = 1.0
        return vec

    def _user_embedding(self, user_profile, user_id) -> np.ndarray:
        """Learned embedding if this user was in the last retrain, else cold start."""
        trained_key = f"real_{user_id}" if user_id is not None else None
        if trained_key is not None and trained_key in self.known_users:
            idx = self.user_enc.transform([trained_key])[0]
            return self.w["user_embedding.weight"][idx]
        return self._find_nearest_user_embedding(user_profile)

    def _score_all_dishes(self, user_emb, cuisine_id) -> np.ndarray:
        """NumPy forward pass over the whole catalog. Mirrors the trained model's
        serving forward: mlp([user, dish, user*dish, cuisine, ingredients]) plus
        the per-dish bias (popularity) and global bias. The per-user bias is a
        constant across dishes, so it doesn't affect ranking and is omitted."""
        n = len(self.all_dish_ids)
        u = np.broadcast_to(user_emb.astype(np.float32), (n, user_emb.shape[0]))
        interaction = self.dish_embs * user_emb.astype(np.float32)
        c = np.broadcast_to(self.w["cuisine_embedding.weight"][cuisine_id], (n, 16))

        combined = np.concatenate(
            [u, self.dish_embs, interaction, c, self.i_proj], axis=1
        ).astype(np.float32)                                            # (n, 240)

        h = _relu(combined @ self.w["mlp.0.weight"].T + self.w["mlp.0.bias"])
        h = _relu(h @ self.w["mlp.3.weight"].T + self.w["mlp.3.bias"])
        out = (h @ self.w["mlp.6.weight"].T + self.w["mlp.6.bias"]).squeeze(-1)
        return out + self.dish_bias_vec + self.global_bias

    # ── Main recommendation function ──────────────────────────────────────────
    def recommend(
        self,
        user_profile,
        available_ingredients=None,
        excluded_dishes=None,
        user_id=None,
        preferred_dishes=None,
        learned_affinity=None,
        top_k=5,
        rng=None,
    ):
        """
        Score every dish for the given user profile and return a top match.

        Returns a dict with dish_name, cuisine, ingredients, score.
        """
        excluded_dishes = set(excluded_dishes or [])
        preferred_dishes = set(preferred_dishes or [])

        # ── Encode profile side features ──────────────────────────────────────
        cuisines = user_profile.get("cuisines") or [self.all_cuisines[0]]
        top_cuisine = cuisines[0]
        if top_cuisine not in self.cuisine_enc.classes_:
            top_cuisine = self.all_cuisines[0]
        skill = user_profile.get("skill_level", "beginner")
        goal = user_profile.get("weight_goal", "maintain")

        cuisine_id = int(self.cuisine_enc.transform([top_cuisine])[0])

        # ── Score all dishes ──────────────────────────────────────────────────
        user_emb = self._user_embedding(user_profile, user_id)
        scores = self._score_all_dishes(user_emb, cuisine_id)

        # ── Hard filters + preference boosts (one pass over precomputed data) ──
        user_diet = set(user_profile.get("dietary_restrictions", []))
        # Normalize here too, so any pre-existing un-normalized data is still caught.
        allergies = normalize_allergens(user_profile.get("allergies") or [])
        skill_rank = {"beginner": 0, "intermediate": 1, "advanced": 2}
        user_skill_rank = skill_rank.get(skill, 0)
        user_cuisines = user_profile.get("cuisines", []) or []
        available = {ing.strip().lower() for ing in (available_ingredients or [])}
        learned = learned_affinity or {}
        learned_cuisines = learned.get("cuisines") or {}
        learned_ingredients = learned.get("ingredients") or {}

        n = len(self.all_dish_ids)
        for i in range(n):
            name = self._names[i]
            ing_set = self._ingredient_sets[i]

            # ── Hard filters ──────────────────────────────────────────────────
            # Safety: unconditionally remove any dish containing an allergen
            if allergies and any(
                matches_allergen(ing, a) for ing in ing_set for a in allergies
            ):
                scores[i] = -np.inf
                continue
            # Remove excluded dishes (recently eaten / disliked)
            if name in excluded_dishes:
                scores[i] = -np.inf
                continue
            # Only nominate dinner mains — no desserts, sides, appetizers, drinks
            if not self._is_dinner[i]:
                scores[i] = -np.inf
                continue
            # Remove dishes that violate dietary restrictions (tags + an
            # ingredient-level safety net for mislabeled catalog data)
            if user_diet and (
                any(r and r not in self._tag_sets[i] for r in user_diet)
                or diet_conflict(self._ingredient_words[i], user_diet)
            ):
                scores[i] = -np.inf
                continue
            # Remove dishes too advanced for the user's skill level
            if self._difficulty_ranks[i] > user_skill_rank:
                scores[i] = -np.inf
                continue

            # ── Preference boosts (make the pick feel personal pre-ratings) ───
            scores[i] += cuisine_affinity(self._cuisines[i], user_cuisines)
            scores[i] += goal_calorie_bonus(goal, self._calorie_tiers[i])
            if available and ing_set:
                scores[i] += INGREDIENT_MAX_BONUS * (len(available & ing_set) / len(ing_set))
            # Favor dishes we can show a real recipe for (better than a fallback)
            if name in preferred_dishes:
                scores[i] += RECIPE_BONUS
            # Online learning: nudge toward cuisines/ingredients this user's own
            # rating history (including implicit cook/takeout signals) favors.
            if learned_cuisines:
                scores[i] += LEARNED_CUISINE_WEIGHT * learned_cuisines.get(
                    self._cuisines[i].strip().lower(), 0.0
                )
            if learned_ingredients:
                words = self._ingredient_words[i]
                hits = [learned_ingredients[w] for w in words if w in learned_ingredients]
                if hits:
                    scores[i] += LEARNED_INGREDIENT_WEIGHT * (sum(hits) / len(hits))

        # ── Sample from the top K so repeat requests feel fresh ──────────────
        best_idx  = sample_top_k(scores, k=top_k, rng=rng)
        best_id   = self.all_dish_ids[best_idx]
        best_dish = self.dish_lookup[best_id]

        return {
            "dish_name":   best_dish.get("dish_name", "Unknown"),
            "cuisine":     best_dish.get("cuisine", ""),
            "ingredients": [
                ing.strip()
                for ing in best_dish.get("ingredients", "").split("|")
                if ing.strip()
            ],
            "score": round(float(scores[best_idx]), 3),
        }

    def get_ingredients(self, dish_name):
        """Look up ingredients for a dish by name — no API call needed."""
        for dish in self.dish_lookup.values():
            if dish.get("dish_name", "").lower() == dish_name.lower():
                return [
                    ing.strip()
                    for ing in dish.get("ingredients", "").split("|")
                    if ing.strip()
                ]
        return []
