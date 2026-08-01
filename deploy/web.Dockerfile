# Build the React app, then serve it (and reverse-proxy the API) with Caddy.
# Build context is the repo root so this can see both frontend/ and deploy/.

# ── Stage 1: build the static site ───────────────────────────────────────────
FROM node:20-alpine AS build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
# Vite bakes these in at build time. Same-origin API (Caddy proxies /api), so
# VITE_API_URL is the site's own https URL.
ARG VITE_API_URL
ARG VITE_GOOGLE_CLIENT_ID
ENV VITE_API_URL=$VITE_API_URL \
    VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID
RUN npm run build

# ── Stage 2: Caddy serves the build + proxies the API, with auto-HTTPS ────────
FROM caddy:2-alpine
COPY --from=build /app/dist /srv
COPY deploy/Caddyfile /etc/caddy/Caddyfile
