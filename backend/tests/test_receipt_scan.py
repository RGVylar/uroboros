"""Escaneo de tickets: puerta, validación y OCR.

La mayoría de los tests no necesitan Tesseract instalado — el binario solo hace
falta para el de integración, que se salta si no está. Lo que sí se prueba
siempre es lo que puede romperse sin avisar: que el flag corta, que la foto se
valida, y que el preprocesado hace lo que dice.
"""
import io
import shutil

import pytest
from PIL import Image, ImageDraw

from app.config import settings
from app.services import receipt_ocr
from app.services.receipt_ocr import InvalidImage, _parse_tsv, preprocess

from conftest import API, auth

FLAG = "receipt_scan"
URL = f"{API}/receipts/scan"


def _png(width: int = 600, height: int = 800, text: bool = True) -> bytes:
    """Un ticket de pega: texto negro sobre blanco con importes a la derecha."""
    img = Image.new("RGB", (width, height), "white")
    if text:
        d = ImageDraw.Draw(img)
        for i, (left, right) in enumerate(
            [("MERCADONA S.A.", ""), ("LECHE SEM DESN 1L", "0,89"), ("PAN MOLDE", "1,10")]
        ):
            d.text((20, 40 + i * 60), left, fill="black")
            if right:
                d.text((width - 90, 40 + i * 60), right, fill="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _flagged(db, make_user, name="Ana"):
    user = make_user(name)
    user.feature_flags = [FLAG]
    db.commit()
    return user


# ── La puerta ────────────────────────────────────────────────────────────────

def test_sin_flag_responde_404(client, make_user):
    """Sin el flag, ni la ruta existe. Esconder el botón no protegía nada."""
    user = make_user("Sin")

    r = client.post(URL, files={"file": ("t.png", _png(), "image/png")}, headers=auth(user))

    assert r.status_code == 404


def test_sin_token_responde_401(client):
    r = client.post(URL, files={"file": ("t.png", _png(), "image/png")})

    assert r.status_code == 401


# ── Validación de la subida ──────────────────────────────────────────────────

def test_lo_que_no_es_imagen_da_422(client, db, make_user):
    """Decide Pillow, no el content-type: esto se anuncia como PNG y no lo es."""
    user = _flagged(db, make_user)

    r = client.post(
        URL, files={"file": ("t.png", b"no soy una imagen", "image/png")}, headers=auth(user)
    )

    assert r.status_code == 422


def test_fichero_vacio_da_422(client, db, make_user):
    user = _flagged(db, make_user)

    r = client.post(URL, files={"file": ("t.png", b"", "image/png")}, headers=auth(user))

    assert r.status_code == 422


def test_demasiado_grande_da_413(client, db, make_user, monkeypatch):
    """El tope se comprueba aunque el Content-Length mienta."""
    user = _flagged(db, make_user)
    monkeypatch.setattr("app.routers.receipts.MAX_UPLOAD_BYTES", 100)

    r = client.post(
        URL, files={"file": ("t.png", _png(), "image/png")}, headers=auth(user)
    )

    assert r.status_code == 413


def test_sin_tesseract_da_503_y_no_500(client, db, make_user, monkeypatch):
    """Falta el binario: es culpa del despliegue, y hay que decirlo como tal."""
    user = _flagged(db, make_user)
    monkeypatch.setattr(settings, "tesseract_cmd", "no-existe-este-binario-xyz")

    r = client.post(URL, files={"file": ("t.png", _png(), "image/png")}, headers=auth(user))

    assert r.status_code == 503


# ── Preprocesado (sin Tesseract) ─────────────────────────────────────────────

def test_preprocess_normaliza_el_ancho():
    """Sube las pequeñas y baja las enormes: el OCR ve siempre la misma escala."""
    pequena = preprocess(_png(width=300, height=400))
    enorme = preprocess(_png(width=4000, height=5000))

    assert pequena.width == receipt_ocr.TARGET_WIDTH
    assert enorme.width == receipt_ocr.TARGET_WIDTH


def test_preprocess_deja_la_imagen_en_blanco_y_negro():
    """Modo '1' = binarizada por Otsu, que es lo que come Tesseract."""
    assert preprocess(_png()).mode == "1"


def test_preprocess_conserva_la_proporcion():
    out = preprocess(_png(width=600, height=1200))

    assert out.height == pytest.approx(out.width * 2, rel=0.01)


def test_preprocess_rechaza_lo_que_no_es_imagen():
    with pytest.raises(InvalidImage):
        preprocess(b"esto no abre")


def test_una_imagen_plana_no_revienta_otsu():
    """Histograma degenerado: todo del mismo color. No debe dividir por cero."""
    buf = io.BytesIO()
    Image.new("RGB", (400, 400), "white").save(buf, format="PNG")

    assert preprocess(buf.getvalue()).mode == "1"


# ── Lectura del TSV ──────────────────────────────────────────────────────────

def test_parse_tsv_se_queda_solo_con_las_palabras():
    """Las filas de estructura (conf -1, sin texto) no son palabras."""
    tsv = (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\t"
        "left\ttop\twidth\theight\tconf\ttext\n"
        "1\t1\t0\t0\t0\t0\t0\t0\t500\t400\t-1\t\n"
        "5\t1\t1\t1\t1\t1\t20\t28\t89\t11\t92.7\tMERCADONA\n"
        "5\t1\t1\t1\t1\t2\t120\t28\t40\t11\t88.1\t0,89\n"
    )

    words = _parse_tsv(tsv)

    assert [w.text for w in words] == ["MERCADONA", "0,89"]
    assert words[0].left == 20 and words[0].width == 89
    assert words[1].conf == pytest.approx(88.1)


def test_parse_tsv_ignora_filas_rotas_en_vez_de_reventar():
    """Una palabra menos es mejor que un 500."""
    tsv = (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\t"
        "left\ttop\twidth\theight\tconf\ttext\n"
        "5\t1\t1\t1\t1\t1\tNOPE\t28\t89\t11\t92.7\tROTA\n"
        "5\t1\t1\t1\t1\t2\t20\t28\t89\t11\t90.0\tBUENA\n"
    )

    assert [w.text for w in _parse_tsv(tsv)] == ["BUENA"]


def test_parse_tsv_vacio_no_falla():
    assert _parse_tsv("") == []


# ── Integración de verdad (necesita el binario) ──────────────────────────────

def _tesseract_disponible() -> bool:
    return shutil.which(settings.tesseract_cmd) is not None


@pytest.mark.skipif(not _tesseract_disponible(), reason="Tesseract no instalado")
def test_lee_un_ticket_y_devuelve_palabras_con_caja(client, db, make_user):
    user = _flagged(db, make_user)

    r = client.post(URL, files={"file": ("t.png", _png(), "image/png")}, headers=auth(user))

    assert r.status_code == 200
    body = r.json()
    assert body["image_width"] == receipt_ocr.TARGET_WIDTH
    assert body["words"], "no ha salido ni una palabra"
    # Lo que de verdad necesita el parser: coordenadas, no solo texto.
    primera = body["words"][0]
    assert {"text", "left", "top", "width", "height", "conf"} <= primera.keys()
    assert "MERCADONA" in body["text"].upper()
