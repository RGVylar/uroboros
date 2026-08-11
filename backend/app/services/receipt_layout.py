"""Geometría de un ticket: de palabras sueltas a líneas y columnas.

Esta capa no sabe nada de supermercados. Solo reconstruye la **maquetación** —
qué palabras van juntas en una línea, y dónde empieza la columna de importes —
que es lo común a cualquier cadena. Las reglas de cada una (cómo se ensambla el
granel en Mercadona, dónde está la cantidad en Lidl) van encima de esto, no aquí.

El orden importa: sin agrupar bien en líneas, cualquier regla de cadena está
leyendo basura y no hay forma de saberlo.
"""
from __future__ import annotations

import re
import statistics
from dataclasses import dataclass, field

from app.services.receipt_ocr import Word

# Un importe: "1,29", "12.50". Sirve para localizar la columna de la derecha, no
# para validar nada — de eso se encarga la aritmética más adelante.
PRICE_RE = re.compile(r"^\d{1,4}[.,]\d{2}$")

# Cuánto se tienen que solapar verticalmente dos palabras para considerarlas de
# la misma línea, como fracción de la altura de la más baja. Medio carácter es
# suficiente para unir lo que va junto sin pegar líneas contiguas.
OVERLAP_RATIO = 0.5


@dataclass
class Line:
    """Una línea **física** del ticket. Ojo: no siempre es un artículo.

    En el granel (las dos cadenas medidas lo hacen) un artículo ocupa dos líneas:
    el nombre en una y el peso y el precio en la siguiente. Ensamblarlas es tarea
    de las reglas de cada cadena, no de aquí.
    """

    words: list[Word] = field(default_factory=list)

    @property
    def top(self) -> int:
        return min(w.top for w in self.words)

    @property
    def bottom(self) -> int:
        return max(w.top + w.height for w in self.words)

    @property
    def height(self) -> int:
        return self.bottom - self.top

    @property
    def text(self) -> str:
        return " ".join(w.text for w in sorted(self.words, key=lambda w: w.left))

    @property
    def band(self) -> tuple[float, float]:
        """Franja típica de la línea, por la mediana y no por los extremos.

        Usar `top`/`bottom` (mínimo y máximo) para decidir quién entra tiene un
        fallo feo: basta **una** palabra con la caja demasiado alta —el OCR las
        produce— para ensanchar la franja, y a partir de ahí la línea atrae todo
        lo que pase cerca y se traga la de abajo. Pasó de verdad, fundiendo dos
        artículos de un Lidl en uno solo.

        La mediana no se mueve por un caso raro, así que la franja sigue siendo
        la de la línea de verdad.
        """
        centers = [w.top + w.height / 2 for w in self.words]
        heights = [w.height for w in self.words]
        center = statistics.median(centers)
        half = statistics.median(heights) / 2
        return center - half, center + half

    def split_at(self, x: int) -> tuple[str, str]:
        """(izquierda, derecha) partiendo por una coordenada X.

        La descripción va a la izquierda y los importes a la derecha; ese es todo
        el truco de leer un ticket.
        """
        ws = sorted(self.words, key=lambda w: w.left)
        left = " ".join(w.text for w in ws if w.left < x)
        right = " ".join(w.text for w in ws if w.left >= x)
        return left, right


def _overlap(a_top: int, a_bottom: int, b_top: int, b_bottom: int) -> int:
    return max(0, min(a_bottom, b_bottom) - max(a_top, b_top))


def group_lines(words: list[Word]) -> list[Line]:
    """Agrupa palabras en líneas físicas por solapamiento vertical.

    Se compara solapamiento y no distancia entre centros a propósito: en un
    ticket conviven tamaños muy distintos (el TOTAL suele ir más grande) y con
    centros hay que elegir un umbral que o parte las líneas altas o junta las
    bajas. El solapamiento se adapta solo.
    """
    if not words:
        return []

    lines: list[Line] = []
    for w in sorted(words, key=lambda w: (w.top, w.left)):
        w_bottom = w.top + w.height
        placed = False
        # Basta mirar las últimas líneas: las palabras llegan ordenadas por Y.
        for line in reversed(lines[-3:]):
            top, bottom = line.band
            need = OVERLAP_RATIO * min(w.height, bottom - top)
            if _overlap(w.top, w_bottom, top, bottom) >= need:
                line.words.append(w)
                placed = True
                break
        if not placed:
            lines.append(Line(words=[w]))

    lines.sort(key=lambda ln: ln.top)
    return lines


def median_line_height(lines: list[Line]) -> float:
    """Alto típico de línea. Escala de referencia para el resto de heurísticas."""
    heights = [ln.height for ln in lines if ln.words]
    return statistics.median(heights) if heights else 0.0


def detect_amount_column(lines: list[Line]) -> int | None:
    """Coordenada X donde empieza la columna de importes, o None si no se ve.

    Los importes van **alineados a la derecha**, así que sus bordes izquierdos se
    apiñan en una banda estrecha. Se busca la palabra con pinta de precio que
    esté más a la derecha en cada línea y se toma la mediana de sus izquierdas:
    la mediana aguanta que alguna línea traiga un precio unitario suelto o que el
    OCR se invente un número en la descripción.

    Devuelve una X un poco a la izquierda de esa mediana, para no cortar por el
    canto justo de los dígitos.
    """
    lefts: list[int] = []
    for line in lines:
        prices = [w for w in line.words if PRICE_RE.match(w.text)]
        if prices:
            lefts.append(max(prices, key=lambda w: w.left).left)

    if len(lefts) < 3:  # con dos coincidencias no hay columna, hay casualidad
        return None

    med = statistics.median(lefts)
    margin = median_line_height(lines) * 0.5
    return max(0, int(med - margin))
