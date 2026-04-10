#!/usr/bin/env bash
# Create and configure a Uroboros LXC on Proxmox
# Run this on the Proxmox host (not inside the LXC)
# Usage (on Proxmox host):
#   bash create-lxc.sh
#   CT_NAME=uroboros CT_ID=200 bash create-lxc.sh

set -euo pipefail

# ---------- pretty output ----------
RED=$'\033[0;31m'; GRN=$'\033[0;32m'; YLW=$'\033[1;33m'; BLU=$'\033[0;34m'; NC=$'\033[0m'
msg()  { echo -e "${BLU}[*]${NC} $*"; }
ok()   { echo -e "${GRN}[+]${NC} $*"; }
warn() { echo -e "${YLW}[!]${NC} $*"; }
die()  { echo -e "${RED}[x]${NC} $*" >&2; exit 1; }

# ---------- check we're on proxmox ----------
command -v pct >/dev/null || die "pct not found — run this on Proxmox host, not inside an LXC"

# ---------- config ----------
CT_NAME="${CT_NAME:-uroboros}"
CT_ID="${CT_ID:-200}"
CT_STORAGE="${CT_STORAGE:-local-lvm}"
CT_MEMORY="${CT_MEMORY:-2048}"
CT_CORES="${CT_CORES:-2}"
CT_DISK="${CT_DISK:-20}"
CT_NET="${CT_NET:-name=eth0,bridge=vmbr0,ip=dhcp,type=veth}"

DOMAIN="${DOMAIN:-comida.mugrelore.com}"
BACKEND_PORT="${BACKEND_PORT:-8000}"

# ---------- check CT doesn't exist ----------
if pct status "$CT_ID" >/dev/null 2>&1; then
    die "CT $CT_ID already exists. Pick another CT_ID or delete it first."
fi

# ---------- create LXC ----------
msg "Creating LXC container…"
TEMPLATE_FILE="debian-12-standard_12.12-1_amd64.tar.zst"

# Try different template paths
for TEMPLATE in "local:vztmpl/$TEMPLATE_FILE" "$TEMPLATE_FILE"; do
    pct create "$CT_ID" "$TEMPLATE" \
        --hostname "$CT_NAME" \
        --storage "$CT_STORAGE" \
        --memory "$CT_MEMORY" \
        --cores "$CT_CORES" \
        --rootfs "${CT_STORAGE}:${CT_DISK}" \
        --net0 "$CT_NET" \
        --nameserver 1.1.1.1 \
        --unprivileged 1 \
        2>&1 && break || continue
done
[[ $? -eq 0 ]] || die "Failed to create container. Is debian-12 template downloaded?"
ok "Container $CT_ID ($CT_NAME) created"

# ---------- start LXC ----------
msg "Starting container…"
pct start "$CT_ID"
sleep 3  # Give it a moment to boot
ok "Container started"

# ---------- wait for network + get IP ----------
msg "Waiting for network…"
CT_IP=""
for i in $(seq 1 30); do
    CT_IP=$(pct exec "$CT_ID" -- hostname -I 2>/dev/null | awk '{print $1}')
    [[ -n "$CT_IP" ]] && break
    sleep 2
done
[[ -n "$CT_IP" ]] || die "Container never got an IP. Check DHCP on bridge vmbr0."
ok "Container IP: $CT_IP"

# ---------- run installer ----------
msg "Running installer inside container…"

msg "Installing git…"
pct exec "$CT_ID" -- apt-get update -qq
pct exec "$CT_ID" -- apt-get install -y -qq git curl ca-certificates

msg "Cloning repo…"
pct exec "$CT_ID" -- rm -rf /tmp/uroboros
pct exec "$CT_ID" -- git clone --branch main https://github.com/RGVylar/uroboros.git /tmp/uroboros

msg "Running install.sh…"
pct exec "$CT_ID" -- env DOMAIN="$DOMAIN" BACKEND_PORT="$BACKEND_PORT" bash /tmp/uroboros/deploy/install.sh

echo ""
cat <<EOF
${GRN}✔ Uroboros LXC ready${NC}

  Container ID:  $CT_ID
  Container IP:  $CT_IP
  Domain:        $DOMAIN  (point your Cloudflare Tunnel here)
  Backend:       http://127.0.0.1:$BACKEND_PORT/health
  SSH:           ssh root@$CT_IP

${YLW}Next: Configure Cloudflare Tunnel to point $DOMAIN to http://$CT_IP:80${NC}

Logs:
  pct exec $CT_ID -- journalctl -u uroboros-backend -f
  pct exec $CT_ID -- journalctl -u caddy -f
EOF
