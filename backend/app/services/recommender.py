"""Boundary between the web layer and the PyTorch recommendation engine.

The engine is loaded lazily on first use (so the app starts fast, tests don't
need torch checkpoints, and CLI commands like `flask db` never touch the ML
stack). Tests replace ``_engine`` with a fake.
"""
import os

_engine = None

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHECKPOINTS = os.path.join(BACKEND_ROOT, "ml", "checkpoints")


def get_engine():
    global _engine
    if _engine is None:
        from ml.recommender import RecommendationEngine

        _engine = RecommendationEngine(
            model_path=os.path.join(CHECKPOINTS, "model.pt"),
            encoders_path=os.path.join(CHECKPOINTS, "encoders.pkl"),
            dishes_path=os.path.join(CHECKPOINTS, "dishes.pkl"),
            users_path=os.path.join(CHECKPOINTS, "users.pkl"),
        )
    return _engine
