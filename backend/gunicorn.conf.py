"""Gunicorn config for the NOMinate API.

One worker keeps memory low (each worker loads its own PyTorch model), and the
long timeout covers cold starts. The worker warms the recommender at boot so no
request has to wait for the model to load.
"""
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"
workers = 1
timeout = 120


def post_worker_init(worker):
    try:
        from app.services.recommender import get_engine

        get_engine()
        worker.log.info("Recommender engine warmed at worker boot")
    except Exception as exc:  # fall back to lazy load on first request
        worker.log.warning("Engine warm-up skipped: %s", exc)
