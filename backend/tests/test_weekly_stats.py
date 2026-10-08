"""Resumen semanal para Telegram: recuentos sin datos personales."""
from datetime import datetime, timedelta, timezone

from app.services.weekly_stats import build_weekly_summary


def test_weekly_summary_counts_and_versions(db, make_user):
    now = datetime.now(timezone.utc)
    ana, bea, cris = make_user("Ana"), make_user("Bea"), make_user("Cris")
    ana.app_version, ana.platform, ana.last_seen_at = "1.29", "ios", now
    bea.app_version, bea.platform, bea.last_seen_at = "1.27", "android", now - timedelta(days=3)
    cris.last_seen_at = None  # nunca ha abierto la app desde que se guarda
    db.commit()

    text = build_weekly_summary(db, now=now)
    assert "Usuarios: *3*" in text
    assert "1.29 · iOS: 1" in text
    assert "1.27 · Android: 1" in text
    assert "sin datos: 1" in text
    # La versión más nueva va primero.
    assert text.index("1.29") < text.index("1.27")
    # Nada que identifique a nadie.
    assert "@example.com" not in text and "Ana" not in text
