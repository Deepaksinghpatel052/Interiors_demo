# Studio OS (Aangan Interiors demo) — Django + gunicorn. All settings come from .env at run time.
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# tzdata: lets TZ from .env (e.g. Asia/Kolkata) set the clock for the scheduler's daily jobs.
RUN apt-get update \
 && apt-get install -y --no-install-recommends tzdata \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# All Python requirements live inside the image; nothing is installed on the server itself.
COPY requirements.txt .
RUN pip install -r requirements.txt gunicorn==23.0.0

COPY . .

# Demo photos shipped with the code are kept aside and copied into the media volume on first start.
RUN sed -i 's/\r$//' docker/*.sh \
 && chmod +x docker/*.sh \
 && mkdir -p /app/media && mv /app/media /opt/media_seed \
 && mkdir -p /app/media /app/data /app/staticfiles \
 && useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin app \
 && chown -R app:app /app /opt/media_seed

# The port comes from APP_PORT in .env (see docker-compose.yml).
ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["web"]
