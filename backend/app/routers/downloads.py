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
from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter(prefix="/download", tags=["download"])

# Invite landing lives outside the /download prefix so the shared URL is short.
# Se monta sin el prefijo /api: es una página, no una API.
landing_router = APIRouter(tags=["download"])

# Ruta antigua (/api/unete), viva solo para redirigir los enlaces ya compartidos.
legacy_landing_router = APIRouter(tags=["download"])

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
<html lang="{L_LANG}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{L_TITLE}</title>
<meta property="og:type" content="website">
<meta property="og:site_name" content="uroboros">
<meta property="og:title" content="{L_OG_TITLE}">
<meta property="og:description" content="{L_OG_DESC}">
<meta property="og:image" content="{APP}/social-banner.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:url" content="{L_CANONICAL}">
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
      display: flex; flex-direction: column; justify-content: center; align-items: center;
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
    /* La placa del QR es el degradado del botón: en vez de un parche blanco,
       una pastilla de la marca. El contraste lo pone el módulo casi negro. */
    .qr svg {
      width: 128px; height: 128px; flex-shrink: 0;
      border-radius: 18px; padding: 9px;
      background: linear-gradient(180deg, oklch(88% 0.19 160), oklch(76% 0.2 168));
      box-shadow: 0 1px 0 rgba(255,255,255,0.35) inset,
                  0 14px 34px -10px oklch(75% 0.2 165 / 0.5);
    }
    .qr b { font-size: 0.85rem; display: block; margin-bottom: 4px; }
    .qr span { font-size: 0.78rem; color: rgba(255,255,255,0.55); line-height: 1.5; }
  }
  /* Dentro del panel de descarga el QR no necesita tarjeta: el propio panel
     ya lo separa del fondo. */
  @media (min-width: 900px) {
    .qr {
      background: none; border: 0; border-radius: 0; padding: 4px 0 0;
      margin-top: 18px; gap: 18px; backdrop-filter: none; -webkit-backdrop-filter: none;
    }
    /* Aquí hay sitio de sobra: el QR manda tanto como el botón. */
    .qr svg { width: 172px; height: 172px; border-radius: 22px; padding: 12px; }
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
    <div class="tag">{L_TAG}</div>
    <p class="pitch">{L_PITCH}</p>
  </div>

  <div class="card">
    <div class="feat"><div class="ico">🍽️</div><div><b>{L_F1_T}</b><span>{L_F1_D}</span></div></div>
    <div class="feat"><div class="ico">📊</div><div><b>{L_F2_T}</b><span>{L_F2_D}</span></div></div>
    <div class="feat"><div class="ico">🍳</div><div><b>{L_F3_T}</b><span>{L_F3_D}</span></div></div>
    <div class="feat"><div class="ico">⚔️</div><div><b>{L_F4_T}</b><span>{L_F4_D}</span></div></div>
  </div>
  </div>

  <div class="col">
  <div class="dl">
  <a class="btn" href="{APP}/api/download/latest-apk">{L_BTN}</a>

  <div class="qr">
    <svg viewBox="0 0 37 37" role="img" aria-label="{L_QR_ARIA}"><rect width="37" height="37" fill="none"/><path stroke="#04150f" d="M2 2.5h7m4 0h2m3 0h1m1 0h4m1 0h1m2 0h7m-33 1h1m5 0h1m3 0h2m3 0h2m1 0h1m2 0h2m1 0h1m1 0h1m5 0h1m-33 1h1m1 0h3m1 0h1m1 0h3m1 0h1m1 0h1m1 0h1m1 0h1m1 0h2m4 0h1m1 0h3m1 0h1m-33 1h1m1 0h3m1 0h1m1 0h1m1 0h1m7 0h2m2 0h1m3 0h1m1 0h3m1 0h1m-33 1h1m1 0h3m1 0h1m1 0h3m3 0h5m2 0h1m1 0h1m2 0h1m1 0h3m1 0h1m-33 1h1m5 0h1m1 0h1m1 0h2m5 0h1m2 0h2m4 0h1m5 0h1m-33 1h7m1 0h1m1 0h1m1 0h1m1 0h1m1 0h1m1 0h1m1 0h1m1 0h1m1 0h1m1 0h7m-25 1h1m2 0h1m2 0h1m1 0h1m2 0h1m1 0h2m1 0h1m-25 1h1m1 0h5m2 0h2m2 0h2m2 0h1m1 0h1m4 0h1m1 0h5m-28 1h1m1 0h1m1 0h2m3 0h3m2 0h1m1 0h3m1 0h1m2 0h2m1 0h2m1 0h1m-31 1h1m1 0h4m1 0h3m1 0h5m2 0h3m2 0h2m1 0h1m1 0h2m-32 1h2m1 0h1m3 0h1m1 0h1m1 0h3m1 0h4m1 0h3m1 0h3m1 0h5m-33 1h1m5 0h1m2 0h4m1 0h1m1 0h1m5 0h4m1 0h3m1 0h2m-33 1h2m2 0h1m2 0h4m4 0h1m2 0h3m1 0h2m2 0h1m2 0h4m-31 1h1m1 0h1m1 0h1m2 0h1m1 0h3m1 0h4m3 0h1m1 0h4m2 0h2m-32 1h1m1 0h1m6 0h3m1 0h3m2 0h1m2 0h1m3 0h2m1 0h3m-27 1h1m1 0h7m1 0h2m1 0h1m4 0h4m1 0h2m3 0h1m-32 1h1m3 0h1m4 0h1m1 0h1m3 0h1m1 0h4m1 0h1m2 0h2m1 0h2m1 0h1m-33 1h1m3 0h1m1 0h1m1 0h2m5 0h2m1 0h1m8 0h2m1 0h1m-31 1h1m4 0h1m4 0h1m2 0h1m2 0h1m2 0h1m1 0h2m2 0h1m1 0h5m-32 1h2m1 0h1m2 0h1m2 0h1m1 0h2m1 0h1m3 0h1m1 0h1m1 0h4m1 0h3m2 0h1m-33 1h2m2 0h2m1 0h1m6 0h3m2 0h2m1 0h2m2 0h1m2 0h1m2 0h1m-33 1h1m1 0h2m1 0h7m2 0h1m5 0h3m4 0h3m1 0h1m-32 1h1m1 0h2m1 0h1m1 0h3m2 0h3m1 0h1m4 0h3m1 0h2m1 0h3m-31 1h1m2 0h6m4 0h1m3 0h2m1 0h1m1 0h8m1 0h1m-24 1h1m2 0h3m2 0h7m1 0h1m3 0h1m1 0h1m1 0h1m-33 1h7m2 0h1m1 0h1m2 0h4m2 0h5m1 0h1m1 0h1m1 0h2m-32 1h1m5 0h1m1 0h5m4 0h5m1 0h2m3 0h3m-31 1h1m1 0h3m1 0h1m1 0h4m3 0h2m7 0h6m-30 1h1m1 0h3m1 0h1m1 0h2m2 0h2m1 0h1m1 0h5m1 0h1m1 0h1m2 0h5m-33 1h1m1 0h3m1 0h1m1 0h5m2 0h3m2 0h4m2 0h2m1 0h1m-30 1h1m5 0h1m2 0h1m5 0h1m2 0h1m1 0h3m2 0h1m2 0h3m-31 1h7m1 0h1m2 0h1m1 0h3m1 0h1m1 0h1m2 0h1m1 0h1m2 0h1m3 0h1"/></svg>
    <div>
      <b>{L_QR_T}</b>
      <span>{L_QR_D}</span>
    </div>
  </div>
  </div>

  <div class="card trust" style="margin-top:14px;">
    <h2>{L_TRUST_T}</h2>
    <p>{L_TRUST_INTRO}</p>
    <ol>
      <li>{L_STEP1}</li>
      <li>{L_STEP2}</li>
      <li>{L_STEP3}</li>
    </ol>
    <p style="margin-top:10px;">{L_TRUST_OUTRO}</p>
  </div>

  <a class="web" href="{APP}/">{L_WEB}</a>

  <footer>
    uroboros · <a href="{APP}/privacy">{L_PRIVACY}</a>·<a href="{APP}/terms">{L_TERMS}</a>
  </footer>
  </div>
 </div>
</div>
</body>
</html>""".replace("{APP}", _APP_URL)


# Copy de la landing en los tres idiomas. Es HTML servido por el servidor, así
# que no hay localStorage donde mirar: el idioma sale de Accept-Language.
# El portugués es europeo (pt-PT), igual que el diccionario del frontend.
_LANDING_COPY: dict[str, dict[str, str]] = {
    "es": {
        "L_LANG": "es",
        "L_TITLE": "Únete a uroboros 🐍",
        "L_OG_TITLE": "uroboros — come mejor, en pareja",
        "L_OG_DESC": "La app para llevar la comida con tu pareja: registra una comida para los dos a la vez, compite en constancia y comparte la lista de la compra.",
        "L_TAG": "Come mejor. Juntos.",
        "L_PITCH": "Te han invitado a la app para llevar la comida <b>en pareja</b>: una sola vez, para los dos.",
        "L_F1_T": "Registro a dos",
        "L_F1_D": "Apunta una comida y aparece en el diario de ambos, con sus macros calculados.",
        "L_F2_T": "Objetivos y progreso",
        "L_F2_D": "Calorías, proteína, agua, peso y medidas — con historial y tendencias.",
        "L_F3_T": "Recetas e inventario compartido",
        "L_F3_D": "La despensa y la lista de la compra, comunes de verdad.",
        "L_F4_T": "Duelo semanal",
        "L_F4_D": "Un pique sano: quién cumple más sus propios objetivos cada semana.",
        "L_BTN": "📥 Descargar para Android",
        "L_QR_ARIA": "Código QR para descargar la app en el móvil",
        "L_QR_T": "¿Estás en el ordenador?",
        "L_QR_D": "Escanea este código con la cámara del móvil y la descarga empezará ahí.",
        "L_TRUST_T": "🔒 Sobre la descarga",
        "L_TRUST_INTRO": "Todavía no estamos en Google Play (estamos en ello), así que la app se instala directamente con su archivo APK. Android te avisará porque no viene de la tienda — es lo normal en este caso:",
        "L_STEP1": "Toca <b>Descargar de todos modos</b> cuando Chrome pregunte.",
        "L_STEP2": "Abre el archivo y toca <b>Instalar</b>. Si Android pide permiso para \"instalar apps desconocidas\", actívalo solo para Chrome.",
        "L_STEP3": "Listo — la app se actualiza avisándote dentro.",
        "L_TRUST_OUTRO": "La descarga viene directa de nuestro servidor, siempre en su última versión.",
        "L_WEB": "¿Sin Android? Úsala desde el navegador →",
        "L_PRIVACY": "privacidad",
        "L_TERMS": "términos",
    },
    "en": {
        "L_LANG": "en",
        "L_TITLE": "Join uroboros 🐍",
        "L_OG_TITLE": "uroboros — eat better, together",
        "L_OG_DESC": "The app for tracking food with your partner: log one meal for both of you at once, compete on consistency and share the shopping list.",
        "L_TAG": "Eat better. Together.",
        "L_PITCH": "You've been invited to the app for tracking food <b>as a couple</b>: log it once, for both of you.",
        "L_F1_T": "Log once, for two",
        "L_F1_D": "Log a meal and it shows up in both diaries, with the macros worked out.",
        "L_F2_T": "Goals and progress",
        "L_F2_D": "Calories, protein, water, weight and measurements — with history and trends.",
        "L_F3_T": "Shared recipes and pantry",
        "L_F3_D": "The pantry and the shopping list, genuinely shared.",
        "L_F4_T": "Weekly duel",
        "L_F4_D": "A friendly rivalry: who sticks to their own goals best each week.",
        "L_BTN": "📥 Download for Android",
        "L_QR_ARIA": "QR code to download the app on your phone",
        "L_QR_T": "On your computer?",
        "L_QR_D": "Scan this code with your phone's camera and the download starts there.",
        "L_TRUST_T": "🔒 About the download",
        "L_TRUST_INTRO": "We're not on Google Play yet (we're working on it), so the app installs directly from its APK file. Android will warn you because it isn't from the store — that's normal here:",
        "L_STEP1": "Tap <b>Download anyway</b> when Chrome asks.",
        "L_STEP2": "Open the file and tap <b>Install</b>. If Android asks for permission to \"install unknown apps\", turn it on for Chrome only.",
        "L_STEP3": "Done — the app tells you from the inside when there's an update.",
        "L_TRUST_OUTRO": "The download comes straight from our server, always the latest version.",
        "L_WEB": "No Android? Use it in your browser →",
        "L_PRIVACY": "privacy",
        "L_TERMS": "terms",
    },
    "pt": {
        "L_LANG": "pt",
        "L_TITLE": "Junta-te ao uroboros 🐍",
        "L_OG_TITLE": "uroboros — comer melhor, a dois",
        "L_OG_DESC": "A app para gerir a comida com o teu par: regista uma refeição para os dois de uma vez, compete na constância e partilha a lista de compras.",
        "L_TAG": "Comer melhor. Juntos.",
        "L_PITCH": "Convidaram-te para a app de gerir a comida <b>a dois</b>: registas uma vez, conta para ambos.",
        "L_F1_T": "Registo a dois",
        "L_F1_D": "Regista uma refeição e aparece no diário de ambos, com os macros já calculados.",
        "L_F2_T": "Objetivos e progresso",
        "L_F2_D": "Calorias, proteína, água, peso e medidas — com histórico e tendências.",
        "L_F3_T": "Receitas e despensa partilhadas",
        "L_F3_D": "A despensa e a lista de compras, partilhadas a sério.",
        "L_F4_T": "Duelo semanal",
        "L_F4_D": "Uma piadinha saudável: quem cumpre melhor os seus próprios objetivos cada semana.",
        "L_BTN": "📥 Descarregar para Android",
        "L_QR_ARIA": "Código QR para descarregar a app no telemóvel",
        "L_QR_T": "Estás no computador?",
        "L_QR_D": "Lê este código com a câmara do telemóvel e a transferência começa aí.",
        "L_TRUST_T": "🔒 Sobre a transferência",
        "L_TRUST_INTRO": "Ainda não estamos no Google Play (estamos a tratar disso), por isso a app instala-se diretamente a partir do ficheiro APK. O Android vai avisar-te porque não vem da loja — é normal neste caso:",
        "L_STEP1": "Toca em <b>Transferir mesmo assim</b> quando o Chrome perguntar.",
        "L_STEP2": "Abre o ficheiro e toca em <b>Instalar</b>. Se o Android pedir permissão para \"instalar apps desconhecidas\", ativa-a só para o Chrome.",
        "L_STEP3": "Pronto — a app avisa-te por dentro quando houver atualização.",
        "L_TRUST_OUTRO": "A transferência vem diretamente do nosso servidor, sempre na versão mais recente.",
        "L_WEB": "Sem Android? Usa-a no navegador →",
        "L_PRIVACY": "privacidade",
        "L_TERMS": "termos",
    },
}


def _pick_language(accept_language: str | None, lang: str | None = None) -> str:
    """Idioma de la landing: ?lang= manda sobre Accept-Language, y es de reserva.

    El parámetro de query existe por dos motivos prácticos:
      - Cloudflare solo honra `Vary` para Accept-Encoding salvo que configures
        una Cache Rule; la query string, en cambio, va en la clave de caché
        siempre. Sin esto el edge puede repartir un único idioma a todos.
      - Los crawlers de WhatsApp y compañía no mandan Accept-Language, así que
        la tarjeta del enlace saldría siempre en español. Con ?lang=, quien
        comparte propaga su idioma y cada variante se cachea por separado.

    Lo demás es deliberadamente simple: recorre las preferencias en orden y se
    queda con la primera que sepamos servir. No pesa los factores q= porque los
    navegadores ya las mandan ordenadas de mayor a menor.
    """
    if lang and lang.split("-")[0].lower() in _LANDING_COPY:
        return lang.split("-")[0].lower()
    if not accept_language:
        return "es"
    for part in accept_language.split(","):
        tag = part.split(";")[0].strip().lower()
        primary = tag.split("-")[0]
        if primary in _LANDING_COPY:
            return primary
    return "es"


def _render_landing(lang: str, canonical: str) -> str:
    html = _LANDING_HTML.replace("{L_CANONICAL}", canonical)
    for key, value in _LANDING_COPY[lang].items():
        html = html.replace("{" + key + "}", value)
    return html


@landing_router.get("/unete", response_class=HTMLResponse)
def invite_landing(
    accept_language: str | None = Header(default=None),
    lang: str | None = None,
) -> HTMLResponse:
    """Public invite landing: OG preview card + download + trust notes.

    Se sirve en es/en/pt. Aquí no hay sesión ni localStorage — quien abre este
    enlace todavía no tiene la app —, así que el idioma sale de ?lang= o, en su
    defecto, de Accept-Language.
    """
    # Warm the latest-APK cache so the download button redirects instantly.
    _warm_cache_async()
    resolved = _pick_language(accept_language, lang)
    # La canónica refleja lo que se pidió: si el enlace traía ?lang=, se queda,
    # que es lo que hace que cada idioma tenga su propia tarjeta cacheada.
    canonical = f"{_APP_URL}/unete?lang={resolved}" if lang else f"{_APP_URL}/unete"
    # 1h cache: the page rarely changes and this keeps Cloudflare serving it
    # from the edge. Caveat: copy edits take up to an hour to show for anyone
    # who already viewed it — bust with a ?v= query while reviewing changes.
    # `Vary` es correcto en HTTP y lo respetan navegadores y cachés intermedias,
    # pero Cloudflare solo lo honra para Accept-Encoding salvo Cache Rule: el
    # reparto de idiomas de verdad lo asegura ?lang=, que sí va en la clave.
    return HTMLResponse(
        _render_landing(resolved, canonical),
        headers={
            "Cache-Control": "public, max-age=3600",
            "Vary": "Accept-Language",
        },
    )


@legacy_landing_router.get("/unete", include_in_schema=False)
def invite_landing_legacy(request: Request) -> RedirectResponse:
    """La landing vivía en /api/unete, y sigue habiendo enlaces por ahí.

    Cada WhatsApp ya enviado apunta aquí para siempre, así que esta ruta no se
    borra: redirige permanente y conserva la query (el ?lang=).
    """
    qs = request.url.query
    return RedirectResponse(f"/unete?{qs}" if qs else "/unete", status_code=301)
