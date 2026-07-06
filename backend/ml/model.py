import torch
import torch.nn as nn
import torch.nn.functional as F


class DishRecommender(nn.Module):
    def __init__(
        self,
        num_users,
        num_dishes,
        num_cuisines,
        num_skills,
        num_goals,
        num_budgets,
        num_ingredients,
        embedding_dim=64,
    ):
        super().__init__()

        # --- Collaborative filtering core ---
        # Each user and dish gets a learned vector (embedding) of size embedding_dim.
        # The model learns these during training — similar users end up with similar vectors.
        self.user_embedding = nn.Embedding(num_users, embedding_dim)
        self.dish_embedding = nn.Embedding(num_dishes, embedding_dim)

        # Bias terms capture things like "this user rates everything high"
        # or "this dish is universally liked/disliked"
        self.user_bias = nn.Embedding(num_users, 1)
        self.dish_bias = nn.Embedding(num_dishes, 1)

        # --- Side feature embeddings ---
        # These encode the user's profile attributes as learned vectors.
        # Smaller than the main embeddings since they carry less information.
        self.cuisine_embedding = nn.Embedding(num_cuisines, 16)
        self.skill_embedding = nn.Embedding(num_skills, 8)
        self.goal_embedding = nn.Embedding(num_goals, 8)
        self.budget_embedding = nn.Embedding(num_budgets, 8)

        # Ingredient availability: user provides a list of ingredients they have.
        # We encode this as a multi-hot vector (1 where they have the ingredient, 0 otherwise)
        # and project it down to 32 dimensions.
        self.ingredient_proj = nn.Linear(num_ingredients, 32)

        # --- MLP tower ---
        # Combines the CF signal (user + dish embeddings) with profile side features.
        # Input size: user_emb(64) + dish_emb(64) + interaction(64)
        #           + cuisine(16) + skill(8) + goal(8) + budget(8) + ingredients(32) = 264
        mlp_input_dim = embedding_dim * 3 + 16 + 8 + 8 + 8 + 32
        self.mlp = nn.Sequential(
            nn.Linear(mlp_input_dim, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 1),
        )

        # A single learned global average rating offset
        self.global_bias = nn.Parameter(torch.zeros(1))

    def forward(
        self,
        user_ids,
        dish_ids,
        cuisine_ids,
        skill_ids,
        goal_ids,
        budget_ids,
        ingredient_multihot,
    ):
        # Look up embeddings for this batch of users and dishes
        u_emb = self.user_embedding(user_ids)
        d_emb = self.dish_embedding(dish_ids)

        # Element-wise product: the classic matrix factorization interaction.
        # Where u_emb and d_emb align strongly, the product is large — meaning
        # the user and dish are a good match in the latent space.
        interaction = u_emb * d_emb

        # Look up profile side feature embeddings
        c_emb = self.cuisine_embedding(cuisine_ids)
        s_emb = self.skill_embedding(skill_ids)
        g_emb = self.goal_embedding(goal_ids)
        b_emb = self.budget_embedding(budget_ids)

        # Project ingredient multi-hot vector to dense representation
        i_proj = F.relu(self.ingredient_proj(ingredient_multihot.float()))

        # Concatenate everything and pass through the MLP
        combined = torch.cat(
            [u_emb, d_emb, interaction, c_emb, s_emb, g_emb, b_emb, i_proj], dim=1
        )
        out = self.mlp(combined)

        # Add bias terms and global offset
        out = out + self.user_bias(user_ids) + self.dish_bias(dish_ids) + self.global_bias

        return out.squeeze()
