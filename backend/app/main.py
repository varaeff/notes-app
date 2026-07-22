from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import account as account_router
from .routers import auth as auth_router
from .routers import notes as notes_router
from .routers import tags as tags_router
from .routers import telegram_settings as telegram_settings_router
from .workers.reminder_worker import reminder_worker_manager


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await reminder_worker_manager.sync()
    try:
        yield
    finally:
        await reminder_worker_manager.stop()


app = FastAPI(title="Notes API", version="0.1.0", lifespan=lifespan)

_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


app.include_router(auth_router.router, prefix="/api")
app.include_router(account_router.router, prefix="/api")
app.include_router(notes_router.router, prefix="/api")
app.include_router(tags_router.router, prefix="/api")
app.include_router(telegram_settings_router.router, prefix="/api")
