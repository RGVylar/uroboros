from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, diary, goals, products, recipes, users, water, weight

app = FastAPI(title="Uroboros", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


api_prefix = "/api"
app.include_router(auth.router, prefix=api_prefix)
app.include_router(users.router, prefix=api_prefix)
app.include_router(products.router, prefix=api_prefix)
app.include_router(diary.router, prefix=api_prefix)
app.include_router(goals.router, prefix=api_prefix)
app.include_router(weight.router, prefix=api_prefix)
app.include_router(water.router, prefix=api_prefix)
app.include_router(recipes.router, prefix=api_prefix)
