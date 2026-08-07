"""Foto de un ticket → fixture JSON para los tests del parser.

Por qué existe: el parser se desarrolla contra la salida del OCR, no contra
fotos. Guardando esa salida como fixture, los tests corren sin cámara, sin móvil
y sin Tesseract instalado, y cada cadena nueva es un fichero más.

Usa el **mismo** `extract()` que producción a propósito. Un fixture generado con
otro preprocesado probaría un parser contra datos que la app nunca va a ver.

Uso (desde backend/):

    python scripts/make_receipt_fixture.py scripts/receipt_samples/lidl-004 --chain lidl

**Anonimiza antes de escribir.** Un ticket lleva NIF, teléfono, número de factura
y a veces los últimos dígitos de la tarjeta, y estos ficheros sí entran en un
repo público. Se sustituye por relleno de la misma longitud para no alterar la
geometría, que es justo lo que los tests miden.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.receipt_ocr import extract  # noqa: E402

FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "receipts"

FECHA_RE = re.compile(r"^\d{2}[/-]\d{2}[/-]\d{2,4}$")
HORA_RE = re.compile(r"^\d{1,2}:\d{2}(:\d{2})?$")

# Cuántos dígitos tiene que sumar un token para considerarlo un identificador.
#
# Se cuentan **por todo el token, ignorando separadores**, y no con un patrón
# de token entero: los datos reales llegan incrustados (`A-46103834` es un NIF,
# `3630-011-156272` un número de factura, `MIJES-0:105057,` un código de tienda)
# y un `^\d+$` no los ve. Se aprendió fallando.
#
# 6 es seguro para lo que sí queremos conservar: los precios y pesos de un
# ticket nunca llegan a tantos dígitos (`1,414` son 4, `12,50` son 4).
MAX_DIGITOS = 6


def scrub(text: str) -> str:
    """Quita identificadores conservando la longitud.

    La longitud importa: las cajas de las palabras siguen siendo válidas y la
    maquetación —que es justo lo que miden los tests— no se mueve.
    """
    # Ceros y no una fecha falsa creíble: así ni se confunde con un dato real ni
    # dispara el propio guardián de privacidad de los tests.
    if FECHA_RE.match(text):
        return "00/00/0000"
    if HORA_RE.match(text):
        return "00:00"
    if sum(c.isdigit() for c in text) >= MAX_DIGITOS:
        return "".join("0" if c.isdigit() else c for c in text)
    return text


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("images", nargs="+", type=Path)
    ap.add_argument("--chain", default="desconocida", help="mercadona | lidl | aldi | …")
    ap.add_argument("--out", type=Path, default=FIXTURES)
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)

    for path in args.images:
        if not path.is_file():
            print(f"  no existe: {path}", file=sys.stderr)
            continue
        result = extract(path.read_bytes())
        fixture = {
            "chain": args.chain,
            "source": path.name,
            "image_width": result.image_width,
            "image_height": result.image_height,
            "words": [
                {
                    "text": scrub(w.text),
                    "left": w.left,
                    "top": w.top,
                    "width": w.width,
                    "height": w.height,
                    "conf": round(w.conf, 1),
                }
                for w in result.words
            ],
        }
        dest = args.out / f"{path.stem}.json"
        dest.write_text(
            json.dumps(fixture, indent=1, ensure_ascii=False), encoding="utf-8"
        )
        print(f"  {dest.name}: {len(fixture['words'])} palabras")


if __name__ == "__main__":
    main()
