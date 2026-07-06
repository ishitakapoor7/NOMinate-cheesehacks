"""WSGI entrypoint.

Run in dev:   flask --app wsgi run --port 5001
Run in prod:  gunicorn wsgi:app
"""
from app import create_app

app = create_app()


if __name__ == "__main__":
    app.run(debug=True, port=5001)
