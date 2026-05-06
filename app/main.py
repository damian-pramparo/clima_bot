from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
import logging

from fastapi import FastAPI
from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.errors import DomainError
from app.services.background import worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Start and stop background services with the FastAPI lifespan."""
    worker.start()
    yield
    await worker.stop()


app = FastAPI(
    title="Sistema de Alertas Climaticas",
    version="0.1.0",
    lifespan=lifespan,
)


@app.exception_handler(DomainError)
async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
    """Return domain validation errors as unprocessable entity responses."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": str(exc)},
    )


app.include_router(router)
