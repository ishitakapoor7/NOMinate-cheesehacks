# NOMinate

**One dish a day, nominated for you.** NOMinate learns what you like to eat, nominates a single dish each day, and then helps you follow through — pull up a real recipe to cook it, or find restaurants nearby that serve it. No endless scrolling, no decision fatigue: one good idea, then the resources to act on it.

Originally a CheeseHacks project, since rebuilt into a full-stack app with persistent accounts, a trained recommender, and live recipe and restaurant data.

---

## How it works

1. **Tell it how you eat** — cuisines you crave, dietary needs, allergies, kitchen skill, budget, what's in your pantry, and your location.
2. **Get your nomination** — a hybrid PyTorch recommender scores the dish catalog against your taste, hard-filters anything unsafe or off-diet, and picks one dish (with enough variety that repeat visits stay fresh).
3. **Cook it or order it** — "Cook it tonight" shows a real recipe (steps + quantities, fetched from Spoonacular and cached), with a checklist that highlights what you already have. "Order it out" surfaces nearby restaurants from Google Places with ratings, price, hours, and directions.
4. **Rate it** — your feedback (loved it → never again) feeds back into the model, so tomorrow's nomination gets smarter.

### A note on the recommender

The recommender is a hybrid model: learned user/dish embeddings (collaborative filtering) combined with content features — cuisine, skill, goal, budget, and an ingredient multi-hot. It's trained on a synthetic ratings dataset so it works from a cold start, and real ratings blend in on retrain as users accumulate them. Cuisine preference and pantry availability are applied as scoring boosts at inference time, while allergens, diets, and skill are enforced as hard filters. The dish catalog is a bounded set — a deliberate choice, since learning taste over time needs a fixed item vocabulary — seeded from TheMealDB and deepened per-cuisine from Spoonacular.

---

## Tech stack

| Layer | Stack |
|-------|-------|
| Frontend | React + Vite, Tailwind CSS, React Router |
| Backend | Flask (app factory + blueprints), SQLAlchemy, Alembic |
| Auth | JWT (access + refresh) with Google Sign-In |
| Database | PostgreSQL |
| ML | PyTorch, pandas, scikit-learn |
| External APIs | Spoonacular (recipes), Google Places (restaurants), Google OAuth |

---

## Repository layout

```
backend/
  app/            Flask application (app factory, config, extensions)
    auth/         signup / login / Google / JWT refresh
    api/          profile, recommend, cooking, takeout, feedback
    models/       SQLAlchemy models
    services/     recommender engine, retraining, recipes, places
  ml/             training pipeline, dataset generation, checkpoints
  migrations/     Alembic migrations
  tests/          pytest suite
  seed.py         load the dish catalog into Postgres
  wsgi.py         app entrypoint
frontend/
  src/
    pages/        the seven screens
    components/   nav, brand panel, route guards, Google button
    context/      AuthContext (session + tokens)
    lib/          axios client with token refresh
docker-compose.yml   Postgres for local dev
```

---

## Getting started

### Prerequisites

- Python 3.11+
- Node 18+
- Docker (for Postgres), or a local Postgres you point `DATABASE_URL` at

### 1. Database

```bash
docker compose up -d db
```

### 2. Backend

```bash
python -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt

# configure — copy the example and fill in secrets/keys
cp backend/.env.example backend/.env

cd backend
flask --app wsgi db upgrade    # create the schema
python seed.py                 # load the dish catalog
flask --app wsgi run --port 5001
```

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local     # set VITE_API_URL and (optionally) VITE_GOOGLE_CLIENT_ID
npm run dev                     # http://localhost:5173
```

Email/password signup works with no external keys. Google Sign-In, recipes, and restaurant search each light up once their key is set (see below); until then those features degrade gracefully.

### Environment variables

Backend (`backend/.env`):

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY`, `JWT_SECRET_KEY` | Flask / JWT signing secrets |
| `DATABASE_URL`, `TEST_DATABASE_URL` | Postgres connection strings |
| `CORS_ORIGINS` | Allowed frontend origins |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Google OAuth |
| `GOOGLE_PLACES_API_KEY` | Restaurant search (Places API New, billing enabled) |
| `SPOONACULAR_API_KEY` | Recipes ([free tier](https://spoonacular.com/food-api)) |

Frontend (`frontend/.env.local`): `VITE_API_URL`, `VITE_GOOGLE_CLIENT_ID`.

---

## Testing

```bash
cd backend
pytest
```

---

## Working with the model

The trained checkpoints are committed, so the app runs out of the box. To rebuild or extend:

```bash
cd backend

# deepen underserved cuisines from Spoonacular, then regenerate ratings
python -m ml.expand_catalog

# retrain the base model over ml/data/
cd ml && python train.py
```

`ml/generate_dataset.py` builds the synthetic users/dishes/ratings from scratch; `ml/expand_catalog.py` adds per-cuisine depth from Spoonacular. After changing the catalog, re-run `python seed.py` and restart the backend so it loads the new checkpoints.

---

## API overview

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/auth/signup`, `/auth/login`, `/auth/google` | Authentication |
| `POST` / `GET` | `/auth/refresh`, `/auth/me` | Session |
| `GET` / `PUT` | `/api/profile` | Taste profile |
| `GET` | `/api/recommend`, `/api/recommend/latest` | Daily nomination |
| `POST` | `/api/cooking` | Recipe + ingredient checklist |
| `POST` / `GET` | `/api/takeout`, `/api/takeout/photo` | Nearby restaurants |
| `POST` | `/api/feedback` | Rate the nomination |
