import os
import pickle
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import LabelEncoder
from model import DishRecommender


# ── 1. Load data ─────────────────────────────────────────────────────────────

ratings = pd.read_csv("data/ratings.csv")
dishes  = pd.read_csv("data/dishes.csv")
users   = pd.read_csv("data/users.csv")

# Fill any missing values so nothing crashes downstream
dishes["dietary_tags"] = dishes["dietary_tags"].fillna("")
dishes["ingredients"]  = dishes["ingredients"].fillna("")
users["dietary_restrictions"] = users["dietary_restrictions"].fillna("")


# ── 2. Build vocabularies ─────────────────────────────────────────────────────
# LabelEncoder turns string categories into integer IDs the embedding layers can use.
# e.g. "Italian" → 3, "Thai" → 14

user_enc    = LabelEncoder().fit(users["user_id"])
dish_enc    = LabelEncoder().fit(dishes["dish_id"])
skill_enc   = LabelEncoder().fit(["beginner", "intermediate", "advanced"])
goal_enc    = LabelEncoder().fit(["weight_loss", "maintain", "weight_gain"])
budget_enc  = LabelEncoder().fit(["<$50", "$50-$100", "$100-$200", "$200+"])

# Build a cuisine vocabulary from all cuisines that appear in the dish catalog
all_cuisines = sorted(dishes["cuisine"].dropna().unique().tolist())
cuisine_enc  = LabelEncoder().fit(all_cuisines)

# Build an ingredient vocabulary from every ingredient across all dishes
all_ingredients = set()
for ing_str in dishes["ingredients"]:
    for ing in ing_str.split("|"):
        ing = ing.strip()
        if ing:
            all_ingredients.add(ing.lower())
all_ingredients = sorted(all_ingredients)
ingredient_to_idx = {ing: i for i, ing in enumerate(all_ingredients)}
num_ingredients = len(all_ingredients)

print(f"Vocab sizes — users: {len(user_enc.classes_)}, dishes: {len(dish_enc.classes_)}, "
      f"cuisines: {len(cuisine_enc.classes_)}, ingredients: {num_ingredients}")


# ── 3. Build lookup tables ────────────────────────────────────────────────────
# Index users and dishes by their ID so we can quickly fetch profile features
# when building each training sample.

user_lookup = users.set_index("user_id").to_dict("index")
dish_lookup = dishes.set_index("dish_id").to_dict("index")


def get_ingredient_multihot(dish_id):
    """Return a binary vector of length num_ingredients for a given dish."""
    vec = np.zeros(num_ingredients, dtype=np.float32)
    dish = dish_lookup.get(dish_id, {})
    for ing in dish.get("ingredients", "").split("|"):
        ing = ing.strip().lower()
        if ing in ingredient_to_idx:
            vec[ingredient_to_idx[ing]] = 1.0
    return vec


def get_user_top_cuisine(user_id):
    """Return the user's top-ranked cuisine (first in their preference list)."""
    user = user_lookup.get(user_id, {})
    cuisines = user.get("preferred_cuisines", "").split("|")
    return cuisines[0] if cuisines else all_cuisines[0]


# ── 4. Dataset ────────────────────────────────────────────────────────────────
# PyTorch's Dataset class defines how to fetch a single training sample.
# DataLoader will call __getitem__ repeatedly and batch the results.

class RatingsDataset(Dataset):
    def __init__(self, ratings_df):
        self.ratings = ratings_df.reset_index(drop=True)

    def __len__(self):
        return len(self.ratings)

    def __getitem__(self, idx):
        row = self.ratings.iloc[idx]
        user_id = int(row["user_id"])
        dish_id = int(row["dish_id"])
        rating  = float(row["rating"])

        user = user_lookup.get(user_id, {})
        dish = dish_lookup.get(dish_id, {})

        # Encode categorical features as integer IDs
        top_cuisine = get_user_top_cuisine(user_id)
        cuisine_id  = int(cuisine_enc.transform([top_cuisine])[0])
        skill_id    = int(skill_enc.transform([user.get("skill", "beginner")])[0])
        goal_id     = int(goal_enc.transform([user.get("health_goal", "maintain")])[0])
        budget_id   = int(budget_enc.transform([user.get("budget", "<$50")])[0])

        ingredient_vec = get_ingredient_multihot(dish_id)

        return {
            "user_id":    torch.tensor(user_enc.transform([user_id])[0], dtype=torch.long),
            "dish_id":    torch.tensor(dish_enc.transform([dish_id])[0], dtype=torch.long),
            "cuisine_id": torch.tensor(cuisine_id, dtype=torch.long),
            "skill_id":   torch.tensor(skill_id,   dtype=torch.long),
            "goal_id":    torch.tensor(goal_id,    dtype=torch.long),
            "budget_id":  torch.tensor(budget_id,  dtype=torch.long),
            "ingredients":torch.tensor(ingredient_vec, dtype=torch.float),
            "rating":     torch.tensor(rating, dtype=torch.float),
        }


# ── 5. Train / val split ──────────────────────────────────────────────────────
# Shuffle and take 80% for training, 20% for validation.
# The model never sees val during training — it's used to check for overfitting.

ratings = ratings.sample(frac=1, random_state=42).reset_index(drop=True)
split   = int(0.8 * len(ratings))
train_df = ratings.iloc[:split]
val_df   = ratings.iloc[split:]

train_loader = DataLoader(RatingsDataset(train_df), batch_size=512, shuffle=True)
val_loader   = DataLoader(RatingsDataset(val_df),   batch_size=512, shuffle=False)

print(f"Train samples: {len(train_df)}, Val samples: {len(val_df)}")


# ── 6. Model, loss, optimizer ─────────────────────────────────────────────────

model = DishRecommender(
    num_users       = len(user_enc.classes_),
    num_dishes      = len(dish_enc.classes_),
    num_cuisines    = len(cuisine_enc.classes_),
    num_skills      = len(skill_enc.classes_),
    num_goals       = len(goal_enc.classes_),
    num_budgets     = len(budget_enc.classes_),
    num_ingredients = num_ingredients,
    embedding_dim   = 64,
)

# MSE loss: penalises the squared difference between predicted and actual rating.
# RMSE (root MSE) is reported because it's in the same units as the ratings (1-5).
criterion = nn.MSELoss()
optimizer = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-5)


# ── 7. Training loop ──────────────────────────────────────────────────────────

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
                loss.backward()        # compute gradients
                optimizer.step()       # update weights

            total_loss += loss.item() * len(batch["rating"])

    rmse = (total_loss / len(loader.dataset)) ** 0.5
    return rmse


best_val_rmse = float("inf")
patience      = 5   # stop early if val RMSE doesn't improve for 5 epochs
no_improve    = 0

for epoch in range(1, 51):
    train_rmse = run_epoch(train_loader, train=True)
    val_rmse   = run_epoch(val_loader,   train=False)

    print(f"Epoch {epoch:02d} — train RMSE: {train_rmse:.4f}  val RMSE: {val_rmse:.4f}")

    # Save the best model seen so far
    if val_rmse < best_val_rmse:
        best_val_rmse = val_rmse
        no_improve    = 0
        torch.save(model.state_dict(), "checkpoints/model.pt")
    else:
        no_improve += 1
        if no_improve >= patience:
            print(f"Early stopping at epoch {epoch}")
            break

print(f"\nBest val RMSE: {best_val_rmse:.4f}")


# ── 8. Save encoders and dish catalog ────────────────────────────────────────
# The inference engine needs these to encode a real user's profile
# the same way training data was encoded.

encoders = {
    "user_enc":         user_enc,
    "dish_enc":         dish_enc,
    "cuisine_enc":      cuisine_enc,
    "skill_enc":        skill_enc,
    "goal_enc":         goal_enc,
    "budget_enc":       budget_enc,
    "ingredient_to_idx":ingredient_to_idx,
    "num_ingredients":  num_ingredients,
    "all_cuisines":     all_cuisines,
}

with open("checkpoints/encoders.pkl", "wb") as f:
    pickle.dump(encoders, f)

with open("checkpoints/dishes.pkl", "wb") as f:
    pickle.dump(dish_lookup, f)

with open("checkpoints/users.pkl", "wb") as f:
    pickle.dump(user_lookup, f)

print("Saved model, encoders, and dish catalog to checkpoints/")
