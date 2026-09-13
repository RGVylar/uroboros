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


def test_release_notes_resolves_translated_dict_by_lang(client, db, make_user):
    user = make_user("Amaia")
    _seed(db, version="1.10", title={"es": "Título", "en": "Title", "pt": "Título PT"},
          importance="minor", published=True,
          items=[{
              "type": "nuevo",
              "title": {"es": "Nuevo ES", "en": "New EN", "pt": "Novo PT"},
              "desc": {"es": "Desc ES", "en": "Desc EN", "pt": "Desc PT"},
          }])

    r = client.get(f"{API}/release-notes?current=1.10&seen=&lang=en", headers=auth(user))
    assert r.status_code == 200, r.text
    note = next(n for n in r.json()["news"] if n["version"] == "1.10")
    assert note["title"] == "Title"
    assert note["items"][0]["title"] == "New EN"
    assert note["items"][0]["desc"] == "Desc EN"


def test_release_notes_falls_back_to_spanish_when_translation_missing(client, db, make_user):
    user = make_user("Bea")
    # Old-shape row: plain strings, no translations at all (pre-1.11 note).
    _seed(db, version="1.9", title="Solo en español", importance="major", published=True,
          items=[{"type": "mejora", "title": "Título ES", "desc": "Descripción ES"}])

    r = client.get(f"{API}/release-notes?current=1.9&seen=&lang=en", headers=auth(user))
    assert r.status_code == 200, r.text
    note = next(n for n in r.json()["news"] if n["version"] == "1.9")
    assert note["title"] == "Solo en español"
    assert note["items"][0]["title"] == "Título ES"


def test_release_notes_rejects_unknown_lang(client, db, make_user):
    user = make_user("Carlos")
    _seed(db, version="1.10", title={"es": "Título", "en": "Title"}, importance="minor",
          published=True, items=[])

    r = client.get(f"{API}/release-notes?current=1.10&seen=&lang=fr", headers=auth(user))
    assert r.status_code == 200, r.text
    note = next(n for n in r.json()["news"] if n["version"] == "1.10")
    assert note["title"] == "Título", "un lang desconocido debe caer a español, no tumbar el endpoint"


def test_latest_is_the_newest_published_even_if_muted(client, db, make_user):
    """/latest sirve a la fila "Acerca de": la última publicada, aunque el
    usuario haya silenciado las novedades y aunque ya la esté ejecutando."""
    ruben = make_user("Ruben")
    ruben.changelog_opt_out = True
    db.commit()
    _seed(db, version="1.9", title="Vieja", importance="major", published=True, items=[])
    _seed(db, version="1.10", title={"es": "Nueva", "en": "New"}, importance="minor", published=True, items=[])
    _seed(db, version="2.0", title="Borrador", importance="major", published=False, items=[])

    r = client.get(f"{API}/release-notes/latest?lang=en", headers=auth(ruben))
    assert r.status_code == 200, r.text
    assert r.json() == {"version": "1.10", "title": "New"}, "1.10 > 1.9 numéricamente, y la 2.0 no está publicada"


def test_latest_is_null_without_notes(client, db, make_user):
    ruben = make_user("Ruben")
    r = client.get(f"{API}/release-notes/latest", headers=auth(ruben))
    assert r.status_code == 200, r.text
    assert r.json() is None
