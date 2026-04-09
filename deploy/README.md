# Deploy

One-shot installer for a fresh Debian 12 LXC on Proxmox.

## Quick install

Inside the LXC, as root:

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/RGVylar/uroboros/main/deploy/install.sh)"
```

Override defaults via env vars:

```bash
DOMAIN=comida.mugrelore.com \
REPO_BRANCH=main \
bash -c "$(curl -fsSL https://raw.githubusercontent.com/RGVylar/uroboros/main/deploy/install.sh)"
```

## What it does

1. Installs Python, PostgreSQL, Caddy, Node.js LTS, git.
2. Creates the `uroboros` system user and clones the repo to `/opt/uroboros`.
3. Creates the Postgres role + database.
4. Builds the backend venv and runs Alembic migrations.
5. Builds the SvelteKit frontend (if present).
6. Installs and starts the `uroboros-backend` systemd unit.
7. Configures Caddy as a local reverse proxy on port 80.

## Cloudflare Tunnel

Point your tunnel hostname (`comida.mugrelore.com`) at `http://127.0.0.1:80`
inside this LXC. TLS is terminated at Cloudflare; Caddy serves plain HTTP locally.

## Updating

Re-run the installer. It will `git pull`, reinstall deps, run migrations,
rebuild the frontend and restart services.

## Logs

```bash
journalctl -u uroboros-backend -f
journalctl -u caddy -f
```
