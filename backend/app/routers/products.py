from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Product, User
from app.models.product import ProductSource
from app.schemas.product import ProductCreate, ProductOut, ProductUpdate
from app.services.openfoodfacts import OFFNotFound, fetch_by_barcode, search_by_name

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductOut])
async def search_products(
    q: str = Query(min_length=1),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[Product]:
    # First, search locally
    stmt = (
        select(Product)
        .where(or_(Product.name.ilike(f"%{q}%"), Product.brand.ilike(f"%{q}%")))
        .limit(limit)
    )
    local = list(db.scalars(stmt))

    # If we have results, return them
    if local:
        return local

    # Otherwise, search Open Food Facts
    try:
        off_results = await search_by_name(q, limit=limit)
    except Exception:
        return []

    # Persist OFF results to DB and return
    products = []
    for off in off_results:
        # Check if already exists by barcode
        if off.barcode:
            existing = db.scalar(select(Product).where(Product.barcode == off.barcode))
            if existing:
                products.append(existing)
                continue

        product = Product(
            barcode=off.barcode or None,
            name=off.name,
            brand=off.brand,
            calories_per_100g=off.kcal,
            protein_per_100g=off.protein,
            carbs_per_100g=off.carbs,
            fat_per_100g=off.fat,
            source="openfoodfacts",
        )
        db.add(product)

    if products or off_results:
        db.commit()
        for p in products:
            db.refresh(p)

    return products or [Product(
        barcode=off.barcode or None,
        name=off.name,
        brand=off.brand,
        calories_per_100g=off.kcal,
        protein_per_100g=off.protein,
        carbs_per_100g=off.carbs,
        fat_per_100g=off.fat,
        source="openfoodfacts",
    ) for off in off_results]


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
