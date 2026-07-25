import pickle
import numpy as np
import torch

try:
    from ml.model import DishRecommender  # imported as a package (backend app)
except ImportError:
    from model import DishRecommender  # run as a script from inside ml/ (train.py)


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
    def __init__(self, model_path, encoders_path, dishes_path, users_path):
        # ── Load encoders and vocabularies ────────────────────────────────────
        with open(encoders_path, "rb") as f:
            enc = pickle.load(f)

        self.user_enc         = enc["user_enc"]
        self.dish_enc         = enc["dish_enc"]
        self.cuisine_enc      = enc["cuisine_enc"]
        self.skill_enc        = enc["skill_enc"]
        self.goal_enc         = enc["goal_enc"]
        self.budget_enc       = enc["budget_enc"]
        self.ingredient_to_idx = enc["ingredient_to_idx"]
        self.num_ingredients  = enc["num_ingredients"]
        self.all_cuisines     = enc["all_cuisines"]

        # ── Load dish catalog ─────────────────────────────────────────────────
        with open(dishes_path, "rb") as f:
            self.dish_lookup = pickle.load(f)   # dict: dish_id -> dish metadata

        # ── Load user profiles (synthetic) ────────────────────────────────────
        with open(users_path, "rb") as f:
            self.user_lookup = pickle.load(f)   # dict: user_id -> user metadata

        # ── Load trained model ────────────────────────────────────────────────
        self.model = DishRecommender(
            num_users       = len(self.user_enc.classes_),
            num_dishes      = len(self.dish_enc.classes_),
            num_cuisines    = len(self.cuisine_enc.classes_),
            num_skills      = len(self.skill_enc.classes_),
            num_goals       = len(self.goal_enc.classes_),
            num_budgets     = len(self.budget_enc.classes_),
            num_ingredients = self.num_ingredients,
            embedding_dim   = 64,
        )
        self.model.load_state_dict(torch.load(model_path, map_location="cpu"))
        self.model.eval()   # disable dropout for inference

        # A fractional-CPU host thrashes if torch spawns many threads for these
        # small ops; one thread is faster here.
        torch.set_num_threads(1)

        # Pre-encode all dish IDs so we can score them all at once
        self.all_dish_ids = sorted(self.dish_lookup.keys())
        self.dish_id_tensor = torch.tensor(
            self.dish_enc.transform(self.all_dish_ids), dtype=torch.long
        )

        # Precompute everything about the catalog that never changes between
        # requests: the ingredient multi-hot matrix and per-dish lookup sets.
        # Rebuilding these per request was the bulk of recommendation latency.
        skill_rank = {"beginner": 0, "intermediate": 1, "advanced": 2}
        self._names, self._cuisines = [], []
        self._ingredient_sets, self._tag_sets, self._difficulty_ranks = [], [], []
        rows = []
        for did in self.all_dish_ids:
            dish = self.dish_lookup[did]
            self._names.append(dish.get("dish_name", ""))
            self._cuisines.append(dish.get("cuisine", ""))
            ings = [i.strip().lower() for i in dish.get("ingredients", "").split("|") if i.strip()]
            self._ingredient_sets.append(set(ings))
            self._tag_sets.append({t for t in dish.get("dietary_tags", "").split("|") if t})
            self._difficulty_ranks.append(skill_rank.get(dish.get("difficulty", "beginner"), 0))
            rows.append(self._dish_ingredient_vec(did))
        self.ingredient_matrix = torch.tensor(np.stack(rows), dtype=torch.float)

        # Users the model actually trained on ("real_<id>" for real users).
        # Anyone not in here goes through nearest-neighbor cold start.
        self.known_users = set(self.user_enc.classes_)

    # ── Cold-start: map a new user to the embedding space ────────────────────
    def _find_nearest_user_embedding(self, user_profile):
        """
        A real user has no learned embedding because they weren't in the
        training set. We solve this by finding the K most similar synthetic
        users and averaging their embeddings.

        Similarity is scored by comparing profile attributes:
        - Cuisine overlap (weighted by rank)
        - Same skill level
        - Same health goal
        - Same budget
        - Dietary restriction overlap
        """
        user_cuisines  = user_profile.get("cuisines", [])
        user_skill     = user_profile.get("skill_level", "beginner")
        user_goal      = user_profile.get("weight_goal", "maintain")
        user_budget    = user_profile.get("budget", "<$50")
        user_diet      = set(user_profile.get("dietary_restrictions", []))

        scores = {}
        for uid, u in self.user_lookup.items():
            score = 0.0
            syn_cuisines = u.get("preferred_cuisines", "").split("|")

            # Cuisine overlap — higher bonus for matching higher-ranked preferences
            for rank, cuisine in enumerate(user_cuisines[:5]):
                if cuisine in syn_cuisines:
                    score += 1.5 - rank * 0.2

            if u.get("skill")        == user_skill:  score += 1.0
            if u.get("health_goal")  == user_goal:   score += 1.0
            if u.get("budget")       == user_budget:  score += 1.0

            syn_diet = set(u.get("dietary_restrictions", "").split("|")) - {""}
            if user_diet:
                overlap = len(user_diet & syn_diet) / len(user_diet)
                score += overlap * 1.0

            scores[uid] = score

        # Take the top 5 most similar synthetic users
        top_k = sorted(scores, key=scores.get, reverse=True)[:5]

        # Average their learned embeddings to create a proxy for the new user
        top_k_encoded = self.user_enc.transform(top_k)
        embeddings = self.model.user_embedding(
            torch.tensor(top_k_encoded, dtype=torch.long)
        )
        return embeddings.mean(dim=0, keepdim=True)  # shape: (1, embedding_dim)

    # ── Ingredient multi-hot for a dish ──────────────────────────────────────
    def _dish_ingredient_vec(self, dish_id):
        dish = self.dish_lookup.get(dish_id, {})
        vec  = np.zeros(self.num_ingredients, dtype=np.float32)
        for ing in dish.get("ingredients", "").split("|"):
            ing = ing.strip().lower()
            if ing in self.ingredient_to_idx:
                vec[self.ingredient_to_idx[ing]] = 1.0
        return vec

    # ── Main recommendation function ──────────────────────────────────────────
    def recommend(
        self,
        user_profile,
        available_ingredients=None,
        excluded_dishes=None,
        user_id=None,
        preferred_dishes=None,
        top_k=5,
        rng=None,
    ):
        """
        Score every dish for the given user profile and return a top match.

        Args:
            user_profile: dict with keys cuisines, skill_level, weight_goal,
                          budget, dietary_restrictions, allergies
            available_ingredients: list of ingredient strings the user has at home
            excluded_dishes: list of dish names to skip (recently eaten, disliked)
            user_id: real DB user id; if this user was in the last retrain they
                     get their learned embedding instead of cold start
            top_k: sample among this many top-scored dishes for variety
            rng: numpy Generator, injectable for deterministic tests

        Returns:
            dict with dish_name, cuisine, ingredients, score
        """
        excluded_dishes = set(excluded_dishes or [])
        preferred_dishes = set(preferred_dishes or [])

        # ── Encode profile side features ──────────────────────────────────────
        top_cuisine = user_profile.get("cuisines", [self.all_cuisines[0]])[0]
        # Fallback to first known cuisine if user's top pick isn't in the catalog
        if top_cuisine not in self.cuisine_enc.classes_:
            top_cuisine = self.all_cuisines[0]

        skill  = user_profile.get("skill_level", "beginner")
        goal   = user_profile.get("weight_goal", "maintain")
        budget = user_profile.get("budget", "<$50")

        n = len(self.all_dish_ids)
        cuisine_ids = torch.tensor([self.cuisine_enc.transform([top_cuisine])[0]] * n, dtype=torch.long)
        skill_ids   = torch.tensor([self.skill_enc.transform([skill])[0]]          * n, dtype=torch.long)
        goal_ids    = torch.tensor([self.goal_enc.transform([goal])[0]]            * n, dtype=torch.long)
        budget_ids  = torch.tensor([self.budget_enc.transform([budget])[0]]        * n, dtype=torch.long)

        # Ingredient multi-hot is precomputed once at load (see __init__).
        ing_matrix = self.ingredient_matrix

        # ── Get user embedding: learned if this user was in training, else
        # cold-start via nearest synthetic neighbors ──────────────────────────
        trained_key = f"real_{user_id}" if user_id is not None else None
        if trained_key is not None and trained_key in self.known_users:
            idx = self.user_enc.transform([trained_key])[0]
            user_emb = self.model.user_embedding(
                torch.tensor([idx], dtype=torch.long)
            )  # (1, 64)
        else:
            user_emb = self._find_nearest_user_embedding(user_profile)  # (1, 64)
        user_emb_expanded = user_emb.expand(n, -1)                      # (n, 64)

        # ── Score all dishes ──────────────────────────────────────────────────
        with torch.no_grad():
            dish_embs   = self.model.dish_embedding(self.dish_id_tensor)   # (n, 64)
            interaction = user_emb_expanded * dish_embs                    # (n, 64)

            c_emb = self.model.cuisine_embedding(cuisine_ids)
            s_emb = self.model.skill_embedding(skill_ids)
            g_emb = self.model.goal_embedding(goal_ids)
            b_emb = self.model.budget_embedding(budget_ids)
            i_proj = torch.relu(self.model.ingredient_proj(ing_matrix))

            combined = torch.cat(
                [user_emb_expanded, dish_embs, interaction,
                 c_emb, s_emb, g_emb, b_emb, i_proj], dim=1
            )
            scores = self.model.mlp(combined).squeeze()   # (n,)
            scores = scores + self.model.global_bias

        scores = scores.numpy()

        # ── Hard filters + preference boosts (one pass over precomputed data) ──
        user_diet = set(user_profile.get("dietary_restrictions", []))
        allergies = user_profile.get("allergies") or []
        if isinstance(allergies, str):
            allergies = [a.strip() for a in allergies.split(",") if a.strip()]
        skill_rank = {"beginner": 0, "intermediate": 1, "advanced": 2}
        user_skill_rank = skill_rank.get(skill, 0)
        user_cuisines = user_profile.get("cuisines", []) or []
        available = {ing.strip().lower() for ing in (available_ingredients or [])}

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
            # Remove dishes that violate dietary restrictions
            if user_diet and any(r and r not in self._tag_sets[i] for r in user_diet):
                scores[i] = -np.inf
                continue
            # Remove dishes too advanced for the user's skill level
            if self._difficulty_ranks[i] > user_skill_rank:
                scores[i] = -np.inf
                continue

            # ── Preference boosts (make the pick feel personal pre-ratings) ───
            scores[i] += cuisine_affinity(self._cuisines[i], user_cuisines)
            if available and ing_set:
                scores[i] += INGREDIENT_MAX_BONUS * (len(available & ing_set) / len(ing_set))
            # Favor dishes we can show a real recipe for (better than a fallback)
            if name in preferred_dishes:
                scores[i] += RECIPE_BONUS

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
