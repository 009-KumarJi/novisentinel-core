from __future__ import annotations


class ScanError(Exception):
    """Base exception for all NoviSentinel SDK errors."""


class AuthError(ScanError):
    """Raised when the API key is missing, invalid, or lacks permission (401/403)."""


class RateLimitError(ScanError):
    """Raised when the server returns 429 Too Many Requests.

    Attributes:
        retry_after: Seconds to wait before retrying (from Retry-After header),
            or None if the header was absent.
    """

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class ServiceUnavailableError(ScanError):
    """Raised when the server returns 502, 503, or 504, or is unreachable."""


class ValidationError(ScanError):
    """Raised when the request is malformed and the server returns 422."""
