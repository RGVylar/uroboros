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


@router.get("", response_model=list[ProductOut])
async def search_products(
    q: str = Query(min_length=1),
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Product]:
    # Always search local DB
    stmt = (
        select(Product)
        .where(or_(Product.name.ilike(f"%{q}%"), Product.brand.ilike(f"%{q}%")))
        .offset(offset)
        .limit(limit)
    )
    local = list(db.scalars(stmt))
    local_barcodes = {p.barcode for p in local if p.barcode}
    local_ids = {p.id for p in local}

    # Always also search OFF (in parallel via await)
    try:
        off_results = await search_by_name(q, limit=limit)
    except Exception:
        off_results = []

    # Merge: skip anything already in local results by barcode
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

    # Local first, then extra OFF results
    return local + existing_off + new_off


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
