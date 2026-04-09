from fastapi import FastAPI

app = FastAPI(title="Uroboros", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
