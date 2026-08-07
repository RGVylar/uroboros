"""Puerta de features sin publicar (`User.feature_flags` + `require_feature_flag`).

Lo que se prueba aquí no es la columna, es la promesa: **esconder el botón en el
frontend no protege nada**, así que la puerta del backend tiene que cortar de
verdad y tiene que hacerlo con 404, no con 403 — una feature que aún no existe
para ti no debería asomar que existe.
"""
from fastapi import APIRouter, Depends

from app.deps import require_feature_flag
from app.main import app
from app.models import User

from conftest import API, auth

FLAG = "receipt_scan"

# Endpoint de mentira montado sobre la dependencia real. Así el test sigue
# valiendo cuando `receipt_scan` deje de existir, porque lo que se prueba es la
# puerta y no la feature que hoy esté detrás.
_router = APIRouter()


@_router.get("/__test_flagged__")
def _flagged(user: User = Depends(require_feature_flag(FLAG))) -> dict:
    return {"ok": True, "user_id": user.id}


app.include_router(_router, prefix=API)


def test_sin_flag_responde_404(client, make_user):
    """Sin el flag no hay pista de que la ruta exista."""
    user = make_user("Ana")

    r = client.get(f"{API}/__test_flagged__", headers=auth(user))

    assert r.status_code == 404


def test_con_el_flag_pasa(client, db, make_user):
    user = make_user("Bea")
    user.feature_flags = [FLAG]
    db.commit()

    r = client.get(f"{API}/__test_flagged__", headers=auth(user))

    assert r.status_code == 200
    assert r.json()["user_id"] == user.id


def test_otro_flag_no_abre_la_puerta(client, db, make_user):
    """Tener flags no es tener *este* flag."""
    user = make_user("Cris")
    user.feature_flags = ["otra_cosa"]
    db.commit()

    r = client.get(f"{API}/__test_flagged__", headers=auth(user))

    assert r.status_code == 404


def test_sin_token_sigue_siendo_401(client):
    """La puerta del flag no debe tragarse el fallo de autenticación."""
    r = client.get(f"{API}/__test_flagged__")

    assert r.status_code == 401


def test_has_flag_tolera_null(make_user):
    """La columna es nullable (null = ninguna), así que nadie debe reventar."""
    user = make_user("Dani")

    assert user.feature_flags is None
    assert user.has_flag(FLAG) is False


def test_auth_me_expone_los_flags_como_lista(client, db, make_user):
    """Fuera siempre es una lista: el frontend no distingue null de []."""
    user = make_user("Eva")

    r = client.get(f"{API}/auth/me", headers=auth(user))
    assert r.status_code == 200
    assert r.json()["feature_flags"] == []

    user.feature_flags = [FLAG]
    db.commit()

    r = client.get(f"{API}/auth/me", headers=auth(user))
    assert r.json()["feature_flags"] == [FLAG]
