"""El endpoint de changelog no debe caerse por un tipo de item heredado/desconocido.

Regresión: la nota 1.6 usaba type "arreglo" (fuera del Literal nuevo|mejora|fix);
al subir APP_VERSION a >=1.6 entraba en la respuesta y ReleaseNoteItem daba un 500.
Ahora el router normaliza el tipo.
"""
from conftest import API, auth
from app.models.release_note import ReleaseNote


def _seed(db, **kw):
    db.add(ReleaseNote(**kw))
    db.commit()


def test_release_notes_tolerates_legacy_arreglo_type(client, db, make_user):
    user = make_user("Ruben")
    _seed(db, version="1.6", title="Pareja y amigos", importance="major", published=True,
          items=[
              {"type": "nuevo", "title": "Algo", "desc": "d"},
              {"type": "arreglo", "title": "La despensa ya no se descuadra", "desc": "d"},
          ])

    r = client.get(f"{API}/release-notes?current=1.7&seen=", headers=auth(user))
    assert r.status_code == 200, r.text

    note = next(n for n in r.json()["news"] if n["version"] == "1.6")
    types = [it["type"] for it in note["items"]]
    assert types == ["nuevo", "fix"], "'arreglo' debe normalizarse a 'fix'"


def test_release_notes_tolerates_unknown_type(client, db, make_user):
    user = make_user("Silva")
    _seed(db, version="1.6", title="x", importance="major", published=True,
          items=[{"type": "loquesea", "title": "t", "desc": "d"}])

    r = client.get(f"{API}/release-notes?current=1.7&seen=", headers=auth(user))
    assert r.status_code == 200, r.text
    note = next(n for n in r.json()["news"] if n["version"] == "1.6")
    assert note["items"][0]["type"] in {"nuevo", "mejora", "fix"}
