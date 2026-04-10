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

## Install on Proxmox

On the Proxmox host:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/RGVylar/uroboros/main/deploy/create-lxc.sh)
```

This creates and configures a new LXC automatically. See [`deploy/README.md`](deploy/README.md) for details and manual install options.

## Local backend dev

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

## Useful commands
```
pct exec 200 -- journalctl -u uroboros-backend -f &
pct exec 200 -- bash -c "cd /opt/uroboros && git pull && cd frontend && npm ci && npm run build && systemctl restart caddy"
pct exec 200 -- bash -c "
  cd /opt/uroboros && git pull
  source backend/.venv/bin/activate
  cd backend && alembic upgrade head
  cd ../frontend && npm ci && npm run build
  systemctl restart uroboros-backend caddy
"
```
