"""Reportar un problema desde Ajustes."""
from typing import Literal

from fastapi import (
    APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile, status,
)
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.limiter import limiter
from app.models import BugReport, User
from app.services.bug_report import (
    MAX_SCREENSHOT_BYTES,
    InvalidScreenshot,
    device_from_user_agent,
    screenshot_to_jpeg,
)
from app.services.telegram_alerts import send_bug_report_alert

router = APIRouter(prefix="/feedback", tags=["feedback"])

MAX_MESSAGE = 2000


@router.post("", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/hour")
async def report_bug(
    request: Request,
    background: BackgroundTasks,
    message: str = Form(..., max_length=MAX_MESSAGE),
    # Lo rellena la app, no la persona. Obligatorio a propósito: un informe sin
    # versión es justo el que no sirve para nada.
    app_version: str = Form(..., max_length=16),
    platform: Literal["android", "ios", "pwa", "web"] = Form(...),
    locale: str = Form("", max_length=8),
    route: str = Form("", max_length=128),
    screenshot: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, int]:
    """Guarda el informe y avisa por Telegram con todo el contexto."""
    message = message.strip()
    if not message:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Cuéntanos qué ha pasado")

    image: bytes | None = None
    if screenshot is not None:
        raw = await screenshot.read(MAX_SCREENSHOT_BYTES + 1)
        if len(raw) > MAX_SCREENSHOT_BYTES:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "La captura pesa demasiado")
        if raw:
            try:
                image = screenshot_to_jpeg(raw)
            except InvalidScreenshot:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "No hemos podido leer esa imagen")

    # El dispositivo sale del User-Agent y no del formulario: lo manda el
    # navegador o el WebView solo, también en clientes que no sepan rellenarlo.
    device = device_from_user_agent(request.headers.get("user-agent", ""))

    report = BugReport(
        user_id=user.id,
        message=message,
        app_version=app_version.strip(),
        platform=platform,
        device=device,
        locale=locale.strip(),
        route=route.strip(),
        had_screenshot=image is not None,
        resolved=False,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    background.add_task(
        send_bug_report_alert,
        report.id,
        user.id,
        user.name,
        message,
        report.app_version,
        report.platform,
        report.device,
        report.locale,
        report.route,
        image,
    )
    return {"id": report.id}
