from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, cheat_days, creatine, diary, exercises, exercise_sessions, friends, goals, inventory, measurements, products, recipes, shopping_list, users, water, weight

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
app.include_router(measurements.router, prefix=api_prefix)
app.include_router(water.router, prefix=api_prefix)
app.include_router(recipes.router, prefix=api_prefix)
app.include_router(friends.router, prefix=api_prefix)
app.include_router(creatine.router, prefix=api_prefix)
app.include_router(cheat_days.router, prefix=api_prefix)
app.include_router(exercises.router, prefix=api_prefix)
app.include_router(exercise_sessions.router, prefix=api_prefix)
app.include_router(inventory.router, prefix=api_prefix)
app.include_router(shopping_list.router, prefix=api_prefix)
