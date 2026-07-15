"""Valid preset avatar slugs. The image files live in the frontend at
static/avatars/<slug>.webp — keep this list in sync with that folder and with
frontend/src/lib/avatars.ts."""

AVATAR_IDS: frozenset[str] = frozenset({
    "aguacate", "sushi", "fresa",
    "taco", "brocoli", "huevo",
    "ramen", "sandia", "cafe",
    "pizza", "pepinillo", "donut",
    "pulpo", "tostada", "lata",
    "chile", "gelatina", "queso",
})
