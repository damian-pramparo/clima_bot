from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from datetime import datetime, timezone

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.alerts import evaluate_alerts

logger = logging.getLogger(__name__)


class AlertEvaluationWorker:
    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

    def start(self) -> None:
        if settings.app_env == "test" or self._task is not None:
            return
        self._task = asyncio.create_task(self._run(), name="alert-evaluation-worker")
        logger.info(
            "automatic alert evaluation worker started; interval=%s seconds",
            settings.alert_evaluation_interval_seconds,
        )

    async def stop(self) -> None:
        if self._task is None:
            return
        self._stop_event.set()
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None
        logger.info("automatic alert evaluation worker stopped")

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                started_at = datetime.now(timezone.utc)
                logger.info("automatic alert evaluation job started at %s", started_at.isoformat())
                async with SessionLocal() as session:
                    created = await evaluate_alerts(session)
                    logger.info(
                        "automatic alert evaluation job completed; created_notifications=%s",
                        created,
                    )
            except Exception:
                logger.exception("automatic alert evaluation job failed")
            logger.info(
                "automatic alert evaluation worker sleeping; next_run_in_seconds=%s",
                settings.alert_evaluation_interval_seconds,
            )
            await asyncio.sleep(settings.alert_evaluation_interval_seconds)


worker = AlertEvaluationWorker()
