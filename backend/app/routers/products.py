from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Product, User
from app.models.product import ProductSource
from app.schemas.product import ProductCreate, ProductOut, ProductUpdate, RecommendedProduct, FrequentProduct
from app.services.openfoodfacts import OFFNotFound, fetch_by_barcode, search_by_name
from app.services.recommendations import get_recommendations, get_frequently_used_products, FrequentlyUsedProduct

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/recommendations", response_model=list[RecommendedProduct])
def get_product_recommendations(
    day: date | None = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if day is None:
        day = datetime.now(timezone.utc).date()

    recommendations = get_recommendations(db, user, day)
    return [
        {
            "product": ProductOut.model_validate(rec.product),
            "suggested_grams": rec.suggested_grams,
            "estimated_calories": rec.estimated_calories,
            "reason": rec.reason,
        }
        for rec in recommendations
    ]


@router.get("/frequent", response_model=list[FrequentProduct])
def get_frequent_products(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get user's most frequently logged products for quick access"""
    frequent = get_frequently_used_products(db, user, limit)
    return [
        {
            "product": ProductOut.model_validate(f.product),
            "count": f.count,
        }
        for f in frequent
    ]


@router.get("/barcode/{barcode}", response_model=ProductOut)
async def get_or_fetch_by_barcode(
    barcode: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Product:
    """Cache-aside: return local product if known, otherwise fetch from
    Open Food Facts and persist."""
    existing = db.scalar(select(Product).where(Product.barcode == barcode))
    if existing:
        return existing

    try:
        off = await fetch_by_barcode(barcode)
    except OFFNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")

    product = Product(
        barcode=off.barcode,
        name=off.name,
        brand=off.brand,
        calories_per_100g=off.kcal,
        protein_per_100g=off.protein,
        carbs_per_100g=off.carbs,
        fat_per_100g=off.fat,
        source=ProductSource.openfoodfacts,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def _relevance(name: str, brand: str | None, q: str) -> int:
    """Score a product against a search query. Higher = more relevant."""
    nl = name.lower()
    ql = q.lower()

    if nl == ql:
        return 100                                    # exact name match
    if nl.startswith(ql + " ") or nl.startswith(ql + ","):
        return 90                                     # name starts with query
    if nl.startswith(ql):
        return 85                                     # name starts with query (no separator)
    words = nl.split()
    if words and words[0] == ql:
        return 80                                     # first word is exactly query
    if any(w == ql for w in words):
        return 70                                     # any word is exactly query
    if any(w.startswith(ql) for w in words):
        return 60                                     # any word starts with query
    if ql in nl:
        return 40                                     # query contained anywhere in name
    bl = (brand or "").lower()
    if ql in bl:
        return 15                                     # only brand matches
    return 0


@router.get("", response_model=list[ProductOut])
async def search_products(
    q: str = Query(min_length=1),
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Product]:
    # Fetch all local matches (no DB-level limit — we rank in Python)
    stmt = (
        select(Product)
        .where(or_(Product.name.ilike(f"%{q}%"), Product.brand.ilike(f"%{q}%")))
    )
    local_all = list(db.scalars(stmt))

    # Sort by relevance, then alphabetically as tiebreaker
    local_all.sort(key=lambda p: (-_relevance(p.name, p.brand, q), p.name.lower()))

    # Paginate on the ranked list
    local = local_all[offset: offset + limit]
    local_barcodes = {p.barcode for p in local_all if p.barcode}
    local_ids = {p.id for p in local_all}

    # Only call OFF if there's room left on this page
    remaining = limit - len(local)
    if remaining <= 0:
        return local

    try:
        off_results = await search_by_name(q, limit=limit)
    except Exception:
        off_results = []

    # Merge OFF results, deduplicating by barcode
    new_off: list[Product] = []
    existing_off: list[Product] = []
    for off in off_results:
        if off.barcode and off.barcode in local_barcodes:
            continue  # already represented in local
        if off.barcode:
            existing = db.scalar(select(Product).where(Product.barcode == off.barcode))
            if existing:
                if existing.id not in local_ids:
                    existing_off.append(existing)
                continue
        p = Product(
            barcode=off.barcode or None,
            name=off.name,
            brand=off.brand,
            calories_per_100g=off.kcal,
            protein_per_100g=off.protein,
            carbs_per_100g=off.carbs,
            fat_per_100g=off.fat,
            source=ProductSource.openfoodfacts,
        )
        db.add(p)
        new_off.append(p)

    if new_off:
        db.commit()
        for p in new_off:
            db.refresh(p)

    # Sort OFF results by relevance too before appending
    off_combined = existing_off + new_off
    off_combined.sort(key=lambda p: (-_relevance(p.name, p.brand, q), p.name.lower()))

    return local + off_combined[:remaining]


@router.get("/{product_id}", response_model=ProductOut)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Product:
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    return product


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Product:
    if payload.barcode:
        existing = db.scalar(select(Product).where(Product.barcode == payload.barcode))
        if existing:
            raise HTTPException(status.HTTP_409_CONFLICT, "Barcode already exists")
    product = Product(
        **payload.model_dump(),
        source=ProductSource.manual,
        edited_by=user.id,
        edited_at=datetime.now(timezone.utc),
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Product:
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(product, k, v)
    if data:
        # mark as edited only if it was OFF-sourced; manual stays manual
        if product.source == ProductSource.openfoodfacts:
            product.source = ProductSource.edited
        product.edited_by = user.id
        product.edited_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(product)
    return product
