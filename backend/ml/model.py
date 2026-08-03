import torch
import torch.nn as nn
import torch.nn.functional as F


class DishRecommender(nn.Module):
    """Hybrid collaborative-filtering + content model.

    Learns user and dish embeddings from real ratings, plus a bias per user and
    per dish (a dish's bias captures how universally liked it is). Content comes
    from the user's top cuisine and the dish's ingredient multi-hot. Skill,
    budget, and health goal are intentionally NOT user features here — they're
    handled at serving time as dish-property filters/boosts (recipe step count,
    restaurant price, calorie tier), so the model only trains on real signal.
    """

    def __init__(
        self,
        num_users,
        num_dishes,
        num_cuisines,
        num_ingredients,
        embedding_dim=64,
    ):
        super().__init__()

        # Collaborative filtering core
        self.user_embedding = nn.Embedding(num_users, embedding_dim)
        self.dish_embedding = nn.Embedding(num_dishes, embedding_dim)
        # Bias terms: "this user rates high", "this dish is widely liked"
        self.user_bias = nn.Embedding(num_users, 1)
        self.dish_bias = nn.Embedding(num_dishes, 1)

        # Content features
        self.cuisine_embedding = nn.Embedding(num_cuisines, 16)
        self.ingredient_proj = nn.Linear(num_ingredients, 32)

        # MLP tower: user(64) + dish(64) + interaction(64) + cuisine(16) + ingredients(32)
        mlp_input_dim = embedding_dim * 3 + 16 + 32
        self.mlp = nn.Sequential(
            nn.Linear(mlp_input_dim, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 1),
        )

        self.global_bias = nn.Parameter(torch.zeros(1))

    def forward(self, user_ids, dish_ids, cuisine_ids, ingredient_multihot):
        u_emb = self.user_embedding(user_ids)
        d_emb = self.dish_embedding(dish_ids)
        interaction = u_emb * d_emb  # matrix-factorization interaction

        c_emb = self.cuisine_embedding(cuisine_ids)
        i_proj = F.relu(self.ingredient_proj(ingredient_multihot.float()))

        combined = torch.cat([u_emb, d_emb, interaction, c_emb, i_proj], dim=1)
        out = self.mlp(combined)
        out = out + self.user_bias(user_ids) + self.dish_bias(dish_ids) + self.global_bias
        return out.squeeze()
