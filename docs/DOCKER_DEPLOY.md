# Deploy with Docker — https://interiors.devnixplus.com

The app runs in Docker on **127.0.0.1:9005**. Your server's existing **nginx** (not in Docker) serves
HTTPS, static files and uploads, and passes everything else to the app.

```
Visitor ──HTTPS──> nginx on the server ──> 127.0.0.1:9005 ──> Docker: web (gunicorn + Django)
                     │                                          Docker: scheduler (daily jobs)
                     ├─ /static/  ← /opt/interiors/docker-data/staticfiles/
                     └─ /media/   ← /opt/interiors/docker-data/media/
```

| File | What it is |
|---|---|
| `Dockerfile` | The image. All Python requirements are installed **inside** it — nothing on the server. |
| `docker-compose.yml` | Two containers: `web` (the site) and `scheduler` (daily automations + nightly demo reset). |
| `.env_server` | Server settings: port `APP_PORT=9005`, domain, secret key, demo options. **Private.** |
| `deploy/nginx/interiors.devnixplus.com.conf` | nginx config for your server. |
| `docker-data/` (created on the server) | Database, uploads and static files. Survives rebuilds — back this up. |

## 1. One-time server setup

Needs Docker with the compose plugin (`docker compose version`). Point the DNS **A record** of
`interiors.devnixplus.com` to the server's IP.

```bash
# 1. Get the code (includes media/ photos and the data snapshot docker/initial_data/data.json.gz):
git clone https://github.com/Deepaksinghpatel052/Interiors_demo.git /opt/interiors
cd /opt/interiors

# 2. Copy the private settings file from your PC (it is not in git):
#    scp .env_server user@SERVER:/opt/interiors/
#    Check DEVNIX_WHATSAPP, ANTHROPIC_API_KEY etc., then build and start:
docker compose --env-file .env_server up -d --build

# 3. Watch the first start until "Listening at: http://0.0.0.0:8000":
docker compose --env-file .env_server logs -f web

# 4. Check it answers on the port:
curl -I -H "Host: interiors.devnixplus.com" http://127.0.0.1:9005/
```

### What happens on the first start (automatic)

1. `migrate` creates all tables (migration files are part of the code; never run `makemigrations` on the server).
2. The database is empty, so the **data snapshot** `docker/initial_data/data.json.gz` is loaded:
   the same users, studio settings, projects, leads, quotations, enquiries and AI knowledge base as your PC.
3. The photos from `media/` are copied into `docker-data/media/`.
4. `collectstatic` prepares CSS/JS for nginx, then the site starts.

On later starts and updates only new migrations run; your server data is never replaced.

### Send your current local data to a new server

```bash
# on your PC (project venv)
python manage.py snapshot_data          # writes docker/initial_data/data.json.gz
git add -A && git commit -m "Update data snapshot" && git push
```

The snapshot is only loaded when the server database is **empty**. To replace the data on an existing
server (this deletes what is there):

```bash
docker compose --env-file .env_server down
sudo rm -rf docker-data/data docker-data/media
git pull && docker compose --env-file .env_server up -d --build
```

`.env_server` has `RESET_DEMO_NIGHTLY=False`, so the data stays exactly as loaded. Set it to `True` to rebuild
the standard demo data with fresh dates every night at `RESET_AT` (product enquiries are kept).

## 2. nginx + HTTPS certificate

```bash
# First time only — get the certificate (needs the DNS record from step 1):
sudo mkdir -p /var/www/certbot
#   a) put ONLY the first server { listen 80 ... } block of the config in place, reload nginx
#   b) issue the certificate:
sudo certbot certonly --webroot -w /var/www/certbot -d interiors.devnixplus.com

# Then install the full config:
sudo cp deploy/nginx/interiors.devnixplus.com.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/interiors.devnixplus.com.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

- Already have a wildcard certificate for `*.devnixplus.com`? Just change the two `ssl_certificate` lines.
- Project not in `/opt/interiors`? Change the two `alias` paths in the config.
- Changed `APP_PORT`? Change the port in the `upstream` block too.

Open https://interiors.devnixplus.com — demo logins: owner / designer / client = `demo12345`.
The **admin** login uses `ADMIN_PASSWORD` from `.env_server` (set on the first start), not the public `admin12345`.

## 3. Everyday commands (run in /opt/interiors)

| Task | Command |
|---|---|
| Update after code changes | `docker compose --env-file .env_server up -d --build` |
| Restart | `docker compose --env-file .env_server restart` |
| Logs | `docker compose --env-file .env_server logs -f web` (or `scheduler`) |
| Stop | `docker compose --env-file .env_server down` |
| Status | `docker compose --env-file .env_server ps` |
| Reset demo now | `docker compose --env-file .env_server exec web python manage.py reset_demo --offline` |
| Any manage.py command | `docker compose --env-file .env_server exec web python manage.py <command>` |
| Django shell | `docker compose --env-file .env_server exec web python manage.py shell` |

Always pass `--env-file .env_server`: it carries `APP_PORT`.

## 4. Daily jobs (no cron needed)

The `scheduler` container runs, on Indian time:
- `run_automations` at `AUTOMATIONS_AT` (08:00) — reminders and follow-ups.
- `reset_demo --offline` at `RESET_AT` (03:30) — only while `DEMO_MODE=True` and `RESET_DEMO_NIGHTLY=True`.
  Product enquiries are kept. Set `RESET_DEMO_NIGHTLY=False` if you don't want the nightly reset.

## 5. Backups

Everything that matters is in `docker-data/` (database `data/db.sqlite3` + `media/`). Example nightly
host cron (03:00, keeps 14 days):

```bash
0 3 * * * cd /opt/interiors && tar czf /opt/backups/interiors-$(date +\%F).tgz docker-data/data docker-data/media && find /opt/backups -name 'interiors-*.tgz' -mtime +14 -delete
```

## 6. Using it for a client's live site

Same files, new folder and port per client (e.g. `/opt/sharma`, `APP_PORT=9006`, their domain in
`ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`, `DEMO_MODE=False`, new `SECRET_KEY`, `AUTO_SEED=False`), then:

```bash
docker compose -p sharma --env-file .env_server up -d --build
docker compose -p sharma --env-file .env_server exec web python manage.py seed_demo --offline
docker compose -p sharma --env-file .env_server exec web python manage.py setup_client --owner-username sharma --owner-name "Rohit Sharma"
```

`setup_client` writes `DEMO_MODE=False` into the container's `.env`, which is lost on rebuild — so also
keep `DEMO_MODE=False` in that client's `.env_server`. Copy the nginx config with the new domain and port.
See `docs/NEW_CLIENT_SETUP.md` for the rest of the onboarding.

## Notes

- The app port is bound to `127.0.0.1`, so only nginx can reach it. That is why `TRUST_X_REAL_IP=True`
  is safe (rate limits see the visitor's real IP) — don't publish the port on `0.0.0.0`.
- A new `SECRET_KEY` is already in `.env_server`. Never share or commit that file.
- Image size is about 630 MB (Python + PDF/AI libraries).
