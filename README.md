# Uroboros

Self-hosted macro & calorie tracker for couples. Killer feature: log a single
meal for two users at once.

## Stack

- **Backend:** FastAPI + SQLAlchemy + Alembic + PostgreSQL
- **Frontend:** SvelteKit PWA
- **Mobile:** SvelteKit + Capacitor (`@capacitor-mlkit/barcode-scanning`)
- **Auth:** JWT + bcrypt
- **Products:** Open Food Facts (cache-aside)
- **Deploy:** Debian 12 LXC on Proxmox, systemd + Caddy + Cloudflare Tunnel

## Layout

```
uroboros/
├── backend/   # FastAPI app, Alembic migrations
├── frontend/  # SvelteKit PWA + Capacitor wrapper
├── deploy/    # install.sh, systemd units, Caddyfile
└── README.md
```

## Install on a fresh LXC

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/RGVylar/uroboros/main/deploy/install.sh)"
```

See [`deploy/README.md`](deploy/README.md) for details.

## Local backend dev

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```
