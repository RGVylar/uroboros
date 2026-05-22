"""Full data export as a ZIP archive containing one CSV per data type."""
import csv
import io
import zipfile
from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.deps import get_current_user
from app.models.body_measurement import BodyMeasurementLog
from app.models.creatine import CreatineLog
from app.models.diary import DiaryEntry
from app.models.exercise import ExerciseSession, ExerciseSessionEntry
from app.models.mood import MoodEntry
from app.models.supplement import SupplementLog, UserSupplement
from app.models.user import User
from app.models.water import WaterLog
from app.models.weight import WeightLog

router = APIRouter(prefix="/export", tags=["export"])

_LEVEL_LABEL = {1: "bajo", 2: "normal", 3: "bueno"}


def _csv_bytes(rows: list, headers: list[str]) -> bytes:
    """Return UTF-8-BOM encoded CSV bytes (Excel-friendly)."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(headers)
    w.writerows(rows)
    return buf.getvalue().encode("utf-8-sig")


def _dt_filter(stmt, col, date_from, date_to):
    """Apply datetime range filter to a statement column."""
    if date_from:
        stmt = stmt.where(col >= datetime.combine(date_from, time.min, tzinfo=timezone.utc))
    if date_to:
        stmt = stmt.where(col <= datetime.combine(date_to, time.max, tzinfo=timezone.utc))
    return stmt


def _date_filter(stmt, col, date_from, date_to):
    """Apply date (not datetime) range filter."""
    if date_from:
        stmt = stmt.where(col >= date_from)
    if date_to:
        stmt = stmt.where(col <= date_to)
    return stmt


@router.get("/full.zip")
def export_full_zip(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Export all user data as a ZIP file with one CSV per data type."""
    uid = user.id
    files: dict[str, bytes] = {}

    # ── diario.csv ────────────────────────────────────────────────────────────
    stmt = (
        select(DiaryEntry)
        .where(DiaryEntry.user_id == uid)
        .options(joinedload(DiaryEntry.product))
        .order_by(DiaryEntry.consumed_at)
    )
    stmt = _dt_filter(stmt, DiaryEntry.consumed_at, date_from, date_to)
    diary_rows = []
    for e in db.scalars(stmt).unique():
        dt = e.consumed_at
        diary_rows.append([
            dt.strftime("%Y-%m-%d"),
            dt.strftime("%H:%M"),
            e.meal_type.value if e.meal_type else "",
            e.product.name if e.product else f"#{e.product_id}",
            e.product.brand if e.product and e.product.brand else "",
            round(e.grams, 1),
            round(e.calories, 1),
            round(e.protein, 1),
            round(e.carbs, 1),
            round(e.fat, 1),
        ])
    files["diario.csv"] = _csv_bytes(
        diary_rows,
        ["fecha", "hora", "comida", "producto", "marca", "gramos", "kcal", "proteina_g", "carbos_g", "grasa_g"],
    )

    # ── agua.csv ──────────────────────────────────────────────────────────────
    stmt = select(WaterLog).where(WaterLog.user_id == uid).order_by(WaterLog.logged_date)
    stmt = _date_filter(stmt, WaterLog.logged_date, date_from, date_to)
    agua_rows = [[w.logged_date.isoformat(), int(w.ml)] for w in db.scalars(stmt)]
    files["agua.csv"] = _csv_bytes(agua_rows, ["fecha", "ml"])

    # ── peso.csv ──────────────────────────────────────────────────────────────
    stmt = select(WeightLog).where(WeightLog.user_id == uid).order_by(WeightLog.logged_at)
    stmt = _dt_filter(stmt, WeightLog.logged_at, date_from, date_to)
    peso_rows = [
        [w.logged_at.strftime("%Y-%m-%d"), w.logged_at.strftime("%H:%M"), round(w.weight, 2)]
        for w in db.scalars(stmt)
    ]
    files["peso.csv"] = _csv_bytes(peso_rows, ["fecha", "hora", "kg"])

    # ── medidas.csv ───────────────────────────────────────────────────────────
    stmt = (
        select(BodyMeasurementLog)
        .where(BodyMeasurementLog.user_id == uid)
        .order_by(BodyMeasurementLog.logged_at)
    )
    stmt = _dt_filter(stmt, BodyMeasurementLog.logged_at, date_from, date_to)
    meas_list = list(db.scalars(stmt))
    # Collect all measurement keys to build dynamic columns
    all_keys: list[str] = []
    for m in meas_list:
        for k in (m.measurements or {}).keys():
            if k not in all_keys:
                all_keys.append(k)
    meas_rows = []
    for m in meas_list:
        row = [m.logged_at.strftime("%Y-%m-%d"), m.logged_at.strftime("%H:%M")]
        row += [m.measurements.get(k, "") for k in all_keys]
        meas_rows.append(row)
    files["medidas.csv"] = _csv_bytes(meas_rows, ["fecha", "hora"] + all_keys)

    # ── ejercicio.csv ─────────────────────────────────────────────────────────
    stmt = (
        select(ExerciseSession)
        .where(ExerciseSession.user_id == uid)
        .options(
            joinedload(ExerciseSession.entries).joinedload(ExerciseSessionEntry.exercise)
        )
        .order_by(ExerciseSession.session_date)
    )
    stmt = _date_filter(stmt, ExerciseSession.session_date, date_from, date_to)
    ejercicio_rows = []
    for session in db.scalars(stmt).unique():
        for entry in session.entries:
            ejercicio_rows.append([
                session.session_date.isoformat(),
                entry.exercise.name if entry.exercise else f"#{entry.exercise_id}",
                round(entry.quantity, 1),
                entry.exercise.unit if entry.exercise else "",
                round(entry.calories, 1),
                round(session.total_calories, 1),
            ])
    files["ejercicio.csv"] = _csv_bytes(
        ejercicio_rows,
        ["fecha", "ejercicio", "cantidad", "unidad", "kcal_quemadas", "total_dia_kcal"],
    )

    # ── suplementos.csv ───────────────────────────────────────────────────────
    stmt = (
        select(SupplementLog.logged_date, UserSupplement.name)
        .join(UserSupplement, SupplementLog.supplement_id == UserSupplement.id)
        .where(SupplementLog.user_id == uid)
        .order_by(SupplementLog.logged_date, UserSupplement.name)
    )
    stmt = _date_filter(stmt, SupplementLog.logged_date, date_from, date_to)
    supp_rows = [[row.logged_date.isoformat(), row.name] for row in db.execute(stmt)]
    files["suplementos.csv"] = _csv_bytes(supp_rows, ["fecha", "suplemento"])

    # ── creatina.csv ──────────────────────────────────────────────────────────
    stmt = (
        select(CreatineLog)
        .where(CreatineLog.user_id == uid)
        .order_by(CreatineLog.logged_date)
    )
    stmt = _date_filter(stmt, CreatineLog.logged_date, date_from, date_to)
    creatine_rows = [[c.logged_date.isoformat()] for c in db.scalars(stmt)]
    files["creatina.csv"] = _csv_bytes(creatine_rows, ["fecha"])

    # ── mood.csv ──────────────────────────────────────────────────────────────
    stmt = (
        select(MoodEntry)
        .where(MoodEntry.user_id == uid)
        .order_by(MoodEntry.entry_date)
    )
    stmt = _date_filter(stmt, MoodEntry.entry_date, date_from, date_to)
    mood_rows = [
        [
            m.entry_date.isoformat(),
            _LEVEL_LABEL.get(m.energy, "") if m.energy else "",
            _LEVEL_LABEL.get(m.digestion, "") if m.digestion else "",
            _LEVEL_LABEL.get(m.mood, "") if m.mood else "",
            m.notes or "",
        ]
        for m in db.scalars(stmt)
    ]
    files["mood.csv"] = _csv_bytes(mood_rows, ["fecha", "energia", "digestion", "animo", "notas"])

    # ── Build ZIP ─────────────────────────────────────────────────────────────
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    zip_buf.seek(0)

    suffix = ""
    if date_from:
        suffix += f"_{date_from}"
    if date_to:
        suffix += f"_{date_to}"
    filename = f"uroboros_export{suffix}.zip"

    return StreamingResponse(
        iter([zip_buf.getvalue()]),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
