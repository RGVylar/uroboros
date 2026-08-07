"""De `CAP. RISTRETTO ALUM` a un producto de verdad.

Esta es la parte cara del escaneo de tickets, y no la arregla ningún OCR: aunque
Tesseract lea esa línea con exactitud perfecta, sigue sin decir que son cápsulas
de café. El plan de ataque tiene tres piezas, de más fiable a menos:

1. **Alias**, que es lo que de verdad funciona. Se recuerda lo que el usuario
   corrigió una vez y la siguiente compra sale sola. La primera cuesta; a la
   tercera o cuarta ya cubre la cesta habitual.
2. **Parecido contra lo que ya usa**, que acierta mucho porque la gente compra
   casi siempre lo mismo.
3. **Parecido contra el catálogo entero**, como último recurso.

La observación que lo hace viable: **las abreviaturas de ticket son casi siempre
truncamientos** (`DESN` → `DESNATADA`, `LONCH` → `LONCHAS`). Tratar el prefijo
como coincidencia buena cubre de golpe casi todas sin diccionario. El
diccionario solo hace falta para las contracciones que se comen letras de en
medio, tipo `PLTN` → `PLATANO`.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    ANY_STORE,
    DiaryEntry,
    InventoryItem,
    Product,
    ProductAlias,
    ShoppingListItem,
    User,
    UserFavorite,
)

# Contracciones que NO son prefijos, así que la regla del truncamiento no las
# pilla. Lista corta a propósito: crece viendo tickets reales, no imaginándolos.
ABBREVIATIONS = {
    "PLTN": "PLATANO",
    "PLTNO": "PLATANO",
    "MANTQ": "MANTEQUILLA",
    "MRMLD": "MERMELADA",
    "CHOCO": "CHOCOLATE",
    "REFR": "REFRESCO",
    "YOG": "YOGUR",
    "AGUACT": "AGUACATE",
    "CRV": "CERVEZA",
    "AZUC": "AZUCAR",
    "HUEV": "HUEVOS",
    "TOMT": "TOMATE",
}

# Cantidad al principio de la línea: "2 AGUA MINERAL". Mercadona la pone así.
LEADING_QTY_RE = re.compile(r"^\s*\d+\s+")

# Peso, volumen y formato pegados al nombre: "1L", "450G", "12U", "0,5 L".
UNIT_SUFFIX_RE = re.compile(r"\b\d+[.,]?\d*\s*(KG|G|GR|ML|CL|L|U|UD|UDS|PACK)\b")

NON_ALNUM_RE = re.compile(r"[^A-Z0-9 ]+")

# Por debajo de esto no es un parecido, es una casualidad. Elegido para que la
# pantalla de revisión reciba sugerencias útiles sin inundarse de ruido: una
# sugerencia mala cuesta más de descartar que una ausente de rellenar.
MIN_SCORE = 0.62

# Un prefijo de menos de 3 letras coincide con demasiadas cosas ("CA" está en
# café, carne, calabacín…).
MIN_PREFIX = 3


@dataclass(frozen=True)
class Match:
    product: Product | None
    score: float
    # De dónde salió: 'alias' | 'usados' | 'catalogo' | 'ignorar'. La pantalla de
    # revisión lo usa para decidir qué da por bueno y qué pregunta.
    source: str

    @property
    def is_confident(self) -> bool:
        """Un alias es una decisión que ya tomó el usuario; el parecido es una
        opinión nuestra."""
        return self.source in ("alias", "ignorar")


def strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )


def normalize(text: str) -> str:
    """Texto del ticket → forma canónica para comparar y para indexar.

    Quita lo que varía sin cambiar de qué producto se habla: mayúsculas, tildes,
    la cantidad de delante, el formato del envase y la puntuación.
    """
    out = strip_accents(text).upper()
    out = LEADING_QTY_RE.sub("", out)
    out = UNIT_SUFFIX_RE.sub(" ", out)
    out = NON_ALNUM_RE.sub(" ", out)
    return " ".join(out.split())


def expand(normalized: str) -> str:
    """Aplica el diccionario de contracciones, token a token."""
    return " ".join(ABBREVIATIONS.get(tok, tok) for tok in normalized.split())


def token_similarity(recorte: str, entero: str) -> float:
    """Parecido entre un token del ticket y uno del nombre del producto.

    **El orden importa.** El truncamiento va en una sola dirección: el ticket
    abrevia el producto (`DESN` de `DESNATADA`), nunca al revés. Premiar también
    la dirección contraria hacía que `PAÑALES XXL` prefiriese `Pan de molde` a
    `Pañales talla 4`, porque `PAN` es prefijo de `PAÑALES` por casualidad.

    No es 1.0 porque `LECHE` también es prefijo de `LECHUGA`.
    """
    if recorte == entero:
        return 1.0
    if len(recorte) >= MIN_PREFIX and entero.startswith(recorte):
        return 0.95
    return SequenceMatcher(None, recorte, entero).ratio()


def similarity(raw: str, candidate: str) -> float:
    """Cuánto se parece una línea de ticket a un nombre de producto (0..1).

    Se puntúa por tokens de la línea y no sobre la cadena entera porque las
    longitudes no tienen nada que ver: `LECHE SEM DESN` contra
    `Leche semidesnatada Hacendado 1L` daría un parecido ridículo comparando
    caracteres, y es la misma cosa.

    Cada token pesa **según su longitud**, porque no informan lo mismo. Con
    media simple, `PAÑALES XXL JUNIOR` no llegaba a `Pañales talla 4`: `PAÑALES`
    coincidía exacto pero `XXL` y `JUNIOR` hundían la nota. El sustantivo que
    identifica el producto es casi siempre el token más largo de la línea.
    """
    q = expand(normalize(raw)).split()
    c = expand(normalize(candidate)).split()
    if not q or not c:
        return 0.0
    total = sum(len(qt) for qt in q)
    if total == 0:
        return 0.0

    base = sum(len(qt) * max(token_similarity(qt, ct) for ct in c) for qt in q) / total

    # El primer token es el sustantivo, y manda sobre los adjetivos. Sin esto,
    # `RIOJA BLANCO` casaba con `Arroz blanco cocido` a 0,73 y `SOJA NATURAL`
    # con `Yogur natural` a 0,72: coincidía el modificador y el nombre de la
    # cosa no se parecía en nada. Compartir adjetivo no es ser el mismo
    # producto.
    cabeza = max(token_similarity(q[0], ct) for ct in c)
    return base * (0.5 + 0.5 * cabeza)


def best_match(raw: str, candidates: list[Product], threshold: float = MIN_SCORE):
    """El producto que mejor encaja, o None si ninguno llega al umbral.

    A igualdad de puntuación gana el nombre más corto: entre `Queso` y
    `Queso azul roquefort curado`, lo genérico se equivoca menos.
    """
    scored = [(similarity(raw, p.name), len(p.name), p) for p in candidates]
    scored = [s for s in scored if s[0] >= threshold]
    if not scored:
        return None
    score, _, product = max(scored, key=lambda s: (s[0], -s[1]))
    return product, score


# ── Alias ────────────────────────────────────────────────────────────────────

def find_alias(db: Session, user_id: int, store: str, norm: str) -> ProductAlias | None:
    """El alias del usuario manda sobre el global: es su decisión, no la media."""
    for where in (
        (ProductAlias.user_id == user_id, ProductAlias.store == store),
        (ProductAlias.user_id == user_id, ProductAlias.store == ANY_STORE),
        (ProductAlias.user_id.is_(None), ProductAlias.store == store),
        (ProductAlias.user_id.is_(None), ProductAlias.store == ANY_STORE),
    ):
        alias = db.scalar(
            select(ProductAlias).where(ProductAlias.raw_text_norm == norm, *where)
        )
        if alias is not None:
            return alias
    return None


def remember(
    db: Session,
    user_id: int,
    store: str,
    raw_text: str,
    product_id: int | None,
    kind: str = "product",
) -> ProductAlias:
    """Aprende (o corrige) un alias. No hace commit: decide quien llama.

    Corregir tiene que poder cambiar un alias existente — la primera vez uno se
    equivoca eligiendo, y si el alias viejo mandara para siempre la feature sería
    peor que teclear.
    """
    norm = normalize(raw_text)
    alias = db.scalar(
        select(ProductAlias).where(
            ProductAlias.user_id == user_id,
            ProductAlias.store == store,
            ProductAlias.raw_text_norm == norm,
        )
    )
    if alias is None:
        alias = ProductAlias(
            user_id=user_id,
            store=store,
            raw_text_norm=norm,
            product_id=product_id,
            kind=kind,
            times_seen=1,
        )
        db.add(alias)
    else:
        alias.product_id = product_id
        alias.kind = kind
        alias.times_seen += 1
    return alias


# ── Candidatos ───────────────────────────────────────────────────────────────

def products_in_use(db: Session, user: User, limit: int = 400) -> list[Product]:
    """Lo que este usuario ya usa: diario, favoritos, despensa y lista.

    Es la mejor fuente del emparejador con diferencia, porque una compra se
    parece muchísimo a la anterior. Buscar aquí antes que en el catálogo entero
    acierta más y además evita sugerir productos que no ha visto nunca.
    """
    ids: set[int] = set()
    for stmt in (
        select(DiaryEntry.product_id).where(DiaryEntry.user_id == user.id),
        select(UserFavorite.product_id).where(UserFavorite.user_id == user.id),
        select(InventoryItem.product_id).where(InventoryItem.user_id == user.id),
        select(ShoppingListItem.product_id).where(ShoppingListItem.user_id == user.id),
    ):
        ids.update(pid for pid in db.scalars(stmt) if pid is not None)

    if not ids:
        return []
    return list(db.scalars(select(Product).where(Product.id.in_(list(ids)[:limit]))))


# ── La cascada ───────────────────────────────────────────────────────────────

def match_line(db: Session, user: User, raw_text: str, store: str = ANY_STORE) -> Match:
    """Una línea de ticket → qué producto es, y con cuánta confianza."""
    norm = normalize(raw_text)
    if not norm:
        return Match(product=None, score=0.0, source="ninguno")

    alias = find_alias(db, user.id, store, norm)
    if alias is not None:
        if alias.kind == "ignore":
            return Match(product=None, score=1.0, source="ignorar")
        product = db.get(Product, alias.product_id) if alias.product_id else None
        if product is not None:
            return Match(product=product, score=1.0, source="alias")

    hit = best_match(raw_text, products_in_use(db, user))
    if hit is not None:
        return Match(product=hit[0], score=hit[1], source="usados")

    # El catálogo entero es el último recurso: son productos que este usuario no
    # ha visto nunca, así que la sugerencia vale menos aunque puntúe igual.
    hit = best_match(raw_text, list(db.scalars(select(Product).limit(2000))))
    if hit is not None:
        return Match(product=hit[0], score=hit[1], source="catalogo")

    return Match(product=None, score=0.0, source="ninguno")
