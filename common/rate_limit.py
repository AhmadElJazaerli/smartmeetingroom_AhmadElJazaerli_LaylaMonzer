"""Shared rate limiting utilities using SlowAPI."""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from .config import get_settings

settings = get_settings()
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.default_rate_limit], enabled=settings.rate_limiting_enabled)


def rate_limit_handler(_: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(status_code=429, content={"detail": f"Rate limit exceeded: {exc.detail}"})


def apply_rate_limiter(app: FastAPI) -> None:
    """Attach the limiter middleware and exception handler to an app."""

    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
