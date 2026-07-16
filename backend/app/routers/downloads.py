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
    name = _latest_apk_name()
    if not name:
        # Couldn't resolve a specific file — send them to the folder instead.
        return RedirectResponse(_FOLDER_FALLBACK, status_code=302)
    download_url = f"{_SHARE_URL}/download?path=%2F&files={quote(name)}"
    return RedirectResponse(download_url, status_code=302)


_APP_URL = "https://comida.mugrelore.com"

# The invite message links here instead of at the raw APK: messaging apps'
# crawlers need an HTML page with Open Graph tags to render a preview card
# (a 302 to a binary shows a bare domain), and a human gets a clear download
# button instead of a surprise APK. This page is also where a future invite
# deep-link would plug in (detect the installed app, open the add-friend modal).
_LANDING_HTML = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Únete a uroboros 🐍</title>
<meta property="og:type" content="website">
<meta property="og:site_name" content="uroboros">
<meta property="og:title" content="uroboros — come mejor, en pareja">
<meta property="og:description" content="La app para llevar la comida con tu pareja: registra una comida para los dos a la vez, compite en constancia y comparte la lista de la compra.">
<meta property="og:image" content="{_APP_URL}/social-banner.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:url" content="{_APP_URL}/api/unete">
<meta name="twitter:card" content="summary_large_image">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #06070a; color: #eef1f5;
    font-family: 'Segoe UI', system-ui, sans-serif;
    min-height: 100dvh; display: flex; align-items: center; justify-content: center;
    padding: 24px; text-align: center;
  }}
  .card {{
    background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.09);
    border-radius: 24px; padding: 40px 28px; max-width: 400px; width: 100%;
  }}
  img.logo {{ width: 110px; height: 110px; margin-bottom: 14px; }}
  h1 {{ font-size: 2rem; letter-spacing: -0.03em; }}
  .tag {{ color: oklch(85% 0.17 160); font-weight: 600; margin-top: 6px; }}
  p.desc {{ color: rgba(255,255,255,0.55); font-size: 0.9rem; line-height: 1.5; margin: 16px 0 28px; }}
  a.btn {{
    display: block; padding: 15px; border-radius: 14px; text-decoration: none;
    background: linear-gradient(180deg, oklch(88% 0.19 160), oklch(72% 0.2 170));
    color: #041010; font-weight: 800; font-size: 1rem;
  }}
  a.web {{
    display: block; margin-top: 14px; color: rgba(255,255,255,0.55);
    font-size: 0.85rem; text-decoration: none;
  }}
  a.web:hover {{ color: #eef1f5; }}
</style>
</head>
<body>
  <div class="card">
    <img class="logo" src="{_APP_URL}/logo.png" alt="uroboros">
    <h1>uroboros</h1>
    <div class="tag">Come mejor. Juntos.</div>
    <p class="desc">Te han invitado a llevar la comida en pareja: registra una comida para los dos a la vez, con macros, recetas e inventario compartido.</p>
    <a class="btn" href="{_APP_URL}/api/download/latest-apk">📥 Descargar para Android</a>
    <a class="web" href="{_APP_URL}/">o úsala desde el navegador →</a>
  </div>
</body>
</html>"""


@landing_router.get("/unete", response_class=HTMLResponse)
def invite_landing() -> HTMLResponse:
    """Public invite landing: OG preview card + download button."""
    return HTMLResponse(_LANDING_HTML)
