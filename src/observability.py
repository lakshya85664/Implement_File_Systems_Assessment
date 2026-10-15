
from __future__ import annotations

import json
import logging
import time
from typing import Any

logger = logging.getLogger("document_lookup")


def configure_logging(level: int = logging.INFO) -> None:
    """Configure logging while preserving standard log capture."""
    logger.setLevel(level)
    logger.propagate = True


def emit_event(
    event_name: str,
    *,
    run_id: str,
    status: str,
    duration_ms: float | None = None,
    error_type: str | None = None,
) -> dict[str, Any]:
    """Emit a structured event without file contents or raw arguments."""
    event: dict[str, Any] = {
        "event": event_name,
        "run_id": run_id,
        "status": status,
    }

    if duration_ms is not None:
        event["duration_ms"] = round(max(0.0, duration_ms), 3)

    if error_type is not None:
        event["error_type"] = error_type

    logger.info(json.dumps(event, sort_keys=True))
    return event


class OperationTimer:
    """Measure an operation's elapsed time in milliseconds."""

    def __enter__(self) -> OperationTimer:
        self._started = time.perf_counter()
        self.duration_ms = 0.0
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.duration_ms = (
            time.perf_counter() - self._started
        ) * 1000.0
