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
from fastapi.responses import RedirectResponse

router = APIRouter(prefix="/download", tags=["download"])

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
