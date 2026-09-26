"""Open Food Facts client. Cache-aside is implemented in the products router:
this module is just the HTTP fetch + normalization."""
from __future__ import annotations

import httpx

from app.config import settings


class OFFNotFound(Exception):
    pass


class OFFProduct:
    __slots__ = ("barcode", "name", "brand", "kcal", "protein", "carbs", "fat", "ingredients_text", "allergens")

    def __init__(
        self,
        barcode: str,
        name: str,
        brand: str | None,
        kcal: float,
        protein: float,
        carbs: float,
        fat: float,
        ingredients_text: str | None = None,
        allergens: list[str] | None = None,
    ) -> None:
        self.barcode = barcode
        self.name = name
        self.brand = brand
        self.kcal = kcal
        self.protein = protein
        self.carbs = carbs
        self.fat = fat
        self.ingredients_text = ingredients_text or ""
        self.allergens = allergens or []


_ALLERGEN_SKIP = {"none", "unknown", ""}


def _parse_allergens(allergens_tags: object) -> list[str]:
    """Normalize OFF allergens_tags to plain English keys.
    Input:  ['en:milk', 'en:nuts', 'fr:alcool', 'en:none']
    Output: ['milk', 'nuts', 'alcool']
    Strips language prefixes and filters out 'none'/'unknown' sentinel values.
    """
    if not isinstance(allergens_tags, list):
        return []
    result = []
    seen: set[str] = set()
    for tag in allergens_tags:
        if not isinstance(tag, str):
            continue
        key = tag.split(":")[-1] if ":" in tag else tag
        if key and key not in seen and key not in _ALLERGEN_SKIP:
            result.append(key)
            seen.add(key)
    return result


def _f(x: object) -> float:
    try:
        return float(x) if x is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


_NUTRITION_KEYS = (
    "energy-kcal_100g", "energy-kj_100g", "energy_100g",
    "proteins_100g", "carbohydrates_100g", "fat_100g",
)


def has_nutrition(n: dict) -> bool:
    return any(n.get(k) is not None for k in _NUTRITION_KEYS)


def kcal_per_100g(n: dict) -> float:
    """Muchas fichas de OFF traen la energía solo en kJ, o las kcal a 0 con los
    macros rellenos; leer solo `energy-kcal_100g` las guardaba a 0 kcal."""
    if n.get("energy-kcal_100g") is not None:
        kcal = _f(n.get("energy-kcal_100g"))
    elif n.get("energy-kj_100g") is not None:
        kcal = _f(n.get("energy-kj_100g")) / 4.184
    elif n.get("energy_100g") is not None:  # en OFF, energy_100g va en kJ
        kcal = _f(n.get("energy_100g")) / 4.184
    else:
        kcal = _f(n.get("energy-kcal"))
    if kcal <= 0:
        kcal = macro_kcal(_f(n.get("proteins_100g")), _f(n.get("carbohydrates_100g")), _f(n.get("fat_100g")))
    return round(kcal, 1)


def macro_kcal(protein: float, carbs: float, fat: float) -> float:
    return 4 * protein + 4 * carbs + 9 * fat


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
            "fields": "code,product_name,brands,nutriments,ingredients_text,allergens_tags",
        })
    if r.status_code != 200:
        return []
    data = r.json()
    products = []
    for p in data.get("products", [])[:limit]:
        try:
            n = p.get("nutriments", {}) or {}
            name = (p.get("product_name") or "").strip()
            # Sin nombre o sin ningún dato nutricional no hay nada que registrar:
            # en la búsqueda solo sale como ruido a 0 kcal.
            if not name or not has_nutrition(n):
                continue
            products.append(OFFProduct(
                barcode=p.get("code") or "",
                name=name,
                brand=p.get("brands") or None,
                kcal=kcal_per_100g(n),
                protein=_f(n.get("proteins_100g")),
                carbs=_f(n.get("carbohydrates_100g")),
                fat=_f(n.get("fat_100g")),
                ingredients_text=p.get("ingredients_text") or "",
                allergens=_parse_allergens(p.get("allergens_tags")),
            ))
        except (KeyError, TypeError):
            continue
    return products


async def fetch_by_barcode(barcode: str) -> OFFProduct:
    url = f"{settings.off_base_url}/api/v2/product/{barcode}.json"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url, headers=HEADERS, params={"fields": "code,product_name,brands,nutriments,ingredients_text,allergens_tags"})
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
        kcal=kcal_per_100g(n),
        protein=_f(n.get("proteins_100g")),
        carbs=_f(n.get("carbohydrates_100g")),
        fat=_f(n.get("fat_100g")),
        ingredients_text=p.get("ingredients_text") or "",
        allergens=_parse_allergens(p.get("allergens_tags")),
    )
