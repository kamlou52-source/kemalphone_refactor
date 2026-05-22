# Dockerfile for Kemal Phone Solutions (Python 3.10)
FROM python:3.10-slim

# --- Runtime env ---
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# --- OS deps utiles (build wheels, reportlab/pillow si roue absente) ---
# note: psycopg2-binary n'a pas besoin de libpq ici
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libjpeg62-turbo \
    zlib1g \
    libfreetype6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- Dépendances Python (couche cache) ---
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# --- Code de l’app ---
COPY . /app

# --- Flask/Gunicorn ---
ENV FLASK_APP=app.py \
    FLASK_RUN_HOST=0.0.0.0

EXPOSE 5000

# Ajustez WEB_CONCURRENCY au besoin (default 3 via -w 3)
CMD ["gunicorn", "-w", "3", "-b", "0.0.0.0:5000", "app:app"]
