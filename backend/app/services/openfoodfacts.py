"""Open Food Facts client. Cache-aside is implemented in the products router:
this module is just the HTTP fetch + normalization."""
from __future__ import annotations

import httpx

from app.config import settings


class OFFNotFound(Exception):
    pass


class OFFProduct:
    __slots__ = ("barcode", "name", "brand", "kcal", "protein", "carbs", "fat")

    def __init__(
        self,
        barcode: str,
        name: str,
        brand: str | None,
        kcal: float,
        protein: float,
        carbs: float,
        fat: float,
    ) -> None:
        self.barcode = barcode
        self.name = name
        self.brand = brand
        self.kcal = kcal
        self.protein = protein
        self.carbs = carbs
        self.fat = fat


def _f(x: object) -> float:
    try:
        return float(x) if x is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


HEADERS = {
    "User-Agent": "Uroboros/0.2 (self-hosted macro tracker; https://github.com/RGVylar/uroboros)"
}


async def search_by_name(query: str, limit: int = 20) -> list[OFFProduct]:
    """Search Open Food Facts by product name."""
    url = "https://es.openfoodfacts.org/cgi/search.pl"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url, headers=HEADERS, params={
            "search_terms": query,
            "search_simple": 1,
            "action": "process",
            "json": 1,
            "page_size": limit,
            "fields": "code,product_name,brands,nutriments",
        })
    if r.status_code != 200:
        return []
    data = r.json()
    products = []
    for p in data.get("products", [])[:limit]:
        try:
            n = p.get("nutriments", {}) or {}
            name = p.get("product_name") or "Unknown"
            products.append(OFFProduct(
                barcode=p.get("code") or "",
                name=name.strip() or "Unknown",
                brand=p.get("brands") or None,
                kcal=_f(n.get("energy-kcal_100g") or n.get("energy-kcal")),
                protein=_f(n.get("proteins_100g")),
                carbs=_f(n.get("carbohydrates_100g")),
                fat=_f(n.get("fat_100g")),
            ))
        except (KeyError, TypeError):
            continue
    return products


async def fetch_by_barcode(barcode: str) -> OFFProduct:
    url = f"{settings.off_base_url}/api/v2/product/{barcode}.json"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url, headers=HEADERS, params={"fields": "code,product_name,brands,nutriments"})
    if r.status_code != 200:
        raise OFFNotFound(barcode)
    data = r.json()
    if data.get("status") != 1:
        raise OFFNotFound(barcode)
    p = data["product"]
    n = p.get("nutriments", {}) or {}
    name = p.get("product_name") or "Unknown"
    return OFFProduct(
        barcode=p.get("code") or barcode,
        name=name.strip() or "Unknown",
        brand=(p.get("brands") or None),
        kcal=_f(n.get("energy-kcal_100g") or n.get("energy-kcal")),
        protein=_f(n.get("proteins_100g")),
        carbs=_f(n.get("carbohydrates_100g")),
        fat=_f(n.get("fat_100g")),
    )
