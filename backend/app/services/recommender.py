"""Boundary between the web layer and the PyTorch recommendation engine.

The engine loads lazily on first use (fast app start, no torch for tests or
CLI commands) from the newest checkpoint: if ``checkpoints/latest`` names a
versioned retrain directory, that wins; otherwise the base checkpoints ship
with the repo. The pointer is re-checked on every call, so a retrain done in
another process is hot-swapped in without a server restart.

Tests inject a fake by setting ``_engine`` directly (``_engine_dir`` stays
None, which pins the injected engine).
"""
import os

_engine = None
_engine_dir: str | None = None

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHECKPOINTS = os.path.join(BACKEND_ROOT, "ml", "checkpoints")
LATEST_POINTER = os.path.join(CHECKPOINTS, "latest")


def resolve_checkpoint_dir() -> str:
    if os.path.exists(LATEST_POINTER):
        with open(LATEST_POINTER) as f:
            version = f.read().strip()
        candidate = os.path.join(CHECKPOINTS, version)
        if version and os.path.isdir(candidate):
            return candidate
    return CHECKPOINTS


def get_engine():
    global _engine, _engine_dir

    if _engine is not None and _engine_dir is None:
        return _engine  # injected by tests

    target = resolve_checkpoint_dir()
    if _engine is None or _engine_dir != target:
        from ml.recommender import RecommendationEngine

        _engine = RecommendationEngine(
            model_path=os.path.join(target, "model.pt"),
            encoders_path=os.path.join(target, "encoders.pkl"),
            dishes_path=os.path.join(target, "dishes.pkl"),
            users_path=os.path.join(target, "users.pkl"),
        )
        _engine_dir = target
    return _engine
