from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.limiter import limiter
from app.routers import (
    auth, cheat_days, creatine, diary, exercises, exercise_sessions,
    favorites, friends, goals, inventory, measurements, products,
    push, recipes, shopping_list, supplements, users, water, weight, allergies,
)
from app.services.notification_scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="Uroboros", version="0.1.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

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
app.include_router(supplements.router, prefix=api_prefix)
app.include_router(allergies.router, prefix=api_prefix)
app.include_router(favorites.router, prefix=api_prefix)
app.include_router(push.router, prefix=api_prefix)
