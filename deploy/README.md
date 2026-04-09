# Deploy

One-shot installer for a fresh Debian 12 LXC on Proxmox.

## Quick install on Proxmox

On the **Proxmox host** (not inside an LXC):

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/RGVylar/uroboros/main/deploy/create-lxc.sh)
```

This will:
1. Create a new Debian 12 LXC container
2. Start it
3. Run the full installer inside

Customize via env vars:

```bash
CT_ID=201 CT_NAME=uroboros-prod DOMAIN=comida.mugrelore.com \
bash <(curl -fsSL https://raw.githubusercontent.com/RGVylar/uroboros/main/deploy/create-lxc.sh)
```

**Or manually**: If you already have an LXC running, SSH into it and:

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/RGVylar/uroboros/main/deploy/install.sh)"
```

## Scripts

### `create-lxc.sh` — Proxmox integration

Run on the **Proxmox host** to create a fresh LXC container and configure it:

```bash
bash create-lxc.sh
```

Env vars:
- `CT_ID=200` — container ID
- `CT_NAME=uroboros` — hostname
- `CT_STORAGE=local-lvm` — storage pool
- `CT_MEMORY=2048` — RAM in MB
- `CT_CORES=2` — CPU cores
- `CT_DISK=20` — disk size in GB
- `DOMAIN=comida.mugrelore.com` — your domain

### `install.sh` — LXC installer

Run **inside** the LXC (or on any Debian 12 machine).

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
