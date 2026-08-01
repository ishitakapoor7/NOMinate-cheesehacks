# NumPy-only API image — no torch, so it's small and boots fast.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

WORKDIR /app

# Install runtime deps first so Docker caches this layer across code changes.
# requirements.txt deliberately excludes torch (see the file's note).
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN chmod +x docker-entrypoint.sh

EXPOSE 8000

# Entrypoint runs migrations + seed (both idempotent/cheap), then hands off to CMD.
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["gunicorn", "wsgi:app", "-c", "gunicorn.conf.py"]
