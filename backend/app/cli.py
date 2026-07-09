"""Custom Flask CLI commands.

    flask retrain            # blend real + synthetic ratings, retrain, go live
    flask retrain --epochs 5 # quicker run for smoke-testing the pipeline
"""
import click
from flask import Flask


def register(app: Flask) -> None:
    @app.cli.command("retrain")
    @click.option("--epochs", default=50, show_default=True, help="Max training epochs.")
    @click.option(
        "--real-weight",
        default=10,
        show_default=True,
        help="How many times each real rating is duplicated vs synthetic ones.",
    )
    def retrain_command(epochs: int, real_weight: int):
        """Retrain the recommender on real + synthetic ratings."""
        from app.services.retrain import retrain

        result = retrain(epochs=epochs, real_rating_weight=real_weight, log=click.echo)
        click.echo(
            f"Done: {result['version']} (val RMSE {result['best_val_rmse']:.4f}, "
            f"{result['epochs_run']} epochs)"
        )
