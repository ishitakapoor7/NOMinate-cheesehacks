import pickle
import numpy as np
import torch
from model import DishRecommender


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

        # Pre-encode all dish IDs so we can score them all at once
        self.all_dish_ids = sorted(self.dish_lookup.keys())
        self.dish_id_tensor = torch.tensor(
            self.dish_enc.transform(self.all_dish_ids), dtype=torch.long
        )

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
    def recommend(self, user_profile, available_ingredients=None, excluded_dishes=None):
        """
        Score every dish for the given user profile and return the best match.

        Args:
            user_profile: dict with keys cuisines, skill_level, weight_goal,
                          budget, dietary_restrictions
            available_ingredients: list of ingredient strings the user has at home
            excluded_dishes: list of dish names to skip (recently eaten, disliked)

        Returns:
            dict with dish_name, cuisine, ingredients, score
        """
        excluded_dishes = set(excluded_dishes or [])

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

        # Build ingredient multi-hot for every dish
        ing_matrix = torch.tensor(
            np.stack([self._dish_ingredient_vec(did) for did in self.all_dish_ids]),
            dtype=torch.float,
        )

        # ── Get user embedding via cold-start ─────────────────────────────────
        user_emb = self._find_nearest_user_embedding(user_profile)  # (1, 64)
        user_emb_expanded = user_emb.expand(n, -1)                  # (n, 64)

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

        # ── Hard filters ─────────────────────────────────────────────────────
        user_diet = set(user_profile.get("dietary_restrictions", []))
        skill_rank = {"beginner": 0, "intermediate": 1, "advanced": 2}
        user_skill_rank = skill_rank.get(skill, 0)

        for i, dish_id in enumerate(self.all_dish_ids):
            dish = self.dish_lookup[dish_id]
            dish_name = dish.get("dish_name", "")

            # Remove excluded dishes (recently eaten / disliked)
            if dish_name in excluded_dishes:
                scores[i] = -np.inf
                continue

            # Remove dishes that violate dietary restrictions
            dish_tags = set(dish.get("dietary_tags", "").split("|")) - {""}
            for restriction in user_diet:
                if restriction and restriction not in dish_tags:
                    scores[i] = -np.inf
                    break

            # Remove dishes too advanced for the user's skill level
            dish_difficulty = dish.get("difficulty", "beginner")
            if skill_rank.get(dish_difficulty, 0) > user_skill_rank:
                scores[i] = -np.inf

        # ── Ingredient availability boost ─────────────────────────────────────
        # If the user told us what ingredients they have, boost dishes
        # where they already have a high fraction of the required ingredients.
        if available_ingredients:
            available = {ing.strip().lower() for ing in available_ingredients}
            for i, dish_id in enumerate(self.all_dish_ids):
                if scores[i] == -np.inf:
                    continue
                dish = self.dish_lookup[dish_id]
                dish_ings = [
                    ing.strip().lower()
                    for ing in dish.get("ingredients", "").split("|")
                    if ing.strip()
                ]
                if dish_ings:
                    fraction = len(available & set(dish_ings)) / len(dish_ings)
                    # Boost score by up to 0.5 points if they have all ingredients
                    scores[i] += 0.5 * fraction

        # ── Return top dish ───────────────────────────────────────────────────
        best_idx  = int(np.argmax(scores))
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
