"""HTTP audit logging middleware shared by services."""
from __future__ import annotations

import logging
from pathlib import Path
from time import time
from typing import Optional

from fastapi import FastAPI, Request

_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)


def _build_logger(service_name: str) -> logging.Logger:
    logger = logging.getLogger(f"audit.{service_name}")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(_LOG_DIR / f"{service_name}.log")
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def add_audit_middleware(app: FastAPI, service_name: str) -> None:
    logger = _build_logger(service_name)

    @app.middleware("http")
    async def audit_logger(request: Request, call_next):  # type: ignore[override]
        start = time()
        response = await call_next(request)
        duration_ms = (time() - start) * 1000
        client_ip: Optional[str] = None
        if request.client:
            client_ip = request.client.host
        logger.info(
            "%s %s | status=%s | client=%s | duration=%.2fms",
            request.method,
            request.url.path,
            response.status_code,
            client_ip or "unknown",
            duration_ms,
        )
        return response
