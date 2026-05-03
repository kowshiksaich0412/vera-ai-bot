from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.context import router as context_router
from app.routes.health import router as health_router
from app.routes.reply import router as reply_router
from app.routes.tick import router as tick_router
from app.utils.logger import configure_logging

configure_logging()

app = FastAPI(
    title="Vera AI Bot",
    version="1.0",
    description="AI engagement assistant for merchants",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/v1")
app.include_router(context_router, prefix="/v1")
app.include_router(tick_router, prefix="/v1")
app.include_router(reply_router, prefix="/v1")
