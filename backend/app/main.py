from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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
from app.services.telegram_alerts import (
    send_brute_force_alert,
    send_error_alert,
    send_unusual_4xx_alert,
)

_AUTH_PATHS = {"/api/auth/login", "/api/auth/register", "/api/auth/forgot-password"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="Uroboros", version="0.1.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    if request.url.path in _AUTH_PATHS:
        ip = request.client.host if request.client else "unknown"
        await send_brute_force_alert(ip, request.url.path)
    return JSONResponse(status_code=429, content={"detail": "Demasiados intentos. Espera un momento."})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    await send_error_alert(request.method, request.url.path, exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.middleware("http")
async def monitor_unusual_4xx(request: Request, call_next):
    response = await call_next(request)
    # Alert on 422 (malformed request) in auth endpoints — likely automated scanning
    if response.status_code == 422 and request.url.path in _AUTH_PATHS:
        await send_unusual_4xx_alert(request.method, request.url.path, 422, "Petición con formato inválido")
    return response

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
