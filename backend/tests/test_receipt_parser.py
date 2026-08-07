"""Líneas del ticket → artículos con cantidad y precio.

Sesgo que se prueba aquí tanto como el acierto: **ante la duda, no devolver la
línea**. Una de menos se añade a mano en la revisión; una de más hay que
descubrirla y borrarla, y si se cuela ensucia la despensa.
"""
import json
from pathlib import Path

import pytest

from app.services.receipt_ocr import Word
from app.services.receipt_parser import (
    ParsedItem,
    parse,
    strip_leftovers,
)

FIXTURES = Path(__file__).parent / "fixtures" / "receipts"


def load(name: str) -> list[Word]:
    data = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
    return [Word(**w) for w in data["words"]]


def by_name(items: list[ParsedItem], needle: str) -> ParsedItem:
    for it in items:
        if needle.lower() in it.raw.lower():
            return it
    raise AssertionError(f"No hay artículo con {needle!r}: {[i.raw for i in items]}")


# ── Limpiar el nombre ────────────────────────────────────────────────────────

def test_quita_los_importes_del_nombre():
    assert strip_leftovers("SOJA NATURAL 1,19") == "SOJA NATURAL"


def test_quita_el_por_y_el_precio_unitario():
    assert strip_leftovers("Zumo melocotón 5 x 0,85") == "Zumo melocotón"


def test_quita_las_marcas_de_precio_por_kilo():
    assert strip_leftovers("Banana 1,414 kg x 1,29 EUR/kg") == "Banana"


def test_no_se_come_el_nombre():
    assert strip_leftovers("PECHUGA PAVO HORNO") == "PECHUGA PAVO HORNO"


# ── Aritmética, la suma de control del propio ticket ─────────────────────────

def test_cantidad_por_precio_tiene_que_dar_el_importe():
    ok = ParsedItem(raw="x", quantity=2, unit="unit", amount=2.38, unit_price=1.19, line_index=0)

    assert ok.arithmetic_ok is True


def test_detecta_un_numero_mal_leido():
    """Caso real: se leyó `0,730 kg x 6,99` para un importe de 0,72. Eso daría
    5,10, así que la línea es imposible — el precio era 0,99. Sin esto, ese 6,99
    entraría en la despensa con pinta de correcto."""
    malo = ParsedItem(raw="Banana", quantity=730, unit="g", amount=0.72,
                      unit_price=6.99, line_index=0)

    assert malo.arithmetic_ok is False


def test_sin_datos_no_dice_ni_bien_ni_mal():
    """Faltar no es lo mismo que estar mal, y confundirlo llenaría la pantalla
    de avisos falsos."""
    sin = ParsedItem(raw="x", quantity=1, unit="unit", amount=1.65,
                     unit_price=None, line_index=0)

    assert sin.arithmetic_ok is None


def test_tolera_el_redondeo_del_ticket():
    casi = ParsedItem(raw="x", quantity=3, unit="unit", amount=3.57,
                      unit_price=1.19, line_index=0)

    assert casi.arithmetic_ok is True


# ── Contra tickets reales ────────────────────────────────────────────────────

def test_mercadona_saca_los_articulos_limpios():
    items = parse(load("mercadona-002"))

    assert len(items) >= 12
    assert by_name(items, "GRISSINI").amount == 1.65
    assert by_name(items, "SALSA TRUFA").quantity == 1


def test_mercadona_lee_la_cantidad_de_delante():
    items = parse(load("mercadona-002"))

    soja = by_name(items, "SOJA NATURAL")

    assert soja.quantity == 2
    assert soja.unit_price == 1.19
    assert soja.arithmetic_ok is True


def test_el_nombre_no_arrastra_el_precio_unitario():
    """`2 SOJA NATURAL 1,19` tiene que dar el nombre a secas: si el precio queda
    pegado, el emparejador busca un producto que no existe."""
    assert by_name(parse(load("mercadona-002")), "SOJA").raw == "SOJA NATURAL"


def test_se_quita_la_basura_del_margen_izquierdo():
    """El OCR se inventa una o dos letras antes del nombre: `M1 QUESO`,
    `BA CARPACCIO`, `ES 2 BOLSA GRANDE`."""
    items = parse(load("mercadona-002"))

    assert by_name(items, "QUESO").raw == "QUESO"
    assert by_name(items, "CARPACCIO").raw == "CARPACCIO"


def test_la_basura_del_margen_no_esconde_la_cantidad():
    """Regresión: con `ES 2 BOLSA GRANDE` la cantidad quedaba detrás del `ES`,
    salía 1 en vez de 2, y encima la aritmética lo delataba."""
    bolsa = by_name(parse(load("mercadona-002")), "BOLSA GRANDE")

    assert bolsa.quantity == 2
    assert bolsa.arithmetic_ok is True


@pytest.mark.parametrize("name", ["mercadona-001", "mercadona-002", "mercadona-003",
                                  "lidl-001", "lidl-002", "lidl-003", "lidl-004", "aldi-001"])
def test_ningun_ticket_cuela_cabecera_ni_totales(name):
    items = parse(load(name))

    # Por tokens y no por subcadena: `iva` está dentro de `oliva`, que es un
    # producto perfectamente legítimo.
    prohibidos = {"total", "tarjeta", "iva", "descripcion", "importe", "nif"}
    for it in items:
        tokens = {t.strip(".,:;").lower() for t in it.raw.split()}
        assert not (tokens & prohibidos), f"{it.raw!r} no es un artículo"


@pytest.mark.parametrize("name", ["mercadona-001", "mercadona-002", "mercadona-003",
                                  "lidl-001", "lidl-002", "lidl-003", "lidl-004", "aldi-001"])
def test_ningun_articulo_sale_sin_nombre_ni_con_cantidad_absurda(name):
    for it in parse(load(name)):
        assert it.raw.strip(), "un artículo sin nombre no sirve para nada"
        assert it.quantity > 0
        assert it.unit in ("g", "ml", "unit")


def test_un_ticket_ilegible_no_inventa_articulos():
    """aldi-001 es una miniatura de 387×516 que el OCR no puede leer. Lo correcto
    es devolver poco, no rellenar con ruido."""
    items = parse(load("aldi-001"))

    assert len(items) <= 8, [i.raw for i in items]


def test_sin_palabras_no_hay_articulos():
    assert parse([]) == []
