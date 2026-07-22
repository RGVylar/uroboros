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

# Curated identity-colour palette (OKLCH hues). Kept to the blue→violet→pink arc
# on purpose: no green (clashes with --primary / goals), no amber (clashes with
# --cal / kcal), no red (clashes with delete / fat). Keep in sync with the
# swatches in frontend/src/lib/avatars.ts.
IDENTITY_HUES: frozenset[int] = frozenset({320, 350, 290, 265, 235, 195})
