"""Líneas de un ticket → artículos con cantidad y precio.

Encima de `receipt_layout` (que reconstruye la maquetación) y por debajo de
`receipt_matcher` (que decide qué producto es cada cosa).

Lo que hay aquí es lo **común a cualquier cadena**: quitar cabecera y pie, sacar
la cantidad de delante, entender el granel y leer los importes de la derecha.
Las reglas propias de cada supermercado — las que necesitan tickets reales del
súper de cada uno — irán encima, no dentro.

Sesgo deliberado: ante la duda, **no** devolver la línea. Una línea de menos se
añade a mano en la pantalla de revisión; una de más hay que descubrirla y
borrarla, y si se cuela ensucia la despensa.
"""
from __future__ import annotations

import re
import statistics
from dataclasses import dataclass

from app.services.receipt_layout import Line, detect_amount_column, group_lines
from app.services.receipt_ocr import Word

# Palabras que delatan cabecera, pie o totales. Si aparecen, la línea no es un
# artículo. En minúsculas y sin tildes: se comparan contra texto normalizado.
STOP_WORDS = {
    "total", "subtotal", "suma", "tarjeta", "efectivo", "cambio",
    "entrega", "entregado", "devolucion", "eur", "euros",
    "iva", "cuota", "base", "imponible", "descuento", "desc", "ahorro", "promo",
    "descripcion", "importe", "precio", "unidad", "articulos", "articulo",
    "factura", "simplificada", "nif", "cif", "telefono", "tel",
    "gracias", "atencion", "cliente", "caja", "op", "www", "http",
    "zahlen", "summe", "kreditkarte", "mwst",  # tickets alemanes de Lidl
}

# "1,29", "12.50" — con la letra de IVA opcional que Lidl pega detrás.
AMOUNT_RE = re.compile(r"^(\d{1,4})[.,](\d{2})\s*[A-C]?$")

# "2 x 0,85" o "5x0,85": unidades y precio unitario.
TIMES_RE = re.compile(r"(\d+)\s*[xX]\s*(\d{1,4}[.,]\d{2})")

# "1,414 kg" — granel. También "0,842 KG".
#
# El caso de la unidad hay que mirarlo con lupa: en un ticket real,
# `1 SETA SHIITAKE 3,19` seguido de una `L` suelta del OCR se leía como 3,19
# LITROS y entraban 3.190 ml en la despensa. Por eso `_looks_like_weight`
# descarta un "peso" cuyo número es en realidad el importe de la línea.
WEIGHT_RE = re.compile(r"(\d+[.,]\d+)\s*(kg|g|ml|l)\b", re.IGNORECASE)

# Cantidad al principio: "2 AGUA MINERAL". Mercadona lo hace así.
#
# El nombre puede empezar por otro número — `1 24 HUEVOS FRESCOS` es "1 unidad
# de 24 huevos" — así que detrás de la cantidad se admite cualquier cosa menos
# un separador decimal, que delataría un precio y no una cantidad.
LEADING_QTY_RE = re.compile(r"^\s*(\d{1,3})\s+(?![\d]+[.,])")

# Un artículo con menos letras que esto es ruido del OCR, no un nombre.
MIN_DESC_LETTERS = 3

# Restos que no forman parte del nombre: importes sueltos, "3 x 1,29", y las
# marcas de precio por unidad de medida ("EUR/kg", "€/Kg", y lo que el OCR haga
# con ellas, tipo "R/KgH").
LEFTOVER_RES = (
    TIMES_RE,
    re.compile(r"\b\w{0,3}[/]\s*k?g\w?\b", re.IGNORECASE),
    re.compile(r"[€$]"),
    # Uno o dos decimales: el OCR se come dígitos a menudo, y en un ticket real
    # `4 RELLENO FAJITAS 1,90 7,60` salía como `1,0` y se quedaba en el nombre.
    re.compile(r"\b\d{1,4}[.,]\d{1,2}\b"),
    # La "x" que queda huérfana cuando el peso y el precio se van por separado:
    # "Banana 1,414 kg x 1,29" dejaba "Banana x".
    re.compile(r"(?<=\s)[xX](?=\s|$)"),
)

# Basura del margen izquierdo: el OCR se inventa una o dos letras antes del
# nombre ("M1 QUESO", "BA CARPACCIO", "ES 2 BOLSA GRANDE"). Se quita un token
# corto como mucho, y nunca si son solo dígitos — eso sería la cantidad.
LEADING_JUNK_RE = re.compile(r"^\s*[^\w\s]*\s*(?:(?![0-9]+\s)[\w]{1,2}\s+)?")


def strip_leftovers(desc: str) -> str:
    """Quita del nombre lo que son números y unidades, no producto."""
    out = desc
    for pattern in LEFTOVER_RES:
        out = pattern.sub(" ", out)
    out = WEIGHT_RE.sub(" ", out)
    return " ".join(out.split())


@dataclass
class ParsedItem:
    """Un artículo tal y como venía en el ticket, todavía sin emparejar."""

    raw: str
    quantity: float
    unit: str          # 'g' | 'ml' | 'unit'
    amount: float | None       # importe de la línea
    unit_price: float | None   # precio por unidad o por kilo, si venía
    line_index: int

    @property
    def arithmetic_ok(self) -> bool | None:
        """¿Cuadran cantidad × precio con el importe?

        Es la suma de control que trae el propio ticket, y sirve para cazar el
        fallo más peligroso del OCR: el número mal leído pero verosímil. Se vio
        de verdad — `0,730 kg x 6,99` para un importe de 0,72, imposible.

        None cuando faltan datos para comprobarlo, que no es lo mismo que mal.
        """
        if self.amount is None or self.unit_price is None or not self.quantity:
            return None
        qty = self.quantity / 1000 if self.unit in ("g", "ml") else self.quantity
        esperado = qty * self.unit_price
        # 2 céntimos de margen: el redondeo del ticket es real.
        return abs(esperado - self.amount) <= 0.02 + 0.01 * abs(esperado)


def _to_float(text: str) -> float | None:
    m = AMOUNT_RE.match(text.strip())
    if m:
        return float(f"{m.group(1)}.{m.group(2)}")
    try:
        return float(text.replace(",", "."))
    except ValueError:
        return None


def _is_noise(desc: str) -> bool:
    """¿Es cabecera, pie o basura del OCR en vez de un artículo?"""
    from app.services.receipt_matcher import normalize

    norm = normalize(desc)
    if sum(c.isalpha() for c in norm) < MIN_DESC_LETTERS:
        return True
    tokens = {t.lower() for t in norm.split()}
    return bool(tokens & STOP_WORDS)


def _is_real_weight(match: re.Match, amount: float | None) -> bool:
    """¿Ese "1,23 kg" es de verdad un peso, o un precio con una letra pegada?

    Caso real que motivó esto: `1 SETA SHIITAKE 3,19` con una `L` suelta al lado
    (ruido del OCR) se leía como 3,19 **litros**, y entraban 3.190 ml en la
    despensa por un producto que costaba 3,19 €. Un número que ya es el importe
    de la línea no puede ser además su peso.

    La `l` sola es la sospechosa: `kg`, `g` y `ml` casi nunca aparecen por
    accidente, pero una `L` mayúscula suelta sí.
    """
    value = float(match.group(1).replace(",", "."))
    if amount is not None and abs(value - amount) < 0.005:
        return False
    return True


def _weight_to_base(value: float, unit: str) -> tuple[float, str]:
    """Peso del ticket → (cantidad, unidad) de la despensa.

    `INVENTORY_UNITS` solo admite g, ml y unit, así que los kilos y los litros se
    pasan a la unidad pequeña. Es exacto, no una estimación.
    """
    unit = unit.lower()
    if unit == "kg":
        return value * 1000, "g"
    if unit == "l":
        return value * 1000, "ml"
    return value, "ml" if unit == "ml" else "g"


def _parse_line(line: Line, cut: int | None, index: int) -> ParsedItem | None:
    desc, right = line.split_at(cut) if cut else (line.text, "")
    full = line.text

    amounts = [v for v in (_to_float(w.text) for w in
                           sorted(line.words, key=lambda w: w.left)
                           if AMOUNT_RE.match(w.text.strip())) if v is not None]
    amount = amounts[-1] if amounts else None
    unit_price = amounts[0] if len(amounts) >= 2 else None

    veces = TIMES_RE.search(full)

    # 1. Fuera la basura del margen izquierdo, antes de leer nada: si no, la
    #    cantidad de "ES 2 BOLSA GRANDE" queda escondida detrás del "ES".
    desc = LEADING_JUNK_RE.sub("", desc, count=1)

    # 2. Granel: "1,414 kg x 1,29". El peso manda sobre cualquier otra cantidad
    #    porque es un dato exacto, no una estimación.
    peso = WEIGHT_RE.search(full)
    if peso is not None and not _is_real_weight(peso, amount):
        peso = None
    if peso:
        value = float(peso.group(1).replace(",", "."))
        quantity, unit = _weight_to_base(value, peso.group(2))
        if veces and unit_price is None:
            unit_price = _to_float(veces.group(2))
        desc = strip_leftovers(desc)
        if _is_noise(desc):
            # Línea de solo-peso: es la continuación del artículo de arriba
            # (las dos cadenas medidas lo hacen así). Ensamblarlas es cosa de
            # las reglas de cadena; aquí se descarta antes que inventarse un
            # artículo sin nombre.
            return None
        return ParsedItem(raw=desc, quantity=quantity, unit=unit,
                          amount=amount, unit_price=unit_price, line_index=index)

    # 3. Cantidad de delante: "2 AGUA MINERAL".
    quantity = 1.0
    m = LEADING_QTY_RE.match(desc)
    if m:
        quantity = float(m.group(1))
        desc = desc[m.end():]

    # 4. "5 x 0,85" manda sobre lo anterior: trae cantidad y precio unitario.
    if veces:
        quantity = float(veces.group(1))
        unit_price = _to_float(veces.group(2))

    desc = strip_leftovers(desc)
    if _is_noise(desc):
        return None

    if amount is None and unit_price is None:
        # Ni importe ni precio: nada dice que esto se haya comprado.
        return None

    return ParsedItem(raw=desc, quantity=quantity, unit="unit",
                      amount=amount, unit_price=unit_price, line_index=index)


# Cuántas veces la mediana tiene que superar un importe del final para tomarlo
# por un total y no por un producto.
FOOTER_FACTOR = 3.0


def drop_footer(items: list[ParsedItem]) -> list[ParsedItem]:
    """Quita del final los totales, el IVA y la forma de pago.

    El pie de un ticket trae importes grandes que se cuelan como artículos
    carísimos: en un ticket real entraban `Rpte: Mastel 129,07` (el pago con
    tarjeta) y `10% HDL 54,95` (una base imponible).

    Las palabras ancla no bastan porque el OCR las destroza — `Suma` salía como
    `Suma 8, Ni`. Y comparar contra la suma de los artículos tampoco vale: si al
    OCR se le escapan tres líneas, la suma ya no cuadra con el total y la regla
    no dispara. Lo que sí aguanta es la **magnitud**: un total es por
    construcción mucho mayor que cualquier artículo suelto.

    Solo se mira **desde el final**, que es donde vive el pie. Un producto caro
    en mitad del ticket no se toca.

    Asume el sesgo de siempre: puede llevarse por delante un último artículo
    genuinamente caro. Una línea de menos se añade a mano en la revisión; un
    total de 129 € metido en la despensa hay que descubrirlo.
    """
    amounts = [i.amount for i in items if i.amount is not None]
    if len(amounts) < 4:
        return items
    limite = statistics.median(amounts) * FOOTER_FACTOR

    fin = len(items)
    while fin > 0:
        amount = items[fin - 1].amount
        if amount is None or amount <= limite:
            break
        fin -= 1
    return items[:fin]


def parse(words: list[Word]) -> list[ParsedItem]:
    """Palabras del OCR → artículos del ticket."""
    lines = group_lines(words)
    cut = detect_amount_column(lines)
    items = []
    for i, line in enumerate(lines):
        item = _parse_line(line, cut, i)
        if item is not None:
            items.append(item)
    return drop_footer(items)
