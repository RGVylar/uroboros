import pytest
from conftest import API

from app.services.name_moderation import is_offensive_name


@pytest.mark.parametrize("name", [
    "puta", "Maricón", "N1GG3R", "xXniggerXx", "niiiigger", "hijo de puta",
    "Hijoputa", "sudaca", "Adolf Hitler", "white power", "negro de mierda",
])
def test_blocks_offensive(name):
    assert is_offensive_name(name)


@pytest.mark.parametrize("name", [
    "Rubén", "Computadora", "Nazir", "Scunthorpe", "María José", "Ana Negro",
    "Fagundes", "Conchi", "Moro", "João", "Alex",
])
def test_allows_real_names(name):
    assert not is_offensive_name(name)


def test_register_rejects_offensive_name(client):
    r = client.post(f"{API}/auth/register", json={
        "email": "insulto@example.com", "password": "12345678", "name": "hijo de puta",
    })
    assert r.status_code == 422
    assert r.json()["detail"] == "Name not allowed"
