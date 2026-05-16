from __future__ import annotations

import asyncio
import time

import httpx

from .exceptions import AuthError, RateLimitError, ServiceUnavailableError
from .exceptions import ValidationError as ScanValidationError
from .models import ScanResult

_DEFAULT_BASE = "http://localhost:8000"
_RETRY_STATUSES = {502, 503, 504}
_BACKOFF = [0.5, 1.0, 2.0]


def _build_body(text: str, context: str | None, config: dict | None) -> dict:
    body: dict = {"text": text}
    if context is not None:
        body["context"] = context
    if config:
        body["config"] = config
    return body


def _raise_for_status(resp: httpx.Response) -> None:
    """Map HTTP errors to typed SDK exceptions."""
    if resp.is_success:
        return
    status = resp.status_code
    if status in (401, 403):
        raise AuthError(f"Authentication failed ({status}). Check your API key.")
    if status == 422:
        raise ScanValidationError(f"Request validation failed: {resp.text}")
    if status == 429:
        retry_after_raw = resp.headers.get("retry-after")
        retry_after = float(retry_after_raw) if retry_after_raw else None
        raise RateLimitError("Rate limited (429).", retry_after=retry_after)
    if status in _RETRY_STATUSES:
        raise ServiceUnavailableError(f"Server returned {status}.")
    resp.raise_for_status()


class Client:
    """Synchronous NoviSentinel client.

    Args:
        api_key: Bearer token for the hosted API. Leave empty for local self-hosted use.
        base_url: Base URL of the NoviSentinel API (default: http://localhost:8000).
        timeout: Request timeout in seconds.
        retries: Number of retry attempts on transient 5xx errors (default 3).

    Example:
        >>> client = Client()          # local NoviSentinel on :8000
        >>> result = client.scan("Ignore previous instructions")
        >>> print(result.action)
        block
    """

    def __init__(
        self,
        api_key: str = "",
        base_url: str = _DEFAULT_BASE,
        timeout: float = 30.0,
        retries: int = 3,
    ) -> None:
        self._retries = retries
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self._http = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=httpx.Timeout(timeout),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _post_with_retry(self, path: str, json: dict) -> httpx.Response:
        last_exc: Exception | None = None
        for attempt in range(self._retries + 1):
            try:
                resp = self._http.post(path, json=json)
                if resp.status_code in _RETRY_STATUSES and attempt < self._retries:
                    time.sleep(_BACKOFF[min(attempt, len(_BACKOFF) - 1)])
                    last_exc = ServiceUnavailableError(f"Server returned {resp.status_code}.")
                    continue
                _raise_for_status(resp)
                return resp
            except httpx.ConnectError as exc:
                if attempt < self._retries:
                    time.sleep(_BACKOFF[min(attempt, len(_BACKOFF) - 1)])
                    last_exc = ServiceUnavailableError(str(exc))
                    continue
                raise ServiceUnavailableError(str(exc)) from exc
        raise last_exc  # type: ignore[misc]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan(
        self,
        text: str,
        context: str | None = None,
        config: dict | None = None,
    ) -> ScanResult:
        """Scan a single text string.

        Args:
            text: The text to scan (user input or LLM output).
            context: ``"input"`` or ``"output"`` — affects which detectors fire
                and how policies are evaluated.
            config: Optional per-request policy overrides.

        Returns:
            ScanResult with action, risk level, and individual detections.

        Raises:
            AuthError: Invalid or missing API key.
            RateLimitError: Too many requests; check ``retry_after``.
            ValidationError: Malformed request.
            ServiceUnavailableError: Server unreachable or returning 5xx after retries.
        """
        resp = self._post_with_retry("/v1/scan", json=_build_body(text, context, config))
        return ScanResult.model_validate(resp.json())

    def scan_batch(
        self,
        texts: list[str],
        context: str | None = None,
        config: dict | None = None,
    ) -> list[ScanResult]:
        """Scan multiple texts sequentially, returning one result per input.

        Args:
            texts: List of texts to scan.
            context: Applied to every item in the batch.
            config: Applied to every item in the batch.

        Returns:
            List of ScanResult, one per input text, in order.
        """
        return [self.scan(t, context, config) for t in texts]

    def health(self) -> bool:
        """Return True if the API is reachable and healthy, False otherwise.

        Never raises — safe to use for polling without try/except.
        """
        try:
            resp = self._http.get("/health")
            return resp.is_success
        except Exception:
            return False

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._http.close()

    def __enter__(self) -> Client:
        return self

    def __exit__(self, *_) -> None:
        self.close()


class AsyncClient:
    """Async NoviSentinel client (use with ``async with``).

    Args:
        api_key: Bearer token for the hosted API. Leave empty for local self-hosted use.
        base_url: Base URL of the NoviSentinel API (default: http://localhost:8000).
        timeout: Request timeout in seconds.
        retries: Number of retry attempts on transient 5xx errors (default 3).

    Example:
        >>> async with AsyncClient() as client:
        ...     result = await client.scan("My SSN is 123-45-6789")
        ...     print(result.has_pii)
        True
    """

    def __init__(
        self,
        api_key: str = "",
        base_url: str = _DEFAULT_BASE,
        timeout: float = 30.0,
        retries: int = 3,
    ) -> None:
        self._retries = retries
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=httpx.Timeout(timeout),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _post_with_retry(self, path: str, json: dict) -> httpx.Response:
        last_exc: Exception | None = None
        for attempt in range(self._retries + 1):
            try:
                resp = await self._http.post(path, json=json)
                if resp.status_code in _RETRY_STATUSES and attempt < self._retries:
                    await asyncio.sleep(_BACKOFF[min(attempt, len(_BACKOFF) - 1)])
                    last_exc = ServiceUnavailableError(f"Server returned {resp.status_code}.")
                    continue
                _raise_for_status(resp)
                return resp
            except httpx.ConnectError as exc:
                if attempt < self._retries:
                    await asyncio.sleep(_BACKOFF[min(attempt, len(_BACKOFF) - 1)])
                    last_exc = ServiceUnavailableError(str(exc))
                    continue
                raise ServiceUnavailableError(str(exc)) from exc
        raise last_exc  # type: ignore[misc]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def scan(
        self,
        text: str,
        context: str | None = None,
        config: dict | None = None,
    ) -> ScanResult:
        """Scan a single text string asynchronously.

        Args:
            text: The text to scan.
            context: ``"input"`` or ``"output"``.
            config: Optional per-request policy overrides.

        Returns:
            ScanResult with action, risk level, and individual detections.

        Raises:
            AuthError: Invalid or missing API key.
            RateLimitError: Too many requests; check ``retry_after``.
            ValidationError: Malformed request.
            ServiceUnavailableError: Server unreachable or returning 5xx after retries.
        """
        resp = await self._post_with_retry("/v1/scan", json=_build_body(text, context, config))
        return ScanResult.model_validate(resp.json())

    async def scan_batch(
        self,
        texts: list[str],
        context: str | None = None,
        config: dict | None = None,
    ) -> list[ScanResult]:
        """Scan multiple texts concurrently, returning one result per input.

        Args:
            texts: List of texts to scan.
            context: Applied to every item in the batch.
            config: Applied to every item in the batch.

        Returns:
            List of ScanResult, one per input text, in order.
        """
        return list(await asyncio.gather(*[self.scan(t, context, config) for t in texts]))

    async def health(self) -> bool:
        """Return True if the API is reachable and healthy, False otherwise.

        Never raises — safe to use for polling without try/except.
        """
        try:
            resp = await self._http.get("/health")
            return resp.is_success
        except Exception:
            return False

    async def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        await self._http.aclose()

    async def __aenter__(self) -> AsyncClient:
        return self

    async def __aexit__(self, *_) -> None:
        await self.close()
