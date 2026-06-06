from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routes import users, stickers, trades

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Copa 2026 Sticker Swap", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(stickers.router)
app.include_router(trades.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "Copa 2026 Sticker Swap"}
