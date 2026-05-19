"""Normalized error taxonomy for the gateway layer."""

from __future__ import annotations

from typing import Literal

ErrorType = Literal[
    "rate_limit_exceeded",
    "invalid_request",
    "authentication_failed",
    "provider_unavailable",
    "provider_safety_block",
    "internal_error",
    "timeout",
]


class GatewayError(Exception):
    def __init__(
        self,
        error_type: ErrorType,
        message: str,
        upstream_status: int = 502,
        provider: str = "",
    ) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.message = message
        self.upstream_status = upstream_status
        self.provider = provider

    def to_openai_dict(self) -> dict:
        return {
            "error": {
                "message": self.message,
                "type": self.error_type,
                "code": self.error_type,
                "param": None,
            }
        }


_OAI_STATUS_MAP: dict[int, ErrorType] = {
    400: "invalid_request",
    401: "authentication_failed",
    403: "authentication_failed",
    404: "invalid_request",
    422: "invalid_request",
    429: "rate_limit_exceeded",
    500: "provider_unavailable",
    502: "provider_unavailable",
    503: "provider_unavailable",
    504: "timeout",
}


def normalize_openai_error(exc: Exception, provider: str = "openai") -> GatewayError:
    import httpx

    if isinstance(exc, httpx.TimeoutException):
        return GatewayError("timeout", "upstream timed out", 504, provider)
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        error_type = _OAI_STATUS_MAP.get(status, "internal_error")
        try:
            body = exc.response.json()
            code = (body.get("error") or {}).get("code", "") or ""
            err_type = (body.get("error") or {}).get("type", "") or ""
            if "content_filter" in code or "content_policy" in err_type:
                error_type = "provider_safety_block"
        except Exception:
            pass
        return GatewayError(error_type, f"upstream returned {status}", status, provider)
    if isinstance(exc, httpx.RequestError):
        return GatewayError("provider_unavailable", "could not reach upstream", 502, provider)
    return GatewayError("internal_error", str(exc), 502, provider)


def normalize_anthropic_error(exc: Exception) -> GatewayError:
    import httpx

    if isinstance(exc, httpx.TimeoutException):
        return GatewayError("timeout", "upstream timed out", 504, "anthropic")
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        _map: dict[int, ErrorType] = {
            400: "invalid_request",
            401: "authentication_failed",
            403: "authentication_failed",
            404: "invalid_request",
            422: "invalid_request",
            429: "rate_limit_exceeded",
            500: "provider_unavailable",
            529: "provider_unavailable",
            503: "provider_unavailable",
        }
        error_type = _map.get(status, "internal_error")
        try:
            body = exc.response.json()
            if (body.get("error") or {}).get("type") == "overloaded_error":
                error_type = "provider_unavailable"
        except Exception:
            pass
        return GatewayError(error_type, f"Upstream anthropic returned {status}", status, "anthropic")
    if isinstance(exc, httpx.RequestError):
        return GatewayError("provider_unavailable", f"Could not reach anthropic: {exc}", 502, "anthropic")
    return GatewayError("internal_error", str(exc), 502, "anthropic")


def normalize_google_error(exc: Exception) -> GatewayError:
    import httpx

    if isinstance(exc, httpx.TimeoutException):
        return GatewayError("timeout", "upstream timed out", 504, "google")
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        try:
            body = exc.response.json()
            if any(c.get("finishReason") == "SAFETY" for c in (body.get("candidates") or [])):
                return GatewayError("provider_safety_block", "Response blocked by Google safety filters", 400, "google")
        except Exception:
            pass
        _map: dict[int, ErrorType] = {
            400: "invalid_request",
            401: "authentication_failed",
            403: "authentication_failed",
            429: "rate_limit_exceeded",
            500: "provider_unavailable",
            503: "provider_unavailable",
        }
        return GatewayError(_map.get(status, "internal_error"), f"Upstream google returned {status}", status, "google")
    if isinstance(exc, httpx.RequestError):
        return GatewayError("provider_unavailable", f"Could not reach google: {exc}", 502, "google")
    return GatewayError("internal_error", str(exc), 502, "google")


_NORMALIZERS = {
    "openai": normalize_openai_error,
    "anthropic": normalize_anthropic_error,
    "google": normalize_google_error,
}


def normalize_error(exc: Exception, provider: str) -> GatewayError:
    if isinstance(exc, GatewayError):
        return exc
    normalizer = _NORMALIZERS.get(provider, lambda e: normalize_openai_error(e, provider))
    return normalizer(exc)
