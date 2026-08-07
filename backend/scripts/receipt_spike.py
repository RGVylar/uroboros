"""Paso 0 del PLAN_ticket_despensa: ¿lee Tesseract un ticket de compra?

Toda la fase A depende de esta respuesta, así que conviene contestarla con datos
y no con una corazonada. Este script coge fotos de tickets, las pasa por varias
combinaciones de preprocesado y modo de segmentación, y saca una tabla para ver
cuál gana.

Uso:

    python backend/scripts/receipt_spike.py

Mete las fotos en `backend/scripts/receipt_samples/` (ignorada por git: el repo
es público y un ticket lleva comercio, fecha, hora y a veces los últimos dígitos
de la tarjeta).

Requiere el binario de Tesseract con el idioma español:

    winget install UB-Mannheim.TesseractOCR

El instalador de UB Mannheim **no** trae español, y su carpeta `tessdata` está en
`Program Files`, que necesita admin para escribir. Por eso el script busca
también un tessdata propio en `%LOCALAPPDATA%\\Tesseract-OCR\\tessdata`, donde se
puede dejar `spa.traineddata` sin elevar nada. Se descarga de:

    https://github.com/tesseract-ocr/tessdata_best/raw/main/spa.traineddata

Copia ahí también `eng.traineddata` y `osd.traineddata` desde la instalación, o
Tesseract no los encontrará al usar esa carpeta.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
DEFAULT_SAMPLES = HERE / "receipt_samples"
DEFAULT_OUT = HERE / "receipt_spike_out"

# tessdata de usuario, para no necesitar admin (ver docstring). Si existe y tiene
# español, gana sobre el de la instalación.
USER_TESSDATA = Path(os.environ.get("LOCALAPPDATA", "")) / "Tesseract-OCR" / "tessdata"

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".heic", ".webp", ".bmp", ".tif", ".tiff"}

# psm 4 = una columna de texto con tamaños variables; psm 6 = un bloque uniforme.
# Son los dos candidatos razonables para un ticket. El resto de modos van de
# líneas sueltas o de páginas con columnas, que no es el caso.
PSM_MODES = (4, 6)

# Un importe al final de la línea: "1,29", "12.50", "4,25 B". Es la señal de que
# Tesseract no solo ha leído letras sino que ha respetado la estructura del
# ticket, que es lo que de verdad necesita el parser.
#
# La letra final es el tipo de IVA, y Lidl la imprime en cada línea. Sin
# contemplarla, un ticket de Lidl puntuaría 0 y parecería ilegible cuando en
# realidad se ha leído entero.
PRICE_RE = re.compile(r"\d+[.,]\d{2}\s*€?\s*[A-C]?\s*$")


WINDOWS_FALLBACK = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")


def check_tesseract(lang: str, tessdata: Path | None) -> tuple[str, Path | None]:
    """(binario, tessdata a usar). Aborta si falta el binario; avisa si falta el idioma.

    El PATH no se refresca en una terminal ya abierta después de instalar, así
    que probamos también la ruta por defecto de Windows antes de rendirnos.
    """
    exe = shutil.which("tesseract")
    if exe is None and WINDOWS_FALLBACK.exists():
        exe = str(WINDOWS_FALLBACK)
    if exe is None:
        sys.exit(
            "No encuentro 'tesseract'.\n"
            "  winget install UB-Mannheim.TesseractOCR\n"
            "Y abre una terminal nueva después (el PATH no se refresca solo)."
        )

    def langs_in(td: Path | None) -> set[str]:
        cmd = [exe, "--list-langs"]
        if td is not None:
            cmd += ["--tessdata-dir", str(td)]
        return set(subprocess.run(cmd, capture_output=True, text=True).stdout.split())

    # Explícito manda; si no, el de usuario sólo si aporta el idioma que falta.
    if tessdata is None:
        if lang not in langs_in(None) and USER_TESSDATA.is_dir() and lang in langs_in(USER_TESSDATA):
            tessdata = USER_TESSDATA

    if lang not in langs_in(tessdata):
        print(
            f"AVISO: falta el idioma '{lang}'. Con un ticket en español el inglés lee\n"
            f"       bastante peor, así que el resultado del spike NO sería concluyente.\n"
            f"       Deja spa.traineddata en {USER_TESSDATA}\n",
            file=sys.stderr,
        )
    return exe, tessdata


def otsu_threshold(gray: Image.Image) -> int:
    """Umbral de Otsu a partir del histograma.

    El papel térmico se decolora de forma desigual, así que un umbral fijo
    (128) borra media mitad del ticket. Otsu lo calcula por imagen, y es la
    palanca que más mueve la aguja aquí — más que ninguna otra cosa que haga
    este script.
    """
    hist = gray.histogram()[:256]
    total = sum(hist)
    if total == 0:
        return 128
    sum_all = sum(i * h for i, h in enumerate(hist))
    sum_bg = 0.0
    weight_bg = 0
    best_var, best_t = -1.0, 128
    for t in range(256):
        weight_bg += hist[t]
        if weight_bg == 0:
            continue
        weight_fg = total - weight_bg
        if weight_fg == 0:
            break
        sum_bg += t * hist[t]
        mean_bg = sum_bg / weight_bg
        mean_fg = (sum_all - sum_bg) / weight_fg
        var = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
        if var > best_var:
            best_var, best_t = var, t
    return best_t


def variants(path: Path) -> dict[str, Image.Image]:
    """Las cuatro versiones que compite el spike.

    De menos a más agresiva. Si 'raw' ya va bien, el preprocesado sobra; si solo
    gana 'otsu_2x', entonces el pipeline de producción tiene que hacer eso.
    """
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)  # la foto del móvil viene rotada

    gray = ImageOps.autocontrast(img.convert("L"))
    t = otsu_threshold(gray)
    otsu = gray.point(lambda p, t=t: 255 if p > t else 0, mode="1")

    # Tesseract quiere unos 300 ppp. Una foto de ticket a pantalla completa se
    # queda corta de altura de letra, y duplicar antes de umbralizar suele dar
    # más que cualquier otro ajuste.
    big = gray.resize((gray.width * 2, gray.height * 2), Image.LANCZOS)
    t_big = otsu_threshold(big)
    otsu_2x = big.point(lambda p, t=t_big: 255 if p > t else 0, mode="1")

    return {"raw": img, "gray": gray, "otsu": otsu, "otsu_2x": otsu_2x}


def run_tesseract(
    exe: str, img: Image.Image, psm: int, lang: str, tessdata: Path | None
) -> tuple[str, str]:
    """(texto, tsv). El TSV trae las cajas por palabra, que es lo que el parser
    de verdad va a consumir — el texto plano aquí es solo para poder mirarlo."""
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "in.png"
        img.convert("L").save(src)
        out_base = Path(tmp) / "out"
        results = []
        for fmt in ("txt", "tsv"):
            cmd = [exe, str(src), str(out_base), "-l", lang, "--psm", str(psm)]
            if tessdata is not None:
                cmd += ["--tessdata-dir", str(tessdata)]
            subprocess.run(cmd + [fmt], capture_output=True, check=False)
            produced = out_base.with_suffix(f".{fmt}")
            results.append(produced.read_text(encoding="utf-8", errors="replace")
                           if produced.exists() else "")
        return results[0], results[1]


def score(text: str) -> tuple[int, int, int]:
    """(caracteres, líneas con algo, líneas que acaban en importe).

    La tercera es la que importa. Un OCR puede escupir mucho texto y no haber
    entendido ni una línea del ticket; si acaba en un importe, es que ha leído
    la línea entera con su precio a la derecha.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    with_price = sum(1 for ln in lines if PRICE_RE.search(ln))
    return len(text), len(lines), with_price


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--samples", type=Path, default=DEFAULT_SAMPLES)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--lang", default="spa")
    ap.add_argument("--tessdata", type=Path, default=None)
    args = ap.parse_args()

    exe, tessdata = check_tesseract(args.lang, args.tessdata)

    if not args.samples.is_dir():
        args.samples.mkdir(parents=True, exist_ok=True)
        sys.exit(f"Creada {args.samples}. Mete ahí las fotos de tickets y repite.")

    # Sin filtrar por extensión: un fichero descargado del móvil o del chat llega
    # a menudo sin sufijo, y saltárselo en silencio es peor que intentar abrirlo
    # y fallar. Pillow decide, no el nombre.
    images = sorted(p for p in args.samples.iterdir() if p.is_file())
    if not images:
        sys.exit(f"No hay ficheros en {args.samples}.")

    args.out.mkdir(parents=True, exist_ok=True)
    rows = []

    for path in images:
        print(f"\n{path.name}")
        try:
            vs = variants(path)
        except Exception as e:
            hint = ""
            if path.suffix.lower() == ".heic":
                hint = "  (HEIC del iPhone: hace falta 'pip install pillow-heif')"
            print(f"  no se pudo abrir: {e}{hint}")
            continue

        for vname, img in vs.items():
            for psm in PSM_MODES:
                text, tsv = run_tesseract(exe, img, psm, args.lang, tessdata)
                chars, lines, priced = score(text)
                rows.append((path.name, vname, psm, chars, lines, priced))
                print(f"  {vname:<8} psm{psm}  {lines:>3} líneas, {priced:>3} con importe")

                stem = f"{path.stem}.{vname}.psm{psm}"
                (args.out / f"{stem}.txt").write_text(text, encoding="utf-8")
                (args.out / f"{stem}.tsv").write_text(tsv, encoding="utf-8")

    if not rows:
        return

    rows.sort(key=lambda r: r[5], reverse=True)
    print("\n" + "=" * 60)
    print("MEJORES COMBINACIONES (por líneas con importe)")
    print("=" * 60)
    for name, vname, psm, chars, lines, priced in rows[:10]:
        print(f"  {priced:>3} importes | {lines:>3} líneas | {vname}/psm{psm} | {name}")

    by_combo: dict[tuple[str, int], list[int]] = {}
    for _, vname, psm, _, _, priced in rows:
        by_combo.setdefault((vname, psm), []).append(priced)
    print("\nMEDIA POR COMBINACIÓN (esto es lo que decide el preprocesado)")
    for (vname, psm), vals in sorted(
        by_combo.items(), key=lambda kv: sum(kv[1]) / len(kv[1]), reverse=True
    ):
        print(f"  {sum(vals) / len(vals):>5.1f} importes/ticket | {vname}/psm{psm}")

    (args.out / "summary.json").write_text(
        json.dumps(
            [
                {"image": n, "variant": v, "psm": p, "chars": c, "lines": l, "priced": pr}
                for n, v, p, c, l, pr in rows
            ],
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"\nVolcado completo en {args.out}")
    print("Míralo con tus ojos: el número dice si lee, no si lee BIEN.")


if __name__ == "__main__":
    main()
