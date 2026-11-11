#!/bin/sh
# Container start-up: prepare volumes, then run the web app (gunicorn) or the daily-jobs scheduler.
set -e
cd /app

if [ "$(id -u)" = "0" ]; then
    mkdir -p /app/data /app/media /app/staticfiles "${CACHE_DIR:-/app/data/cache}"
    # First start on a new server: put the demo photos into the (empty) media folder.
    if [ -z "$(ls -A /app/media 2>/dev/null)" ] && [ -d /opt/media_seed ]; then
        echo "First start: copying demo photos into media/"
        cp -a /opt/media_seed/. /app/media/
    fi
    chown -R app:app /app/data /app/media /app/staticfiles "${CACHE_DIR:-/app/data/cache}"
    # Static and media files must stay readable by the host's nginx.
    chmod -R a+rX /app/media /app/staticfiles
    # Drop root: run everything below as the unprivileged "app" user.
    exec setpriv --reuid=app --regid=app --init-groups "$0" "$@"
fi

case "$1" in
    web)
        python manage.py migrate --noinput
        python manage.py collectstatic --noinput --verbosity 0
        if [ "${AUTO_SEED:-True}" = "True" ]; then
            if ! python manage.py shell -c "import sys; from django.contrib.auth.models import User; sys.exit(0 if User.objects.exists() else 1)"; then
                echo "Empty database: loading the demo data (about a minute)..."
                # Demo photos normally ship in media/; if they are missing, seed_demo downloads them.
                if [ -d /app/media/demo_photos ]; then
                    python manage.py seed_demo --offline
                else
                    python manage.py seed_demo
                fi
            fi
        fi
        exec gunicorn config.wsgi:application \
            --bind 0.0.0.0:8000 \
            --workers "${GUNICORN_WORKERS:-3}" \
            --timeout "${GUNICORN_TIMEOUT:-120}" \
            --access-logfile - --error-logfile -
        ;;
    scheduler)
        exec /app/docker/scheduler.sh
        ;;
    *)
        exec "$@"
        ;;
esac
