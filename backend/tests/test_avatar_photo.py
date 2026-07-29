"""Foto de perfil: qué se guarda, qué se descarta y quién llega a verla."""
from io import BytesIO

import pytest
from PIL import Image

from conftest import API, auth

from app.services.avatar_photo_service import media_root


def _jpeg(size=(800, 400), exif: Image.Exif | None = None) -> bytes:
    """Un JPEG de verdad, rectangular a propósito (para ver el recorte)."""
    buf = BytesIO()
    im = Image.new("RGB", size, (120, 80, 200))
    im.save(buf, "JPEG", exif=exif) if exif else im.save(buf, "JPEG")
    return buf.getvalue()


def _upload(client, user, data: bytes, filename="foto.jpg", content_type="image/jpeg"):
    return client.post(
        f"{API}/users/me/avatar-photo",
        files={"file": (filename, data, content_type)},
        headers=auth(user),
    )


def _stored_image(name: str) -> Image.Image:
    return Image.open(media_root() / name)


# ── Lo que llega a disco ────────────────────────────────────────────────────

def test_upload_stores_a_square_webp(client, make_user):
    r = _upload(client, make_user("Ruben"), _jpeg())
    assert r.status_code == 200, r.text

    name = r.json()["avatar_photo"]
    assert name.endswith(".webp")
    with _stored_image(name) as im:
        assert im.format == "WEBP"
        assert im.size == (256, 256)  # rectangular entra, cuadrado sale


def test_stored_photo_has_no_metadata_left(client, make_user):
    """El EXIF de una foto de móvil trae GPS. Reencodear lo borra entero.

    Se comprueba que no queda *nada* de EXIF, que es más fuerte que buscar la
    etiqueta de GPS: las coordenadas viajan en ese mismo bloque, así que si el
    bloque no existe tampoco existen.
    """
    exif = Image.Exif()
    exif[0x010F] = "ACME Phone"          # Make
    exif[0x0110] = "Modelo con GPS"      # Model
    exif[0x0132] = "2026:07:29 12:00:00"  # DateTime
    r = _upload(client, make_user("Ruben"), _jpeg(exif=exif))
    assert r.status_code == 200, r.text

    with _stored_image(r.json()["avatar_photo"]) as im:
        assert not im.getexif()
        assert "exif" not in im.info


def test_filename_is_random_not_derived_from_the_user(client, make_user):
    """Si se filtra una URL, no puede servir para deducir las de los demás.

    La propiedad que importa no es "no contiene el id" (un hex de 32 dígitos
    contiene casi cualquier cifra por casualidad), sino que el nombre no sea una
    función del usuario: dos subidas del mismo usuario dan nombres distintos.
    """
    ruben = make_user("Ruben")
    first = _upload(client, ruben, _jpeg()).json()["avatar_photo"]
    second = _upload(client, ruben, _jpeg()).json()["avatar_photo"]

    stem = first.removesuffix(".webp")
    assert len(stem) == 32 and all(c in "0123456789abcdef" for c in stem)
    assert first != second
    assert "ruben" not in first.lower()


def test_replacing_a_photo_removes_the_old_file(client, make_user):
    ruben = make_user("Ruben")
    first = _upload(client, ruben, _jpeg()).json()["avatar_photo"]
    second = _upload(client, ruben, _jpeg(size=(300, 300))).json()["avatar_photo"]

    assert first != second
    assert not (media_root() / first).exists()
    assert (media_root() / second).exists()


def test_deleting_the_photo_removes_the_file_and_the_row(client, make_user):
    ruben = make_user("Ruben")
    name = _upload(client, ruben, _jpeg()).json()["avatar_photo"]

    r = client.delete(f"{API}/users/me/avatar-photo", headers=auth(ruben))
    assert r.status_code == 200, r.text
    assert r.json()["avatar_photo"] is None
    assert not (media_root() / name).exists()


def test_deleting_the_account_takes_the_photo_with_it(client, make_user):
    ruben = make_user("Ruben")
    name = _upload(client, ruben, _jpeg()).json()["avatar_photo"]

    assert client.delete(f"{API}/users/me", headers=auth(ruben)).status_code == 204
    assert not (media_root() / name).exists()


# ── Lo que no entra ─────────────────────────────────────────────────────────

def test_an_svg_is_rejected_however_it_is_labelled(client, make_user):
    """El vector clásico: un SVG con script servido desde tu propio dominio."""
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    r = _upload(client, make_user("Ruben"), svg, filename="foto.jpg", content_type="image/jpeg")
    assert r.status_code == 422


def test_content_type_does_not_decide_anything(client, make_user):
    """Decide si Pillow sabe abrirlo, no lo que diga la cabecera."""
    r = _upload(client, make_user("Ruben"), b"esto no es una imagen" * 100)
    assert r.status_code == 422


def test_oversized_upload_is_rejected(client, make_user):
    from app.services.avatar_photo_service import MAX_UPLOAD_BYTES

    r = _upload(client, make_user("Ruben"), b"\xff" * (MAX_UPLOAD_BYTES + 1))
    assert r.status_code == 413


def test_decompression_bomb_is_rejected(client, make_user):
    """Un PNG pequeño que descomprime a una imagen enorme."""
    from app.services import avatar_photo_service

    buf = BytesIO()
    Image.new("RGB", (2000, 2000), (0, 0, 0)).save(buf, "PNG")

    # Bajamos el umbral en vez de generar de verdad una imagen de 40 MP: lo que
    # se comprueba es que el tope actúa y que el usuario ve un 422, no un 500.
    original = Image.MAX_IMAGE_PIXELS
    avatar_photo_service.Image.MAX_IMAGE_PIXELS = 1000
    try:
        r = _upload(client, make_user("Ruben"), buf.getvalue(), filename="b.png", content_type="image/png")
        assert r.status_code == 422
    finally:
        avatar_photo_service.Image.MAX_IMAGE_PIXELS = original


# ── Quién la ve ─────────────────────────────────────────────────────────────

def test_pending_request_hides_the_photo(client, make_user):
    """Lo que sostiene la feature: una solicitud pendiente no enseña la foto."""
    ruben, silva = make_user("Ruben"), make_user("Silva")
    _upload(client, ruben, _jpeg())

    r = client.post(f"{API}/friends", json={"email": silva.email}, headers=auth(ruben))
    assert r.status_code == 201, r.text

    pend = client.get(f"{API}/friends/pending", headers=auth(silva)).json()
    assert len(pend) == 1
    assert pend[0]["requester"]["avatar_photo"] is None
    # El avatar predefinido sí: son dibujos nuestros, no puede haber sorpresa.
    assert "avatar_id" in pend[0]["requester"]


def test_photo_appears_once_the_request_is_accepted(client, make_user):
    ruben, silva = make_user("Ruben"), make_user("Silva")
    name = _upload(client, ruben, _jpeg()).json()["avatar_photo"]

    fid = client.post(f"{API}/friends", json={"email": silva.email}, headers=auth(ruben)).json()["id"]
    client.patch(f"{API}/friends/{fid}", json={"status": "accepted"}, headers=auth(silva))

    friends = client.get(f"{API}/friends", headers=auth(silva)).json()
    assert friends[0]["requester"]["avatar_photo"] == name


def test_rejected_request_never_shows_the_photo(client, make_user):
    ruben, silva = make_user("Ruben"), make_user("Silva")
    _upload(client, ruben, _jpeg())

    fid = client.post(f"{API}/friends", json={"email": silva.email}, headers=auth(ruben)).json()["id"]
    client.patch(f"{API}/friends/{fid}", json={"status": "rejected"}, headers=auth(silva))

    for f in client.get(f"{API}/friends", headers=auth(silva)).json():
        assert f["requester"]["avatar_photo"] is None


# ── Moderación ──────────────────────────────────────────────────────────────

def test_upload_notifies_the_admin_with_a_thumbnail(client, make_user, monkeypatch):
    """No hay moderación automática: la hay porque cada foto llega al chat."""
    sent = []

    async def _fake(user_id, name, email, image, photo_name):
        sent.append((user_id, name, email, image, photo_name))

    monkeypatch.setattr("app.routers.users.send_avatar_photo_alert", _fake)

    ruben = make_user("Ruben")
    stored = _upload(client, ruben, _jpeg()).json()["avatar_photo"]

    assert len(sent) == 1
    user_id, name, email, image, photo_name = sent[0]
    assert (user_id, name, email) == (ruben.id, "Ruben", ruben.email)
    assert image is not None and image.startswith(b"\xff\xd8")  # JPEG
    # El nombre viaja para que el botón de rechazar sepa qué foto retirar, y
    # para que rechazar un aviso viejo no se lleve una foto ya cambiada.
    assert photo_name == stored


def test_thumbnail_is_none_when_the_file_vanished(client, make_user):
    """Sin miniatura el aviso se manda igual, así que esto no puede explotar."""
    from app.services.avatar_photo_service import read_thumbnail_jpeg

    assert read_thumbnail_jpeg("no-existe.webp") is None


def test_stranger_cannot_read_the_profile_photo(client, make_user):
    ruben, nadie = make_user("Ruben"), make_user("Nadie")
    _upload(client, ruben, _jpeg())

    r = client.get(f"{API}/users/{ruben.id}/profile", headers=auth(nadie))
    assert r.status_code == 403
