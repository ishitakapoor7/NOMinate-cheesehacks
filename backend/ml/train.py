"""Model training.

Callable as a library (``train_model``) so the backend can retrain on real +
synthetic ratings, or as a script for the original synthetic-only workflow:

    cd backend/ml && python train.py

User ids are treated as strings so synthetic ids ("0".."499") and real ids
("real_<db id>") can share one embedding table without colliding.
"""
import os
import pickle

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.preprocessing import LabelEncoder
from torch.utils.data import DataLoader, Dataset

try:
    from ml.model import DishRecommender
except ImportError:
    from model import DishRecommender

SKILLS = ["beginner", "intermediate", "advanced"]
GOALS = ["weight_loss", "maintain", "weight_gain"]
BUDGETS = ["<$50", "$50-$100", "$100-$200", "$200+"]


class RatingsDataset(Dataset):
    def __init__(self, ratings_df, encode_sample):
        self.ratings = ratings_df.reset_index(drop=True)
        self.encode_sample = encode_sample

    def __len__(self):
        return len(self.ratings)

    def __getitem__(self, idx):
        row = self.ratings.iloc[idx]
        return self.encode_sample(str(row["user_id"]), int(row["dish_id"]), float(row["rating"]))


def train_model(
    ratings: pd.DataFrame,
    dishes: pd.DataFrame,
    users: pd.DataFrame,
    out_dir: str,
    embedding_dim: int = 64,
    epochs: int = 50,
    batch_size: int = 512,
    lr: float = 1e-3,
    patience: int = 5,
    seed: int = 42,
    log=print,
) -> dict:
    """Train the recommender and write model.pt / encoders.pkl / dishes.pkl /
    users.pkl into ``out_dir``. Returns training metrics.

    Expected columns:
      ratings: user_id, dish_id, rating
      dishes:  dish_id, dish_name, cuisine, category, dietary_tags, difficulty,
               calorie_tier, cost_tier, ingredients
      users:   user_id, preferred_cuisines, skill, health_goal, budget,
               dietary_restrictions
    """
    os.makedirs(out_dir, exist_ok=True)
    torch.manual_seed(seed)

    ratings = ratings.copy()
    dishes = dishes.copy()
    users = users.copy()

    ratings["user_id"] = ratings["user_id"].astype(str)
    users["user_id"] = users["user_id"].astype(str)
    dishes["dietary_tags"] = dishes["dietary_tags"].fillna("")
    dishes["ingredients"] = dishes["ingredients"].fillna("")
    users["dietary_restrictions"] = users["dietary_restrictions"].fillna("")

    # ── Vocabularies ─────────────────────────────────────────────────────────
    user_enc = LabelEncoder().fit(users["user_id"])
    dish_enc = LabelEncoder().fit(dishes["dish_id"])
    skill_enc = LabelEncoder().fit(SKILLS)
    goal_enc = LabelEncoder().fit(GOALS)
    budget_enc = LabelEncoder().fit(BUDGETS)

    all_cuisines = sorted(dishes["cuisine"].dropna().unique().tolist())
    cuisine_enc = LabelEncoder().fit(all_cuisines)

    all_ingredients = set()
    for ing_str in dishes["ingredients"]:
        for ing in ing_str.split("|"):
            ing = ing.strip()
            if ing:
                all_ingredients.add(ing.lower())
    all_ingredients = sorted(all_ingredients)
    ingredient_to_idx = {ing: i for i, ing in enumerate(all_ingredients)}
    num_ingredients = len(all_ingredients)

    log(
        f"Vocab sizes — users: {len(user_enc.classes_)}, dishes: {len(dish_enc.classes_)}, "
        f"cuisines: {len(cuisine_enc.classes_)}, ingredients: {num_ingredients}"
    )

    # ── Lookup tables ────────────────────────────────────────────────────────
    user_lookup = users.set_index("user_id").to_dict("index")
    dish_lookup = dishes.set_index("dish_id").to_dict("index")

    # Pre-encode per-id features once; per-sample LabelEncoder.transform calls
    # are far too slow inside __getitem__.
    cuisine_by_user = {}
    skill_by_user = {}
    goal_by_user = {}
    budget_by_user = {}
    for uid, user in user_lookup.items():
        cuisines = [c for c in str(user.get("preferred_cuisines", "")).split("|") if c]
        top = cuisines[0] if cuisines and cuisines[0] in cuisine_enc.classes_ else all_cuisines[0]
        cuisine_by_user[uid] = int(cuisine_enc.transform([top])[0])
        skill = user.get("skill") if user.get("skill") in SKILLS else "beginner"
        goal = user.get("health_goal") if user.get("health_goal") in GOALS else "maintain"
        budget = user.get("budget") if user.get("budget") in BUDGETS else "<$50"
        skill_by_user[uid] = int(skill_enc.transform([skill])[0])
        goal_by_user[uid] = int(goal_enc.transform([goal])[0])
        budget_by_user[uid] = int(budget_enc.transform([budget])[0])

    user_idx = {uid: i for i, uid in enumerate(user_enc.classes_)}
    dish_idx = {did: i for i, did in enumerate(dish_enc.classes_)}

    def dish_ingredient_multihot(dish_id):
        vec = np.zeros(num_ingredients, dtype=np.float32)
        for ing in dish_lookup.get(dish_id, {}).get("ingredients", "").split("|"):
            ing = ing.strip().lower()
            if ing in ingredient_to_idx:
                vec[ingredient_to_idx[ing]] = 1.0
        return vec

    ingredient_vecs = {did: dish_ingredient_multihot(did) for did in dish_lookup}

    def encode_sample(user_id, dish_id, rating):
        return {
            "user_id": torch.tensor(user_idx[user_id], dtype=torch.long),
            "dish_id": torch.tensor(dish_idx[dish_id], dtype=torch.long),
            "cuisine_id": torch.tensor(cuisine_by_user[user_id], dtype=torch.long),
            "skill_id": torch.tensor(skill_by_user[user_id], dtype=torch.long),
            "goal_id": torch.tensor(goal_by_user[user_id], dtype=torch.long),
            "budget_id": torch.tensor(budget_by_user[user_id], dtype=torch.long),
            "ingredients": torch.tensor(ingredient_vecs[dish_id], dtype=torch.float),
            "rating": torch.tensor(rating, dtype=torch.float),
        }

    # ── Train / val split ────────────────────────────────────────────────────
    ratings = ratings.sample(frac=1, random_state=seed).reset_index(drop=True)
    split = int(0.8 * len(ratings))
    train_df, val_df = ratings.iloc[:split], ratings.iloc[split:]

    train_loader = DataLoader(
        RatingsDataset(train_df, encode_sample), batch_size=batch_size, shuffle=True
    )
    val_loader = DataLoader(
        RatingsDataset(val_df, encode_sample), batch_size=batch_size, shuffle=False
    )
    log(f"Train samples: {len(train_df)}, Val samples: {len(val_df)}")

    # ── Model, loss, optimizer ───────────────────────────────────────────────
    model = DishRecommender(
        num_users=len(user_enc.classes_),
        num_dishes=len(dish_enc.classes_),
        num_cuisines=len(cuisine_enc.classes_),
        num_skills=len(skill_enc.classes_),
        num_goals=len(goal_enc.classes_),
        num_budgets=len(budget_enc.classes_),
        num_ingredients=num_ingredients,
        embedding_dim=embedding_dim,
    )
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-5)

    def run_epoch(loader, train=True):
        model.train() if train else model.eval()
        total_loss = 0.0
        with torch.set_grad_enabled(train):
            for batch in loader:
                preds = model(
                    batch["user_id"],
                    batch["dish_id"],
                    batch["cuisine_id"],
                    batch["skill_id"],
                    batch["goal_id"],
                    batch["budget_id"],
                    batch["ingredients"],
                )
                loss = criterion(preds, batch["rating"])
                if train:
                    optimizer.zero_grad()
                    loss.backward()
                    optimizer.step()
                total_loss += loss.item() * len(batch["rating"])
        return (total_loss / len(loader.dataset)) ** 0.5

    best_val_rmse = float("inf")
    no_improve = 0
    epochs_run = 0
    model_path = os.path.join(out_dir, "model.pt")

    for epoch in range(1, epochs + 1):
        epochs_run = epoch
        train_rmse = run_epoch(train_loader, train=True)
        val_rmse = run_epoch(val_loader, train=False)
        log(f"Epoch {epoch:02d} — train RMSE: {train_rmse:.4f}  val RMSE: {val_rmse:.4f}")

        if val_rmse < best_val_rmse:
            best_val_rmse = val_rmse
            no_improve = 0
            torch.save(model.state_dict(), model_path)
        else:
            no_improve += 1
            if no_improve >= patience:
                log(f"Early stopping at epoch {epoch}")
                break

    log(f"Best val RMSE: {best_val_rmse:.4f}")

    # ── Save encoders and lookups for the inference engine ──────────────────
    encoders = {
        "user_enc": user_enc,
        "dish_enc": dish_enc,
        "cuisine_enc": cuisine_enc,
        "skill_enc": skill_enc,
        "goal_enc": goal_enc,
        "budget_enc": budget_enc,
        "ingredient_to_idx": ingredient_to_idx,
        "num_ingredients": num_ingredients,
        "all_cuisines": all_cuisines,
    }
    with open(os.path.join(out_dir, "encoders.pkl"), "wb") as f:
        pickle.dump(encoders, f)
    with open(os.path.join(out_dir, "dishes.pkl"), "wb") as f:
        pickle.dump(dish_lookup, f)
    with open(os.path.join(out_dir, "users.pkl"), "wb") as f:
        pickle.dump(user_lookup, f)
    log(f"Saved model, encoders, and catalogs to {out_dir}/")

    return {"best_val_rmse": best_val_rmse, "epochs_run": epochs_run}


if __name__ == "__main__":
    train_model(
        ratings=pd.read_csv("data/ratings.csv"),
        dishes=pd.read_csv("data/dishes.csv"),
        users=pd.read_csv("data/users.csv"),
        out_dir="checkpoints",
    )
