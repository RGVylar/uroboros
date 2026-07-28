"""GET /goals?user_id= — ver los objetivos de la pareja, no los tuyos.

Bug reportado: el chip de "vista previa" del diario de la pareja mostraba el
progreso real de la pareja pero contra TUS objetivos (el frontend usaba la
variable `goals` del usuario en vez de pedir los de la pareja). El backend no
tenía forma de servir los objetivos de otra persona; este endpoint la añade,
con el mismo permiso household que ya usan /diary/day y /allergies.
"""
from conftest import API, auth
from test_friendships import _befriend
from test_partner_edit import _partner_can_write


def _set_goals(client, actor, kcal):
    r = client.put(
        f"{API}/goals",
        json={"kcal": kcal, "protein": kcal / 20, "carbs": kcal / 10, "fat": kcal / 40},
        headers=auth(actor),
    )
    assert r.status_code == 200, r.text


def test_partner_can_read_partner_goals(client, make_user):
    ruben, pilar = make_user("Ruben"), make_user("Pilar")
    _partner_can_write(client, ruben, pilar)
    _set_goals(client, ruben, kcal=2200)
    _set_goals(client, pilar, kcal=1800)

    r = client.get(f"{API}/goals?user_id={pilar.id}", headers=auth(ruben))
    assert r.status_code == 200, r.text
    assert r.json()["kcal"] == 1800, "debe devolver los objetivos de Pilar, no los de Ruben"


def test_plain_friend_cannot_read_goals(client, make_user):
    ruben, silva = make_user("Ruben"), make_user("Silva")
    _befriend(client, ruben, silva)  # amigo, no pareja
    _set_goals(client, silva, kcal=1800)

    r = client.get(f"{API}/goals?user_id={silva.id}", headers=auth(ruben))
    assert r.status_code == 403


def test_own_goals_still_work_without_user_id(client, make_user):
    ruben = make_user("Ruben")
    _set_goals(client, ruben, kcal=2200)

    r = client.get(f"{API}/goals", headers=auth(ruben))
    assert r.status_code == 200, r.text
    assert r.json()["kcal"] == 2200
