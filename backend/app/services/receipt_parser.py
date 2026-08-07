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
from dataclasses import dataclass

from app.services.receipt_layout import Line, detect_amount_column, group_lines
from app.services.receipt_ocr import Word

# Palabras que delatan cabecera, pie o totales. Si aparecen, la línea no es un
# artículo. En minúsculas y sin tildes: se comparan contra texto normalizado.
STOP_WORDS = {
    "total", "subtotal", "tarjeta", "efectivo", "cambio", "entrega",
    "iva", "cuota", "base", "imponible", "descuento", "ahorro",
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
WEIGHT_RE = re.compile(r"(\d+[.,]\d+)\s*(kg|g|ml|l)\b", re.IGNORECASE)

# Cantidad al principio: "2 AGUA MINERAL". Mercadona lo hace así.
LEADING_QTY_RE = re.compile(r"^\s*(\d{1,3})\s+(?=\D)")

# Un artículo con menos letras que esto es ruido del OCR, no un nombre.
MIN_DESC_LETTERS = 3

# Restos que no forman parte del nombre: importes sueltos, "3 x 1,29", y las
# marcas de precio por unidad de medida ("EUR/kg", "€/Kg", y lo que el OCR haga
# con ellas, tipo "R/KgH").
LEFTOVER_RES = (
    TIMES_RE,
    re.compile(r"\b\w{0,3}[/]\s*k?g\w?\b", re.IGNORECASE),
    re.compile(r"[€$]"),
    re.compile(r"\b\d{1,4}[.,]\d{2}\b"),
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


def parse(words: list[Word]) -> list[ParsedItem]:
    """Palabras del OCR → artículos del ticket."""
    lines = group_lines(words)
    cut = detect_amount_column(lines)
    items = []
    for i, line in enumerate(lines):
        item = _parse_line(line, cut, i)
        if item is not None:
            items.append(item)
    return items
