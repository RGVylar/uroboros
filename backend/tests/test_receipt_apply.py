"""Volcar un ticket revisado a la despensa, y deshacerlo.

Lo que más se prueba aquí es el **deshacer**, porque es lo que hace tolerable
equivocarse: una importación mete diez cosas de golpe, así que cuando sale mal
sale mal diez veces.
"""
import pytest
from sqlalchemy import select

from app.models import InventoryItem, InventoryLog, ProductAlias, ReceiptImport
from app.models.product import Product, ProductSource
from app.services.receipt_apply import LineToApply, apply_receipt, undo_receipt
from app.services.receipt_matcher import normalize

from conftest import API, auth


@pytest.fixture()
def producto(db):
    p = Product(
        name="Leche semidesnatada",
        calories_per_100g=46, protein_per_100g=3.2, carbs_per_100g=4.7, fat_per_100g=1.6,
        source=ProductSource.manual,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@pytest.fixture()
def flagged(db, make_user):
    user = make_user("Ana")
    user.feature_flags = ["receipt_scan"]
    db.commit()
    return user


def stock(db, user, product) -> InventoryItem | None:
    return db.scalar(
        select(InventoryItem).where(
            InventoryItem.user_id == user.id, InventoryItem.product_id == product.id
        )
    )


# ── Aplicar ──────────────────────────────────────────────────────────────────

def test_una_linea_confirmada_entra_en_la_despensa(db, flagged, producto):
    apply_receipt(db, flagged, "mercadona", [
        LineToApply(raw="LECHE SEM DESN 1L", action="add", product_id=producto.id, quantity=2)
    ])

    item = stock(db, flagged, producto)
    assert item is not None and item.quantity_base == 2


def test_aplicar_deja_log_de_compra_atado_a_su_tanda(db, flagged, producto):
    """Sin el vínculo, deshacer sería imposible."""
    tanda = apply_receipt(db, flagged, "mercadona", [
        LineToApply(raw="LECHE", action="add", product_id=producto.id, quantity=1)
    ])

    log = db.scalar(select(InventoryLog).where(InventoryLog.receipt_import_id == tanda.id))
    assert log is not None
    assert log.log_type == "purchase"


def test_aplicar_aprende_el_alias(db, flagged, producto):
    """Es todo el truco: la próxima compra ya no pregunta."""
    apply_receipt(db, flagged, "mercadona", [
        LineToApply(raw="LECHE SEM DESN 1L", action="add", product_id=producto.id)
    ])

    alias = db.scalar(
        select(ProductAlias).where(ProductAlias.raw_text_norm == normalize("LECHE SEM DESN 1L"))
    )
    assert alias is not None and alias.product_id == producto.id


def test_ignorar_aprende_que_eso_no_es_comida(db, flagged):
    """Bolsas de basura, pañales. Sin recordarlo se descartarían cada vez."""
    apply_receipt(db, flagged, "mercadona", [
        LineToApply(raw="B.BASURA EXT.C.FACIL", action="ignore")
    ])

    alias = db.scalar(select(ProductAlias).where(ProductAlias.kind == "ignore"))
    assert alias is not None and alias.product_id is None


def test_saltar_una_linea_no_deja_rastro(db, flagged):
    """Saltar es 'no sé', no 'no es comida'. Aprenderlo la escondería la próxima
    vez, que es justo lo contrario de lo que el usuario quiso."""
    apply_receipt(db, flagged, "mercadona", [LineToApply(raw="RAREZA", action="skip")])

    assert db.scalar(select(ProductAlias)) is None


def test_solo_cuentan_las_lineas_realmente_aplicadas(db, flagged, producto):
    tanda = apply_receipt(db, flagged, "mercadona", [
        LineToApply(raw="LECHE", action="add", product_id=producto.id),
        LineToApply(raw="BOLSAS", action="ignore"),
        LineToApply(raw="RARO", action="skip"),
    ])

    assert tanda.line_count == 1


def test_dos_tickets_suman_stock_en_vez_de_pisarlo(db, flagged, producto):
    apply_receipt(db, flagged, "mercadona", [
        LineToApply(raw="LECHE", action="add", product_id=producto.id, quantity=2)
    ])
    apply_receipt(db, flagged, "mercadona", [
        LineToApply(raw="LECHE", action="add", product_id=producto.id, quantity=3)
    ])

    assert stock(db, flagged, producto).quantity_base == 5


# ── Deshacer ─────────────────────────────────────────────────────────────────

def test_deshacer_devuelve_el_stock_a_como_estaba(db, flagged, producto):
    apply_receipt(db, flagged, "mercadona", [
        LineToApply(raw="LECHE", action="add", product_id=producto.id, quantity=4)
    ])
    tanda = apply_receipt(db, flagged, "mercadona", [
        LineToApply(raw="LECHE", action="add", product_id=producto.id, quantity=3)
    ])

    assert undo_receipt(db, flagged, tanda.id) is True
    assert stock(db, flagged, producto).quantity_base == 4


def test_deshacer_resta_lo_que_sumo_y_no_lo_que_hay(db, flagged, producto):
    """Entre importar y deshacer el usuario ha podido comerse parte de lo que
    compró. Se resta lo que aportó la tanda; si eso lo deja a cero, desaparece.
    """
    apply_receipt(db, flagged, "mercadona", [
        LineToApply(raw="LECHE", action="add", product_id=producto.id, quantity=5)
    ])
    tanda = apply_receipt(db, flagged, "mercadona", [
        LineToApply(raw="LECHE", action="add", product_id=producto.id, quantity=2)
    ])
    item = stock(db, flagged, producto)
    item.quantity_base = 4          # se ha consumido parte
    item.quantity_g = 4
    db.commit()

    undo_receipt(db, flagged, tanda.id)

    assert stock(db, flagged, producto).quantity_base == 2


def test_deshacer_nunca_deja_stock_negativo(db, flagged, producto):
    """Restar más de lo que hay no puede dar un número imposible."""
    tanda = apply_receipt(db, flagged, "mercadona", [
        LineToApply(raw="LECHE", action="add", product_id=producto.id, quantity=2)
    ])
    item = stock(db, flagged, producto)
    item.quantity_base = 0
    item.quantity_g = 0
    db.commit()

    undo_receipt(db, flagged, tanda.id)

    item = stock(db, flagged, producto)
    assert item is None or (item.quantity_base >= 0 and item.quantity_g >= 0)


def test_deshacer_borra_la_tanda_y_sus_logs(db, flagged, producto):
    tanda = apply_receipt(db, flagged, "mercadona", [
        LineToApply(raw="LECHE", action="add", product_id=producto.id)
    ])

    undo_receipt(db, flagged, tanda.id)

    assert db.scalar(select(ReceiptImport)) is None
    assert db.scalar(select(InventoryLog).where(InventoryLog.receipt_import_id.isnot(None))) is None


def test_deshacer_no_toca_otras_compras(db, flagged, producto):
    """Un log de compra hecho a mano no pertenece a ninguna tanda."""
    db.add(InventoryLog(user_id=flagged.id, product_id=producto.id, quantity_change=1,
                        unit="unit", quantity_base_change=1000, log_type="purchase"))
    tanda = apply_receipt(db, flagged, "mercadona", [
        LineToApply(raw="LECHE", action="add", product_id=producto.id)
    ])
    db.commit()

    undo_receipt(db, flagged, tanda.id)

    assert db.scalar(select(InventoryLog)) is not None, "el log manual sigue ahí"


def test_no_se_puede_deshacer_la_tanda_de_otro(db, flagged, make_user, producto):
    tanda = apply_receipt(db, flagged, "mercadona", [
        LineToApply(raw="LECHE", action="add", product_id=producto.id)
    ])
    otro = make_user("Bea")

    assert undo_receipt(db, otro, tanda.id) is False
    assert db.scalar(select(ReceiptImport)) is not None


def test_deshacer_algo_que_no_existe_devuelve_false(db, flagged):
    assert undo_receipt(db, flagged, 9999) is False


# ── Por HTTP ─────────────────────────────────────────────────────────────────

def test_apply_por_api(client, db, flagged, producto):
    r = client.post(f"{API}/receipts/apply", headers=auth(flagged), json={
        "store": "mercadona",
        "lines": [{"raw": "LECHE SEM DESN 1L", "action": "add",
                   "product_id": producto.id, "quantity": 2, "unit": "unit"}],
    })

    assert r.status_code == 201
    assert r.json()["applied"] == 1


def test_apply_sin_flag_da_404(client, make_user, producto):
    r = client.post(f"{API}/receipts/apply", headers=auth(make_user("Sin")), json={
        "lines": [{"raw": "X", "action": "add", "product_id": producto.id}]
    })

    assert r.status_code == 404


@pytest.mark.parametrize("mala", [
    {"raw": "X", "action": "inventada", "product_id": 1},
    {"raw": "X", "action": "add", "product_id": 1, "unit": "toneladas"},
    {"raw": "X", "action": "add", "product_id": 1, "location": "garaje"},
    {"raw": "X", "action": "add"},  # sin producto
])
def test_el_backend_no_se_fia_del_cliente(client, db, flagged, mala):
    r = client.post(f"{API}/receipts/apply", headers=auth(flagged),
                    json={"lines": [mala]})

    assert r.status_code == 422


def test_undo_por_api(client, db, flagged, producto):
    tanda = apply_receipt(db, flagged, "mercadona", [
        LineToApply(raw="LECHE", action="add", product_id=producto.id)
    ])

    r = client.delete(f"{API}/receipts/imports/{tanda.id}", headers=auth(flagged))

    assert r.status_code == 204
    assert db.scalar(select(ReceiptImport)) is None


def test_undo_de_algo_ajeno_da_404(client, db, flagged, make_user, producto):
    tanda = apply_receipt(db, flagged, "mercadona", [
        LineToApply(raw="LECHE", action="add", product_id=producto.id)
    ])
    otro = make_user("Bea")
    otro.feature_flags = ["receipt_scan"]
    db.commit()

    r = client.delete(f"{API}/receipts/imports/{tanda.id}", headers=auth(otro))

    assert r.status_code == 404


def test_deshacer_no_deja_productos_fantasma_a_cero(db, flagged, producto):
    """Regresión vista en la app: tras deshacer, la despensa seguía listando los
    productos con cantidad 0. Deshacer tiene que dejarlo como si no hubiera
    pasado; para 'esto lo quiero comprar' ya está la lista de la compra."""
    tanda = apply_receipt(db, flagged, "mercadona", [
        LineToApply(raw="LECHE", action="add", product_id=producto.id, quantity=2)
    ])

    undo_receipt(db, flagged, tanda.id)

    assert stock(db, flagged, producto) is None


def test_deshacer_conserva_el_producto_si_aun_queda_stock(db, flagged, producto):
    """Solo desaparece lo que se queda a cero: lo que ya había es suyo."""
    apply_receipt(db, flagged, "mercadona", [
        LineToApply(raw="LECHE", action="add", product_id=producto.id, quantity=4)
    ])
    tanda = apply_receipt(db, flagged, "mercadona", [
        LineToApply(raw="LECHE", action="add", product_id=producto.id, quantity=3)
    ])

    undo_receipt(db, flagged, tanda.id)

    item = stock(db, flagged, producto)
    assert item is not None and item.quantity_base == 4
