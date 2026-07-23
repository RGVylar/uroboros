"""Resolve the latest Android build and redirect to its download.

The GitHub pipeline uploads each debug APK to a Nextcloud folder with a
timestamped name (`uroboros-debug-YYYYMMDD-HHMM.apk`). Because the upload share
renames duplicates instead of overwriting, there is no stable "latest" filename
to link to. So the in-app "Actualizar" button points here: we list the folder
via the read-only public share (WebDAV PROPFIND), pick the most recently
modified `.apk`, and redirect to its direct download.

Public + unauthenticated on purpose: the button opens this in an external
browser (Android), where there is no session/JWT to send.
"""
import threading
import time as _time
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from urllib.parse import quote, unquote

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter(prefix="/download", tags=["download"])

# Invite landing lives outside the /download prefix so the shared URL is short.
landing_router = APIRouter(tags=["download"])

# Read-only public share of the APK folder. The pipeline uploads via a separate
# upload-only share; this one only exposes listing + download.
_SHARE_TOKEN = "ww2FbfP67R6PNiR"
_NC_BASE = "https://files.mugrelore.com"
_WEBDAV_URL = f"{_NC_BASE}/public.php/dav/files/{_SHARE_TOKEN}/"
_SHARE_URL = f"{_NC_BASE}/index.php/s/{_SHARE_TOKEN}"
# Fallback: the share's folder page, so a failure still lands the user somewhere useful.
_FOLDER_FALLBACK = _SHARE_URL

_DAV_NS = "{DAV:}"


# The WebDAV listing takes 1-3s against Nextcloud, which made the download
# button feel sluggish. Cache the resolved name and refresh it in the
# background from the landing view, so the click itself is instant.
_CACHE_TTL = 600.0  # seconds
_cache: dict = {"name": None, "at": 0.0}


def _cached_apk_name() -> str | None:
    if _time.monotonic() - _cache["at"] < _CACHE_TTL and _cache["name"]:
        return _cache["name"]
    name = _latest_apk_name()
    if name:
        _cache.update(name=name, at=_time.monotonic())
    return name


def _warm_cache_async() -> None:
    """Refresh the cache off-thread if stale (fire-and-forget)."""
    if _time.monotonic() - _cache["at"] < _CACHE_TTL:
        return
    threading.Thread(target=_cached_apk_name, daemon=True).start()


def _latest_apk_name() -> str | None:
    """Return the filename of the most recently modified .apk, or None."""
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.request(
                "PROPFIND",
                _WEBDAV_URL,
                auth=(_SHARE_TOKEN, ""),
                headers={"Depth": "1"},
            )
        resp.raise_for_status()
    except httpx.HTTPError:
        return None

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError:
        return None

    latest_name: str | None = None
    latest_dt = None
    for response in root.findall(f"{_DAV_NS}response"):
        href = response.findtext(f"{_DAV_NS}href") or ""
        # href is URL-encoded (spaces as %20 etc.); decode for a clean filename.
        name = unquote(href.rstrip("/").rsplit("/", 1)[-1])
        if not name.lower().endswith(".apk"):
            continue
        modified = response.find(
            f".//{_DAV_NS}getlastmodified"
        )
        if modified is None or not modified.text:
            continue
        try:
            dt = parsedate_to_datetime(modified.text)
        except (TypeError, ValueError):
            continue
        if latest_dt is None or dt > latest_dt:
            latest_dt = dt
            latest_name = name

    return latest_name


@router.get("/latest-apk")
def latest_apk() -> RedirectResponse:
    """Redirect to the direct download of the newest debug APK."""
    name = _cached_apk_name()
    if not name:
        # Couldn't resolve a specific file — send them to the folder instead.
        return RedirectResponse(_FOLDER_FALLBACK, status_code=302)
    download_url = f"{_SHARE_URL}/download?path=%2F&files={quote(name)}"
    return RedirectResponse(download_url, status_code=302)


_APP_URL = "https://comida.mugrelore.com"

# The invite message links here instead of at the raw APK: messaging apps'
# crawlers need an HTML page with Open Graph tags to render a preview card
# (a 302 to a binary shows a bare domain), and — until the app is on Google
# Play — this page has to earn the trust of someone about to sideload an APK:
# clear pitch, install steps, and the open-source link. It's also where a
# future invite deep-link would plug in (open the add-friend modal in the app).
_LANDING_HTML = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Únete a uroboros 🐍</title>
<meta property="og:type" content="website">
<meta property="og:site_name" content="uroboros">
<meta property="og:title" content="uroboros — come mejor, en pareja">
<meta property="og:description" content="La app para llevar la comida con tu pareja: registra una comida para los dos a la vez, compite en constancia y comparte la lista de la compra.">
<meta property="og:image" content="{APP}/social-banner.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:url" content="{APP}/api/unete">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{APP}/logo.png" type="image/png">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: #06070a; color: #eef1f5;
    font-family: 'Segoe UI', system-ui, sans-serif;
    min-height: 100dvh;
    background-image:
      radial-gradient(60% 45% at 15% 0%, oklch(45% 0.12 170 / 0.22), transparent 60%),
      radial-gradient(50% 40% at 90% 15%, oklch(45% 0.14 300 / 0.16), transparent 60%),
      radial-gradient(70% 50% at 50% 110%, oklch(40% 0.1 220 / 0.18), transparent 60%);
    background-attachment: fixed;
  }
  .wrap { max-width: 460px; margin: 0 auto; padding: 40px 20px 32px; }

  /* En escritorio la columna de 460px deja demasiado aire a los lados: pasamos
     a un split a pantalla completa — izquierda el gancho (marca + ventajas),
     derecha un panel con todo lo de descargar. */
  @media (min-width: 900px) {
    .wrap { max-width: none; padding: 0; }
    .cols {
      display: grid; grid-template-columns: 1.05fr 1fr;
      min-height: 100dvh; align-items: stretch;
    }
    .col {
      padding: 60px 48px;
      display: flex; flex-direction: column; justify-content: center;
    }
    /* El panel de descarga se separa del fondo con un velo y un filo. */
    .col + .col {
      background: rgba(255,255,255,0.035);
      border-left: 1px solid rgba(255,255,255,0.09);
    }
    .col > * { width: 100%; max-width: 460px; }
    .col + .col > * { max-width: 400px; margin-left: auto; margin-right: auto; }
  }

  /* Hero */
  .hero { text-align: center; margin-bottom: 26px; }
  .hero img { width: 96px; height: 96px; filter: drop-shadow(0 12px 32px oklch(70% 0.18 165 / 0.35)); }
  h1 {
    font-family: Lora, Georgia, serif; font-weight: 500;
    font-size: 2.6rem; letter-spacing: -0.04em; margin-top: 10px;
  }
  .tag { color: oklch(85% 0.17 160); font-weight: 600; font-size: 1.02rem; margin-top: 4px; }
  .pitch { color: rgba(255,255,255,0.6); font-size: 0.92rem; line-height: 1.55; margin: 14px auto 0; max-width: 340px; }
  @media (min-width: 900px) {
    .hero { text-align: left; margin-bottom: 0; }
    .hero img { width: 72px; height: 72px; }
    h1 { font-size: 3.2rem; margin-top: 8px; }
    .tag { font-size: 1.15rem; margin-top: 2px; }
    .pitch { margin-left: 0; margin-right: 0; max-width: 420px; font-size: 0.95rem; }
  }

  /* Cards */
  .card {
    background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.09);
    border-radius: 20px; padding: 18px; margin-bottom: 12px;
    backdrop-filter: blur(22px) saturate(1.3); -webkit-backdrop-filter: blur(22px) saturate(1.3);
  }
  .feat { display: flex; gap: 12px; align-items: flex-start; padding: 9px 4px; }
  .feat .ico {
    width: 38px; height: 38px; flex-shrink: 0; border-radius: 12px; font-size: 1.05rem;
    background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.08);
    display: flex; align-items: center; justify-content: center;
  }
  .feat b { font-size: 0.88rem; display: block; }
  .feat span { font-size: 0.78rem; color: rgba(255,255,255,0.5); line-height: 1.45; }
  @media (min-width: 900px) {
    /* En el lado del gancho las ventajas van sueltas sobre el degradado:
       una tarjeta ahí competiría con el panel de descarga. */
    .col:first-child .card {
      background: none; border: 0; padding: 0; margin: 30px 0 0;
      backdrop-filter: none; -webkit-backdrop-filter: none;
    }
    .col:first-child .feat { padding: 8px 0; }
  }

  /* CTA */
  a.btn {
    display: block; text-align: center; padding: 16px; border-radius: 16px; text-decoration: none;
    background: linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170));
    color: #041010; font-weight: 800; font-size: 1.05rem; letter-spacing: -0.01em;
    box-shadow: 0 1px 0 rgba(255,255,255,0.3) inset, 0 14px 34px -8px oklch(75% 0.2 165 / 0.45);
  }
  /* Trust */
  .trust h2 { font-size: 0.85rem; display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
  .trust p { font-size: 0.78rem; color: rgba(255,255,255,0.55); line-height: 1.55; }
  .trust ol { margin: 10px 0 0 2px; list-style: none; counter-reset: step; }
  .trust li {
    counter-increment: step; font-size: 0.78rem; color: rgba(255,255,255,0.65);
    padding: 4px 0 4px 30px; position: relative; line-height: 1.45;
  }
  .trust li::before {
    content: counter(step); position: absolute; left: 0; top: 3px;
    width: 20px; height: 20px; border-radius: 50%; font-size: 0.68rem; font-weight: 800;
    background: oklch(75% 0.18 165 / 0.15); border: 1px solid oklch(75% 0.18 165 / 0.35);
    color: oklch(88% 0.16 160); display: flex; align-items: center; justify-content: center;
  }
  .trust a { color: oklch(85% 0.17 160); text-decoration: none; }

  /* QR: solo tiene sentido en pantallas grandes (móvil ya tiene el botón). */
  .qr { display: none; }
  @media (min-width: 560px) {
    .qr {
      display: flex; gap: 15px; align-items: center; margin-top: 12px; padding: 18px;
      background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.09);
      border-radius: 20px;
      backdrop-filter: blur(22px) saturate(1.3); -webkit-backdrop-filter: blur(22px) saturate(1.3);
    }
    .qr svg { width: 104px; height: 104px; flex-shrink: 0; border-radius: 10px; }
    .qr b { font-size: 0.85rem; display: block; margin-bottom: 4px; }
    .qr span { font-size: 0.78rem; color: rgba(255,255,255,0.55); line-height: 1.5; }
  }
  /* Dentro del panel de descarga el QR no necesita tarjeta: el propio panel
     ya lo separa del fondo. */
  @media (min-width: 900px) {
    .qr {
      background: none; border: 0; border-radius: 0; padding: 4px 0 0;
      margin-top: 14px; backdrop-filter: none; -webkit-backdrop-filter: none;
    }
  }

  a.web {
    display: block; text-align: center; margin: 18px 0 0; color: rgba(255,255,255,0.55);
    font-size: 0.85rem; text-decoration: none;
  }
  a.web:hover { color: #eef1f5; }
  footer {
    text-align: center; margin-top: 26px; font-size: 0.7rem; color: rgba(255,255,255,0.3);
  }
  footer a { color: rgba(255,255,255,0.45); text-decoration: none; margin: 0 6px; }
</style>
</head>
<body>
<div class="wrap">
 <div class="cols">
  <div class="col">
  <div class="hero">
    <img src="{APP}/logo.png" alt="uroboros" width="96" height="96">
    <h1>uroboros</h1>
    <div class="tag">Come mejor. Juntos.</div>
    <p class="pitch">Te han invitado a la app para llevar la comida <b>en pareja</b>: una sola vez, para los dos.</p>
  </div>

  <div class="card">
    <div class="feat"><div class="ico">🍽️</div><div><b>Registro a dos</b><span>Apunta una comida y aparece en el diario de ambos, con sus macros calculados.</span></div></div>
    <div class="feat"><div class="ico">📊</div><div><b>Objetivos y progreso</b><span>Calorías, proteína, agua, peso y medidas — con historial y tendencias.</span></div></div>
    <div class="feat"><div class="ico">🍳</div><div><b>Recetas e inventario compartido</b><span>La despensa y la lista de la compra, comunes de verdad.</span></div></div>
    <div class="feat"><div class="ico">⚔️</div><div><b>Duelo semanal</b><span>Un pique sano: quién cumple más sus propios objetivos cada semana.</span></div></div>
  </div>
  </div>

  <div class="col">
  <div class="dl">
  <a class="btn" href="{APP}/api/download/latest-apk">📥 Descargar para Android</a>

  <div class="qr">
    <svg viewBox="0 0 37 37" role="img" aria-label="Código QR para descargar la app en el móvil"><rect width="37" height="37" fill="#fff"/><path stroke="#0b0f14" d="M2 2.5h7m4 0h2m3 0h1m1 0h4m1 0h1m2 0h7m-33 1h1m5 0h1m3 0h2m3 0h2m1 0h1m2 0h2m1 0h1m1 0h1m5 0h1m-33 1h1m1 0h3m1 0h1m1 0h3m1 0h1m1 0h1m1 0h1m1 0h1m1 0h2m4 0h1m1 0h3m1 0h1m-33 1h1m1 0h3m1 0h1m1 0h1m1 0h1m7 0h2m2 0h1m3 0h1m1 0h3m1 0h1m-33 1h1m1 0h3m1 0h1m1 0h3m3 0h5m2 0h1m1 0h1m2 0h1m1 0h3m1 0h1m-33 1h1m5 0h1m1 0h1m1 0h2m5 0h1m2 0h2m4 0h1m5 0h1m-33 1h7m1 0h1m1 0h1m1 0h1m1 0h1m1 0h1m1 0h1m1 0h1m1 0h1m1 0h1m1 0h7m-25 1h1m2 0h1m2 0h1m1 0h1m2 0h1m1 0h2m1 0h1m-25 1h1m1 0h5m2 0h2m2 0h2m2 0h1m1 0h1m4 0h1m1 0h5m-28 1h1m1 0h1m1 0h2m3 0h3m2 0h1m1 0h3m1 0h1m2 0h2m1 0h2m1 0h1m-31 1h1m1 0h4m1 0h3m1 0h5m2 0h3m2 0h2m1 0h1m1 0h2m-32 1h2m1 0h1m3 0h1m1 0h1m1 0h3m1 0h4m1 0h3m1 0h3m1 0h5m-33 1h1m5 0h1m2 0h4m1 0h1m1 0h1m5 0h4m1 0h3m1 0h2m-33 1h2m2 0h1m2 0h4m4 0h1m2 0h3m1 0h2m2 0h1m2 0h4m-31 1h1m1 0h1m1 0h1m2 0h1m1 0h3m1 0h4m3 0h1m1 0h4m2 0h2m-32 1h1m1 0h1m6 0h3m1 0h3m2 0h1m2 0h1m3 0h2m1 0h3m-27 1h1m1 0h7m1 0h2m1 0h1m4 0h4m1 0h2m3 0h1m-32 1h1m3 0h1m4 0h1m1 0h1m3 0h1m1 0h4m1 0h1m2 0h2m1 0h2m1 0h1m-33 1h1m3 0h1m1 0h1m1 0h2m5 0h2m1 0h1m8 0h2m1 0h1m-31 1h1m4 0h1m4 0h1m2 0h1m2 0h1m2 0h1m1 0h2m2 0h1m1 0h5m-32 1h2m1 0h1m2 0h1m2 0h1m1 0h2m1 0h1m3 0h1m1 0h1m1 0h4m1 0h3m2 0h1m-33 1h2m2 0h2m1 0h1m6 0h3m2 0h2m1 0h2m2 0h1m2 0h1m2 0h1m-33 1h1m1 0h2m1 0h7m2 0h1m5 0h3m4 0h3m1 0h1m-32 1h1m1 0h2m1 0h1m1 0h3m2 0h3m1 0h1m4 0h3m1 0h2m1 0h3m-31 1h1m2 0h6m4 0h1m3 0h2m1 0h1m1 0h8m1 0h1m-24 1h1m2 0h3m2 0h7m1 0h1m3 0h1m1 0h1m1 0h1m-33 1h7m2 0h1m1 0h1m2 0h4m2 0h5m1 0h1m1 0h1m1 0h2m-32 1h1m5 0h1m1 0h5m4 0h5m1 0h2m3 0h3m-31 1h1m1 0h3m1 0h1m1 0h4m3 0h2m7 0h6m-30 1h1m1 0h3m1 0h1m1 0h2m2 0h2m1 0h1m1 0h5m1 0h1m1 0h1m2 0h5m-33 1h1m1 0h3m1 0h1m1 0h5m2 0h3m2 0h4m2 0h2m1 0h1m-30 1h1m5 0h1m2 0h1m5 0h1m2 0h1m1 0h3m2 0h1m2 0h3m-31 1h7m1 0h1m2 0h1m1 0h3m1 0h1m1 0h1m2 0h1m1 0h1m2 0h1m3 0h1"/></svg>
    <div>
      <b>¿Estás en el ordenador?</b>
      <span>Escanea este código con la cámara del móvil y la descarga empezará ahí.</span>
    </div>
  </div>
  </div>

  <div class="card trust" style="margin-top:14px;">
    <h2>🔒 Sobre la descarga</h2>
    <p>Todavía no estamos en Google Play (estamos en ello), así que la app se instala directamente con su archivo APK. Android te avisará porque no viene de la tienda — es lo normal en este caso:</p>
    <ol>
      <li>Toca <b>Descargar de todos modos</b> cuando Chrome pregunte.</li>
      <li>Abre el archivo y toca <b>Instalar</b>. Si Android pide permiso para "instalar apps desconocidas", actívalo solo para Chrome.</li>
      <li>Listo — la app se actualiza avisándote dentro.</li>
    </ol>
    <p style="margin-top:10px;">La descarga viene directa de nuestro servidor, siempre en su última versión.</p>
  </div>

  <a class="web" href="{APP}/">¿Sin Android? Úsala desde el navegador →</a>

  <footer>
    uroboros · <a href="{APP}/privacy">privacidad</a>·<a href="{APP}/terms">términos</a>
  </footer>
  </div>
 </div>
</div>
</body>
</html>""".replace("{APP}", _APP_URL)


@landing_router.get("/unete", response_class=HTMLResponse)
def invite_landing() -> HTMLResponse:
    """Public invite landing: OG preview card + download + trust notes."""
    # Warm the latest-APK cache so the download button redirects instantly.
    _warm_cache_async()
    # 1h cache: the page rarely changes and this keeps Cloudflare serving it
    # from the edge. Caveat: copy edits take up to an hour to show for anyone
    # who already viewed it — bust with a ?v= query while reviewing changes.
    return HTMLResponse(
        _LANDING_HTML,
        headers={"Cache-Control": "public, max-age=3600"},
    )
