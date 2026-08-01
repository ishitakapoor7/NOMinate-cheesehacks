#!/usr/bin/env sh
# Prepare the database, then start the app server (the CMD passed as "$@").
# Compose waits for Postgres to be healthy before this runs, so no wait loop is
# needed. Both steps are idempotent and cheap on an already-provisioned DB.
set -e

echo "→ Applying database migrations…"
flask --app wsgi db upgrade

echo "→ Seeding catalog (skips when already populated)…"
python seed.py

echo "→ Starting server…"
exec "$@"
