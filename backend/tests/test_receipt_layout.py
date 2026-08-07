"""Geometría del ticket: agrupar en líneas y encontrar la columna de importes.

Dos capas de prueba, a propósito:

- **Sintéticas**, para fijar el comportamiento con casos exactos y controlados.
- **Contra fixtures reales** (`tests/fixtures/receipts/`), que es donde aparecen
  los problemas que uno no se inventa: tamaños de letra mezclados, líneas que se
  tuercen, el OCR partiendo palabras.

Los fixtures son salida real de Tesseract sobre tickets reales, anonimizada por
`scripts/make_receipt_fixture.py`. No hacen falta ni fotos ni Tesseract para
correr esto.
"""
import json
from pathlib import Path

import pytest

from app.services.receipt_layout import (
    Line,
    detect_amount_column,
    group_lines,
    median_line_height,
)
from app.services.receipt_ocr import Word

FIXTURES = Path(__file__).parent / "fixtures" / "receipts"


def load(name: str) -> tuple[list[Word], dict]:
    data = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
    return [Word(**w) for w in data["words"]], data


def w(text: str, left: int, top: int, width: int = 40, height: int = 20) -> Word:
    return Word(text=text, left=left, top=top, width=width, height=height, conf=90.0)


def line_with(lines: list[Line], needle: str) -> Line:
    """La primera línea que contiene ese texto. Falla con contexto si no está."""
    for ln in lines:
        if needle in ln.text:
            return ln
    raise AssertionError(f"No hay ninguna línea con {needle!r}:\n" + "\n".join(l.text for l in lines))


# ── Agrupar en líneas ────────────────────────────────────────────────────────

def test_sin_palabras_no_hay_lineas():
    assert group_lines([]) == []


def test_palabras_a_la_misma_altura_van_juntas():
    lines = group_lines([w("LECHE", 10, 100), w("SEMI", 60, 100), w("0,89", 300, 100)])

    assert len(lines) == 1
    assert lines[0].text == "LECHE SEMI 0,89"


def test_palabras_en_alturas_distintas_no_se_mezclan():
    lines = group_lines([w("LECHE", 10, 100), w("PAN", 10, 200)])

    assert [ln.text for ln in lines] == ["LECHE", "PAN"]


def test_una_linea_algo_torcida_sigue_siendo_una_linea():
    """La foto nunca sale recta; unos pocos píxeles de desnivel son lo normal."""
    lines = group_lines([w("PECHUGA", 10, 100), w("PAVO", 90, 104), w("1,55", 300, 97)])

    assert len(lines) == 1


def test_letras_de_tamanos_distintos_en_la_misma_linea():
    """El TOTAL suele ir más grande que el resto. Por eso se mide solapamiento y
    no distancia entre centros: con centros habría que elegir un umbral que o
    parte las líneas altas o junta las bajas."""
    lines = group_lines([w("TOTAL", 10, 100, height=40), w("44,16", 300, 110, height=20)])

    assert len(lines) == 1
    assert lines[0].text == "TOTAL 44,16"


def test_las_lineas_salen_ordenadas_de_arriba_abajo():
    lines = group_lines([w("TERCERA", 10, 300), w("PRIMERA", 10, 100), w("SEGUNDA", 10, 200)])

    assert [ln.text for ln in lines] == ["PRIMERA", "SEGUNDA", "TERCERA"]


def test_las_palabras_de_una_linea_se_ordenan_por_x():
    """Tesseract no promete orden, y la descripción tiene que salir legible."""
    lines = group_lines([w("MINERAL", 90, 100), w("2", 5, 100), w("AGUA", 30, 100)])

    assert lines[0].text == "2 AGUA MINERAL"


# ── Partir en columnas ───────────────────────────────────────────────────────

def test_split_at_separa_descripcion_e_importe():
    line = group_lines([w("1", 5, 100), w("GRISSINI", 30, 100), w("1,65", 300, 100)])[0]

    assert line.split_at(250) == ("1 GRISSINI", "1,65")


def test_split_at_sin_nada_a_la_derecha():
    line = group_lines([w("BOLLERIA", 10, 100)])[0]

    assert line.split_at(250) == ("BOLLERIA", "")


def test_sin_precios_suficientes_no_se_inventa_columna():
    """Con dos coincidencias no hay columna, hay casualidad."""
    lines = group_lines([w("HOLA", 10, 100), w("1,65", 300, 100), w("2,00", 300, 140)])

    assert detect_amount_column(lines) is None


def test_la_columna_se_situa_a_la_izquierda_de_los_importes():
    importes = ["1,65", "2,38", "5,00", "1,50"]
    lines = group_lines(
        [w(t, 300, 100 + i * 50) for i, t in enumerate(importes)]
        + [w("DESC", 10, 100 + i * 50) for i in range(len(importes))]
    )
    assert len(lines) == len(importes), "cada importe en su línea"

    x = detect_amount_column(lines)

    assert x is not None and x <= 300


# ── Contra tickets reales ────────────────────────────────────────────────────

TICKETS = ["mercadona-001", "mercadona-002", "mercadona-003",
           "lidl-001", "lidl-002", "lidl-003", "lidl-004", "aldi-001"]


@pytest.mark.parametrize("name", TICKETS)
def test_ningun_ticket_real_revienta_el_agrupado(name):
    words, _ = load(name)

    lines = group_lines(words)

    assert lines, "un ticket con palabras tiene que dar líneas"
    assert len(lines) <= len(words), "agrupar no puede producir más líneas que palabras"
    assert sum(len(ln.words) for ln in lines) == len(words), "no se pierde ni se duplica"


@pytest.mark.parametrize("name", TICKETS)
def test_las_lineas_no_se_solapan_entre_si(name):
    """Si dos líneas se pisan verticalmente, el agrupado ha partido una de más."""
    words, _ = load(name)

    lines = group_lines(words)

    for antes, despues in zip(lines, lines[1:]):
        assert despues.top >= antes.top


def test_mercadona_reconstruye_articulos_con_su_importe():
    words, _ = load("mercadona-002")
    lines = group_lines(words)
    x = detect_amount_column(lines)
    assert x is not None

    for desc, importe in [("GRISSINI", "1,65"), ("SALSA TRUFA", "1,50"), ("QUESO", "1,95")]:
        izq, der = line_with(lines, desc).split_at(x)
        assert desc in izq
        assert der == importe


def test_regresion_bolsa_grande_no_pierde_su_importe():
    """La primera versión agrupaba por distancia entre centros con una tolerancia
    fija, y esta línea concreta quedaba partida: la descripción en un grupo y sus
    importes en otro. Se descubrió mirando salida real, no en un test."""
    words, _ = load("mercadona-002")

    linea = line_with(group_lines(words), "BOLSA GRANDE")

    assert "0,20" in linea.text, "el importe tiene que estar en la misma línea"


def test_mercadona_encuentra_el_total():
    words, _ = load("mercadona-002")
    lines = group_lines(words)

    _, der = line_with(lines, "TOTAL").split_at(detect_amount_column(lines))

    assert der == "32,68"


def test_lidl_deja_la_linea_de_cantidad_sin_importe():
    """En Lidl un artículo son dos líneas físicas: nombre e importe en la
    primera, cantidad en la segunda. Que la segunda salga sin nada en la columna
    derecha es la señal que usarán las reglas de cadena para ensamblarlas."""
    words, _ = load("lidl-003")
    lines = group_lines(words)
    x = detect_amount_column(lines)

    izq, der = line_with(lines, "kg x").split_at(x)

    assert "kg x" in izq
    assert der == ""


@pytest.mark.parametrize("name", TICKETS)
def test_la_altura_mediana_es_positiva(name):
    words, _ = load(name)

    assert median_line_height(group_lines(words)) > 0


# ── Guardián de privacidad ───────────────────────────────────────────────────

@pytest.mark.parametrize("name", TICKETS)
def test_ningun_fixture_lleva_identificadores(name):
    """El repo es PÚBLICO y un ticket lleva NIF, teléfono y número de factura.

    `make_receipt_fixture.py` los sustituye por ceros, pero la primera versión
    solo miraba tokens que fueran *solo* dígitos y dejó pasar `A-46103834` y
    `3630-011-156272`. Esto es la red: si alguien añade un ticket con el script
    viejo, o a mano, la suite se cae en vez de publicarlo.

    Los precios y pesos no llegan a 6 dígitos (`1,414` son 4), así que el umbral
    no toca nada que haga falta conservar.
    """
    words, _ = load(name)

    culpables = [
        word.text
        for word in words
        if sum(c.isdigit() for c in word.text) >= 6
        and any(c in "123456789" for c in word.text)
    ]

    assert not culpables, f"identificadores sin anonimizar en {name}: {culpables}"


def test_los_fixtures_declaran_su_cadena():
    """Sin saber de qué súper es, un fixture no sirve para escribir sus reglas."""
    for name in TICKETS:
        _, data = load(name)
        assert data["chain"] in {"mercadona", "lidl", "aldi"}, name
