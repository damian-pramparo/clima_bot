from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
import logging

from fastapi import FastAPI

from app.api.routes import router
from app.services.background import worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    worker.start()
    yield
    await worker.stop()


app = FastAPI(
    title="Sistema de Alertas Climaticas",
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(router)
