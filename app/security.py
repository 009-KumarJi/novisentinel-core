"""Gateway auth + request hardening.

- `require_gateway_auth` is a FastAPI dependency that gates /v1/* when
  MASTER_API_KEY_REQUIRED is true. Callers are allowed if either:
    1. they present the master key as `Authorization: Bearer <key>`, or
    2. they supply their own upstream provider key (BYOK), which the proxy
       forwards to the LLM provider — in that case the gateway isn't
       spending the operator's quota, so we don't need to gate it.
- `BodySizeLimitMiddleware` rejects bodies larger than `max_request_bytes`
  before they hit the JSON parser.
"""

from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import settings


def _bearer(authorization: str | None) -> str:
    if not authorization:
        return ""
    return authorization.removeprefix("Bearer ").strip()


async def require_gateway_auth(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
) -> None:
    """Allow if BYOK present, else require master key (when enforcement on)."""
    if not settings.master_api_key_required:
        return

    bearer = _bearer(authorization)
    byok = x_api_key or ""

    # BYOK: caller supplied a provider key — they pay, we proxy.
    if byok:
        return

    # Otherwise: bearer must match the configured master key.
    master = settings.master_api_key
    if not master:
        # Misconfigured: enforcement on but no key set. Fail closed.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": {"message": "gateway auth misconfigured", "type": "configuration_error"}},
        )

    if not bearer or not hmac.compare_digest(bearer, master):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"message": "missing or invalid API key", "type": "authentication_failed"}},
        )


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests whose Content-Length exceeds the configured cap."""

    def __init__(self, app, max_bytes: int) -> None:
        super().__init__(app)
        self._max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):
        cl = request.headers.get("content-length")
        if cl is not None:
            try:
                if int(cl) > self._max_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={"error": {"message": "request body too large", "type": "invalid_request"}},
                    )
            except ValueError:
                pass
        return await call_next(request)
