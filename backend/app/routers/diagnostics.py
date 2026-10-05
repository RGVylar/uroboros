"""Diagnóstico de lo que solo existe en la APK (pasos, recordatorios locales).

No se guarda: se reenvía al chat de admin de Telegram y ya. La app solo lo
manda cuando el resultado cambia, así que cada mensaje es un cambio de estado.
"""
import json
from typing import Any, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.deps import get_current_user
from app.limiter import limiter
from app.models import User
from app.services.bug_report import device_from_user_agent
from app.services.telegram_alerts import send_diagnostic_alert

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])

# El detalle son unos pocos campos técnicos; más que esto es un cliente roto.
MAX_DATA_BYTES = 4000


class DiagnosticIn(BaseModel):
    kind: Literal["health", "notifications"]
    outcome: str = Field(..., min_length=1, max_length=32)
    # Lo último que mandó este móvil; None la primera vez.
    previous: str | None = Field(None, max_length=32)
    app_version: str = Field("", max_length=16)
    platform: Literal["android", "ios", "pwa", "web"]
    data: dict[str, Any] = Field(default_factory=dict)


@router.post("", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/hour")
def report_diagnostic(
    request: Request,
    body: DiagnosticIn,
    background: BackgroundTasks,
    user: User = Depends(get_current_user),
) -> None:
    if len(json.dumps(body.data, default=str)) > MAX_DATA_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Diagnóstico demasiado grande")
    background.add_task(
        send_diagnostic_alert,
        user.id,
        user.name,
        body.kind,
        body.outcome.strip(),
        body.previous,
        body.app_version.strip(),
        body.platform,
        # El dispositivo sale del User-Agent, como en los informes de problemas.
        device_from_user_agent(request.headers.get("user-agent", "")),
        body.data,
    )
