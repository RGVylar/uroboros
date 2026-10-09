"""Resumen semanal para Telegram: recuentos sin datos personales."""
from datetime import datetime, timedelta, timezone

from app.models.bug_report import BugReport
from app.models.diary import DiaryEntry
from app.services.weekly_stats import build_weekly_summary


def _log(db, user, product, when):
    db.add(DiaryEntry(user_id=user.id, product_id=product.id, grams=100, calories=100,
                      protein=10, carbs=10, fat=1, consumed_at=when))


def test_weekly_summary_counts_and_versions(db, make_user):
    now = datetime.now(timezone.utc)
    ana, bea, cris, dani = make_user("Ana"), make_user("Bea"), make_user("Cris"), make_user("Dani")
    ana.app_version, ana.platform, ana.last_seen_at = "1.29", "ios", now
    dani.app_version, dani.platform, dani.last_seen_at = "1.29", "web", now
    bea.app_version, bea.platform, bea.last_seen_at = "1.27", "android", now - timedelta(days=3)
    cris.last_seen_at = None  # nunca ha abierto la app desde que se guarda
    db.commit()

    text = build_weekly_summary(db, now=now)
    assert "Usuarios: *4*" in text
    assert "Al día (1.29): 2 · desactualizados: 1" in text
    assert "1.27 · Android: 1" in text
    assert "1.29 ·" not in text  # quien está al día no se desglosa
    assert "sin datos: 1" in text
    # Nada que identifique a nadie.
    assert "@example.com" not in text and "Ana" not in text


def test_weekly_summary_retention_and_consistency(db, make_user, make_product):
    now = datetime.now(timezone.utc)
    p = make_product()
    ana, bea, cris, dani = make_user("Ana"), make_user("Bea"), make_user("Cris"), make_user("Dani")
    for u in (ana, bea, cris, dani):
        u.created_at = now - timedelta(days=60)
    # Ana: 5 días esta semana y también la anterior.
    for d in range(5):
        _log(db, ana, p, now - timedelta(days=d, hours=1))
    _log(db, ana, p, now - timedelta(days=9))
    # Bea: solo la semana anterior → dejó de apuntar.
    _log(db, bea, p, now - timedelta(days=10))
    # Cris: hace un mes y esta semana → volvió.
    _log(db, cris, p, now - timedelta(days=20))
    _log(db, cris, p, now - timedelta(days=1))
    # Dani nunca ha apuntado.
    db.add(BugReport(user_id=ana.id, message="x", created_at=now - timedelta(days=1)))
    db.add(BugReport(user_id=ana.id, message="y", created_at=now - timedelta(days=20), resolved=True))
    db.commit()

    text = build_weekly_summary(db, now=now)
    assert "Activos: *2* (sem. anterior 2, =)" in text
    assert "Dejaron de apuntar: 1 · Volvieron: 1" in text
    assert "3,0/7 días de media · 1 con 5+ días" in text
    assert "Entradas: 6" in text
    assert "Nunca han apuntado (cuenta de +7 días): 1" in text
    assert "Bugs: 1 nuevos · 1 sin resolver" in text
