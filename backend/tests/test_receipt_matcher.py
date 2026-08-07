"""Emparejar una línea de ticket con un producto.

Los casos salen de tickets reales medidos (`tests/fixtures/receipts/`), no
inventados: `CAP. RISTRETTO ALUM` y `PLTNO CANARIAS` existen tal cual.

La regla que sostiene el diseño es que **las abreviaturas de ticket son casi
siempre truncamientos**, así que el prefijo puntúa alto y el diccionario solo
cubre las contracciones que se comen letras de en medio.
"""
import pytest

from app.models import ANY_STORE, Product, ProductAlias
from app.models.product import ProductSource
from app.services.receipt_matcher import (
    MIN_SCORE,
    best_match,
    expand,
    find_alias,
    match_line,
    normalize,
    products_in_use,
    remember,
    similarity,
    token_similarity,
)


def make_products(db, *names: str) -> list[Product]:
    out = []
    for name in names:
        p = Product(
            name=name,
            calories_per_100g=100, protein_per_100g=5,
            carbs_per_100g=10, fat_per_100g=2,
            source=ProductSource.manual,
        )
        db.add(p)
        out.append(p)
    db.commit()
    for p in out:
        db.refresh(p)
    return out


# ── Normalizar ───────────────────────────────────────────────────────────────

def test_normalize_quita_tildes_y_pone_mayusculas():
    assert normalize("Jamón serrano") == "JAMON SERRANO"


def test_normalize_quita_la_cantidad_de_delante():
    """Mercadona escribe la cantidad como prefijo: '2 AGUA MINERAL'."""
    assert normalize("2 AGUA MINERAL") == "AGUA MINERAL"


def test_normalize_quita_el_formato_del_envase():
    """El mismo producto en otro tamaño sigue siendo el mismo producto."""
    assert normalize("LECHE SEM DESN 1L") == "LECHE SEM DESN"
    assert normalize("PAN MOLDE 450G") == "PAN MOLDE"
    assert normalize("HUEVOS L 12U") == "HUEVOS L"


def test_normalize_quita_la_puntuacion():
    assert normalize("B.BASURA EXT.C.FACIL") == "B BASURA EXT C FACIL"
    assert normalize("CAP. RISTRETTO ALUM") == "CAP RISTRETTO ALUM"


def test_normalize_colapsa_espacios():
    assert normalize("  ACEITUNA   ANCHOA  ") == "ACEITUNA ANCHOA"


def test_normalize_de_algo_vacio_no_falla():
    assert normalize("") == ""
    assert normalize("...") == ""


def test_expand_aplica_el_diccionario():
    assert expand("PLTNO CANARIAS") == "PLATANO CANARIAS"


def test_expand_deja_en_paz_lo_que_no_conoce():
    assert expand("AGUA MINERAL") == "AGUA MINERAL"


# ── Parecido ─────────────────────────────────────────────────────────────────

def test_un_truncamiento_puntua_alto():
    """`DESN` es `DESNATADA` cortada. Esto es lo que hace innecesario un
    diccionario gigante."""
    assert token_similarity("DESN", "DESNATADA") > 0.9


def test_un_prefijo_muy_corto_no_cuenta_como_truncamiento():
    """'CA' está en café, carne y calabacín: no distingue nada."""
    assert token_similarity("CA", "CAFE") < 0.9


def test_palabras_distintas_puntuan_bajo():
    assert token_similarity("LECHE", "PESCADO") < 0.4


def test_la_linea_abreviada_encuentra_el_producto_completo():
    """El caso que motiva puntuar por tokens: las longitudes no se parecen en
    nada y es la misma cosa."""
    assert similarity("LECHE SEM DESN 1L", "Leche semidesnatada Hacendado 1L") >= MIN_SCORE


def test_lineas_de_productos_distintos_no_se_confunden():
    assert similarity("LECHE SEM DESN 1L", "Pescado congelado") < MIN_SCORE


def test_similarity_con_algo_vacio_es_cero():
    assert similarity("", "Leche") == 0.0
    assert similarity("LECHE", "") == 0.0


def test_best_match_elige_el_mas_parecido(db):
    leche, pan, _ = make_products(db, "Leche semidesnatada", "Pan de molde", "Aceite de oliva")

    hit = best_match("LECHE SEM DESN 1L", [leche, pan])

    assert hit is not None and hit[0].id == leche.id


def test_best_match_devuelve_none_si_nada_llega_al_umbral(db):
    productos = make_products(db, "Aceite de oliva", "Detergente")

    assert best_match("PECHUGA PAVO HORNO", productos) is None


def test_a_igualdad_gana_el_nombre_mas_generico(db):
    """Entre `Queso` y `Queso azul roquefort curado`, equivocarse con el
    genérico cuesta menos."""
    generico, especifico = make_products(db, "Queso", "Queso azul roquefort curado")

    hit = best_match("1 QUESO", [especifico, generico])

    assert hit is not None and hit[0].id == generico.id


# ── Alias ────────────────────────────────────────────────────────────────────

def test_remember_crea_el_alias(db, make_user):
    user = make_user("Ana")
    (producto,) = make_products(db, "Cápsulas café ristretto")

    remember(db, user.id, "mercadona", "CAP. RISTRETTO ALUM", producto.id)
    db.commit()

    alias = find_alias(db, user.id, "mercadona", normalize("CAP. RISTRETTO ALUM"))
    assert alias is not None and alias.product_id == producto.id


def test_remember_corrige_un_alias_ya_existente(db, make_user):
    """A la primera uno elige mal. Si el alias viejo mandara para siempre, esto
    sería peor que teclear."""
    user = make_user("Bea")
    malo, bueno = make_products(db, "Cerveza", "Cápsulas café ristretto")
    remember(db, user.id, "mercadona", "CAP. RISTRETTO ALUM", malo.id)
    db.commit()

    remember(db, user.id, "mercadona", "CAP. RISTRETTO ALUM", bueno.id)
    db.commit()

    alias = find_alias(db, user.id, "mercadona", normalize("CAP. RISTRETTO ALUM"))
    assert alias.product_id == bueno.id
    assert alias.times_seen == 2


def test_el_alias_no_depende_de_como_estuviera_escrito(db, make_user):
    """Se guarda normalizado, así que la cantidad de delante o el formato no
    generan un alias distinto por cada compra."""
    user = make_user("Cris")
    (producto,) = make_products(db, "Leche semidesnatada")
    remember(db, user.id, "mercadona", "2 LECHE SEM DESN 1L", producto.id)
    db.commit()

    alias = find_alias(db, user.id, "mercadona", normalize("1 LECHE SEM DESN"))

    assert alias is not None and alias.product_id == producto.id


def test_el_alias_de_otro_usuario_no_se_usa(db, make_user):
    ana, bea = make_user("Ana"), make_user("Bea")
    (producto,) = make_products(db, "Cerveza")
    remember(db, ana.id, "mercadona", "CRV LATA", producto.id)
    db.commit()

    assert find_alias(db, bea.id, "mercadona", normalize("CRV LATA")) is None


def test_el_alias_propio_gana_al_global(db, make_user):
    """El global es la media de todo el mundo; el propio es su decisión."""
    user = make_user("Ana")
    global_p, mio = make_products(db, "Cerveza rubia", "Cerveza artesana IPA")
    db.add(ProductAlias(user_id=None, store="mercadona",
                        raw_text_norm=normalize("CRV LATA"), product_id=global_p.id))
    remember(db, user.id, "mercadona", "CRV LATA", mio.id)
    db.commit()

    assert find_alias(db, user.id, "mercadona", normalize("CRV LATA")).product_id == mio.id


# ── La cascada ───────────────────────────────────────────────────────────────

def test_match_line_usa_el_alias_y_va_con_confianza(db, make_user):
    user = make_user("Ana")
    (producto,) = make_products(db, "Cápsulas café ristretto")
    remember(db, user.id, "mercadona", "CAP. RISTRETTO ALUM", producto.id)
    db.commit()

    m = match_line(db, user, "CAP. RISTRETTO ALUM", "mercadona")

    assert m.product.id == producto.id
    assert m.source == "alias"
    assert m.is_confident


def test_match_line_respeta_lo_marcado_como_no_es_comida(db, make_user):
    """Bolsas de basura, pañales, discos desmaquillantes. Sin poder recordarlo,
    se descartarían las mismas líneas en cada compra."""
    user = make_user("Ana")
    remember(db, user.id, "mercadona", "B.BASURA EXT.C.FACIL", None, kind="ignore")
    db.commit()

    m = match_line(db, user, "B.BASURA EXT.C.FACIL", "mercadona")

    assert m.product is None
    assert m.source == "ignorar"
    assert m.is_confident


def test_match_line_sin_alias_tira_del_catalogo(db, make_user):
    user = make_user("Ana")
    (leche,) = make_products(db, "Leche semidesnatada")

    m = match_line(db, user, "LECHE SEM DESN 1L", "mercadona")

    assert m.product.id == leche.id
    assert m.source == "catalogo"
    assert not m.is_confident, "una opinión nuestra no es una decisión suya"


def test_match_line_prefiere_lo_que_el_usuario_ya_usa(db, make_user, make_product):
    """Una compra se parece muchísimo a la anterior, así que lo ya usado acierta
    más que el catálogo entero — y no sugiere cosas que no ha visto nunca."""
    from app.models import UserFavorite

    user = make_user("Ana")
    catalogo, usado = make_products(db, "Queso de cabra", "Queso curado")
    db.add(UserFavorite(user_id=user.id, product_id=usado.id))
    db.commit()

    m = match_line(db, user, "1 QUESO", "mercadona")

    assert m.source == "usados"
    assert m.product.id == usado.id


def test_match_line_con_una_linea_ilegible_no_inventa(db, make_user):
    make_products(db, "Leche semidesnatada")
    user = make_user("Ana")

    m = match_line(db, user, "...", "mercadona")

    assert m.product is None
    assert m.source == "ninguno"


def test_products_in_use_vacio_cuando_el_usuario_no_tiene_nada(db, make_user):
    make_products(db, "Leche semidesnatada")

    assert products_in_use(db, make_user("Nueva")) == []


@pytest.mark.parametrize(
    "linea,producto",
    [
        ("1 CEREAL TRIGO ENTERO", "Cereales de trigo integral"),
        ("PLTNO CANARIAS", "Plátano de Canarias"),
        ("1 LACÓN HORNO", "Lacón al horno"),
        ("Jamón serrano", "Jamón serrano en lonchas"),
        ("1 SALSA TRUFA", "Salsa de trufa"),
    ],
)
def test_lineas_reales_de_ticket_encuentran_su_producto(db, linea, producto):
    """Todas estas salen de los tickets medidos, tal cual venían."""
    (p,) = make_products(db, producto)

    hit = best_match(linea, [p])

    assert hit is not None, f"{linea!r} no llegó a {producto!r}"


def test_el_truncamiento_solo_cuenta_en_una_direccion():
    """Regresión: `PAÑALES XXL` prefería `Pan de molde` a `Pañales talla 4`,
    porque `PAN` es prefijo de `PAÑALES` por casualidad. El ticket abrevia el
    producto, nunca al revés."""
    assert similarity("Pañales XXL Junior", "Pañales talla 4") > similarity(
        "Pañales XXL Junior", "Pan de molde integral"
    )


def test_el_token_largo_pesa_mas_que_el_ruido():
    """Con media simple, `XXL` y `JUNIOR` hundían un `PAÑALES` que coincidía
    exacto. El sustantivo que identifica el producto es casi siempre el token
    más largo."""
    con_ruido = similarity("PAÑALES XXL JUNIOR", "Pañales talla 4")
    solo = similarity("PAÑALES", "Pañales talla 4")

    assert solo > con_ruido > 0.45, "el ruido resta, pero no debe arrasar"
