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

---

# Operar el LXC 200 (día a día)

> Todo lo de aquí abajo se ejecuta **desde el host Proxmox**, con `pct exec`.
> Probado en el despliegue del 2026-07-29.

## ⚠️ NO re-ejecutes `install.sh` para actualizar

Reescribe `/opt/uroboros/backend/.env` desde cero con su heredoc. Eso:

- **Rota `JWT_SECRET`** → todas las sesiones abiertas se caen y hay que volver
  a iniciar sesión.
- **Pierde `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `VAPID_*`, `RESEND_API_KEY`
  y `MEDIA_DIR`**, que no están en esa plantilla. Adiós alertas, push, emails de
  recuperación y fotos de perfil.

La contraseña de la BD sí sobrevive (hace `ALTER USER` con la nueva, así que
`.env` y Postgres quedan consistentes), pero lo demás no. Usa los comandos de
abajo.

## Despliegue normal

Backend primero, frontend después: si sale antes el frontend nuevo, llama a
endpoints que todavía no existen.

```bash
pct exec 200 -- bash -c "cd /opt/uroboros && git pull && cd backend && .venv/bin/alembic upgrade head && systemctl restart uroboros-backend"
```

```bash
pct exec 200 -- bash -c "git config --global --add safe.directory /opt/uroboros && cd /opt/uroboros && git pull && cd frontend && npm ci && npm run build && systemctl restart caddy"
```

## Cuando el despliegue lleva algo más que código

El de arriba **no basta** si la release toca alguna de estas cosas. Señales y
qué añadir:

### Dependencia nueva de Python

`git pull` no instala nada. Si el backend importa un paquete que no está, **no
arranca** — y como las migraciones sí funcionan sin él, te quedas con la BD
migrada y el servicio muerto. Instala **antes** de migrar y reiniciar:

```bash
pct exec 200 -- bash -c "cd /opt/uroboros/backend && .venv/bin/pip install -e . && .venv/bin/python -c 'import PIL; print(\"Pillow\", PIL.__version__)'"
```

### Variable nueva en el `.env`

Añádela sin tocar el resto del fichero (idempotente: no duplica si ya está):

```bash
pct exec 200 -- bash -c "test -f /opt/uroboros/backend/.env && (grep -q '^MEDIA_DIR=' /opt/uroboros/backend/.env || echo 'MEDIA_DIR=/var/lib/uroboros/media' >> /opt/uroboros/backend/.env) && tail -3 /opt/uroboros/backend/.env"
```

### Cambió `uroboros-backend.service`

Hay que instalarlo y recargar systemd **antes** de reiniciar el servicio:

```bash
pct exec 200 -- bash -c "install -m 644 /opt/uroboros/deploy/uroboros-backend.service /etc/systemd/system/ && systemctl daemon-reload && echo UNIDAD-OK"
```

### Cambió el Caddyfile

`/etc/caddy/Caddyfile` es un fichero aparte: el `git pull` **no lo toca**. Se
regenera desde la referencia del repo sustituyendo los placeholders. Compara
antes de pisarlo, por si tenía algo a mano:

```bash
pct exec 200 -- bash -c "sed -e 's|__BACKEND_PORT__|8000|g' -e 's|__APP_DIR__|/opt/uroboros|g' /opt/uroboros/deploy/Caddyfile > /tmp/Caddyfile.new && diff /etc/caddy/Caddyfile /tmp/Caddyfile.new; echo '--- fin del diff ---'"
```

Si el diff convence:

```bash
pct exec 200 -- bash -c "cp /etc/caddy/Caddyfile /etc/caddy/Caddyfile.bak && cp /tmp/Caddyfile.new /etc/caddy/Caddyfile && caddy validate --config /etc/caddy/Caddyfile && systemctl reload caddy && echo CADDY-OK"
```

## Verificar que ha ido bien

`active` + `{"status":"ok"}` + el listado del directorio de fotos. Lo tercero es
lo que prueba que `MEDIA_DIR` se está aplicando: ese directorio lo crea el
backend al arrancar, así que si no aparece las fotos están yendo a `/tmp` y se
perderán en el siguiente reinicio.

```bash
pct exec 200 -- bash -c "systemctl restart uroboros-backend && sleep 3 && systemctl is-active uroboros-backend && curl -sf localhost:8000/api/health && ls -la /var/lib/uroboros/media/avatars"
```

Y si falla:

```bash
pct exec 200 -- bash -c "journalctl -u uroboros-backend -n 40 --no-pager"
```

## Volver atrás

Las migraciones de este proyecto solo **añaden** columnas, así que el código
viejo funciona contra el esquema nuevo: revertir es volver el código, sin tocar
la BD.

```bash
pct exec 200 -- bash -c "cd /opt/uroboros && git reset --hard <sha-anterior> && systemctl restart uroboros-backend && cd frontend && npm ci && npm run build && systemctl reload caddy"
```

## Problemas que ya nos han pasado

### `git pull` aborta: "Your local changes would be overwritten"

Suele ser solo el bit de ejecución (alguien hizo `chmod +x` a un script).
**Mira el diff antes de descartar nada** — puede ser un ajuste real:

```bash
pct exec 200 -- bash -c "cd /opt/uroboros && git diff backend/scripts/backup.sh"
```

Si sale únicamente `old mode 100644 / new mode 100755`, la solución **no** es
`git checkout --` (devolvería el modo a 644 y le quitaría el `+x`). Se le dice a
git que ignore el bit de ejecución en este repo, lo que además evita que vuelva
a pasar en cada despliegue:

```bash
pct exec 200 -- bash -c "cd /opt/uroboros && git config core.fileMode false && git pull && chmod +x backend/scripts/backup.sh && ls -l backend/scripts/backup.sh"
```

Nunca `git reset --hard` aquí: se llevaría por delante el cambio sin que
llegues a verlo.

## Backups

Cron nocturno a las 2:00 (`/etc/cron.d/uroboros-backup`), 30 días de retención
en `/var/backups/uroboros`. Guarda el dump de Postgres **y** un tar de las fotos
de perfil, con el mismo sello de tiempo — al restaurar hacen falta los dos.

Lanzarlo a mano (recomendado antes de cualquier despliegue con migraciones):

```bash
pct exec 200 -- bash -c "bash /opt/uroboros/backend/scripts/backup.sh"
```

> El aviso `could not change directory to "/root": Permission denied` es de
> `sudo -u postgres` y es inofensivo: el backup se completa igual.

## Inspeccionar datos

```bash
pct exec 200 -- bash -c 'sudo -u postgres psql -d uroboros -c "SELECT id, name, avatar_photo FROM users ORDER BY id;"'
```

Fotos de perfil en disco (cuántas y cuánto ocupan):

```bash
pct exec 200 -- bash -c 'ls -lh /var/lib/uroboros/media/avatars; du -sh /var/lib/uroboros/media/avatars; find /var/lib/uroboros/media/avatars -name "*.webp" | wc -l'
```

## Duración de la sesión

La decide `JWT_EXPIRE_MINUTES` del `.env`, que **pisa** el default de
`config.py`. No hay refresh token: cuando caduca, el usuario vuelve a escribir
email y contraseña.

```bash
pct exec 200 -- bash -c "grep JWT_EXPIRE /opt/uroboros/backend/.env"
```

Valores: `10080` = 7 días · `43200` = 30 días · `129600` = 90 días.

```bash
pct exec 200 -- bash -c "sed -i 's/^JWT_EXPIRE_MINUTES=.*/JWT_EXPIRE_MINUTES=129600/' /opt/uroboros/backend/.env && grep JWT_EXPIRE /opt/uroboros/backend/.env && systemctl restart uroboros-backend"
```

> Solo afecta a los tokens **nuevos**; las sesiones ya abiertas conservan su
> caducidad. Y ojo: el token solo lleva `sub` y `exp`, así que **cambiar la
> contraseña no cierra las sesiones abiertas** y no hay forma de revocarlas.

## Webhook de Telegram (botón de rechazar foto)

Solo hace falta una vez, y de nuevo cada vez que rotes el token del bot (el
webhook se registra contra el token).

```bash
pct exec 200 -- bash -c "cd /opt/uroboros/backend && .venv/bin/python scripts/set_telegram_webhook.py"
```

Diagnóstico si el botón no responde — mira `url`, `pending_update_count` y sobre
todo `last_error_message`:

```bash
pct exec 200 -- bash -c 'cd /opt/uroboros/backend && set -a && . .env && set +a && curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getWebhookInfo"'
```

## Logs

```bash
journalctl -u uroboros-backend -f
journalctl -u caddy -f
```
