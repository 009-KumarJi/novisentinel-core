"""Retry and in-process circuit breaker for provider calls."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from app.gateway.errors import GatewayError

logger = logging.getLogger(__name__)

T = TypeVar("T")

_RETRYABLE_TYPES = {"provider_unavailable", "timeout"}

_CB_FAILURE_THRESHOLD = 10
_CB_WINDOW_SECONDS = 30
_CB_HALF_OPEN_AFTER = 60


def _is_retryable(exc: Exception) -> bool:
    return isinstance(exc, GatewayError) and exc.error_type in _RETRYABLE_TYPES


async def with_retry(coro_fn: Callable[[], Coroutine[Any, Any, T]], provider: str) -> T:  # noqa: UP047
    try:
        async for attempt in AsyncRetrying(
            retry=retry_if_exception(_is_retryable),
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=10),
            reraise=True,
        ):
            with attempt:
                return await coro_fn()
    except RetryError as exc:
        raise exc.last_attempt.exception() from exc
    raise RuntimeError("retry loop exited unexpectedly")


class CircuitBreaker:
    """In-process circuit breaker (single-worker, no Redis needed)."""

    def __init__(self, provider: str) -> None:
        self.provider = provider
        self._state = "closed"
        self._failures = 0
        self._opened_at = 0.0
        self._window_start = time.monotonic()

    def _reset_window_if_expired(self) -> None:
        if time.monotonic() - self._window_start >= _CB_WINDOW_SECONDS:
            self._failures = 0
            self._window_start = time.monotonic()

    def record_success(self) -> None:
        self._state = "closed"
        self._failures = 0

    def record_failure(self) -> None:
        self._reset_window_if_expired()
        if self._state == "half-open":
            self._state = "open"
            self._opened_at = time.time()
            logger.warning("circuit_breaker.reopened provider=%s", self.provider)
            return
        self._failures += 1
        if self._failures >= _CB_FAILURE_THRESHOLD:
            self._state = "open"
            self._opened_at = time.time()
            logger.warning("circuit_breaker.opened provider=%s failures=%d", self.provider, self._failures)

    def check(self) -> None:
        if self._state == "closed":
            return
        if self._state == "open":
            if time.time() - self._opened_at >= _CB_HALF_OPEN_AFTER:
                self._state = "half-open"
                logger.info("circuit_breaker.half_open provider=%s", self.provider)
                return
            raise GatewayError(
                "provider_unavailable",
                f"Circuit breaker open for {self.provider} — try again shortly",
                503,
                self.provider,
            )


_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(provider: str) -> CircuitBreaker:
    if provider not in _circuit_breakers:
        _circuit_breakers[provider] = CircuitBreaker(provider)
    return _circuit_breakers[provider]


async def resilient_call(  # noqa: UP047
    coro_fn: Callable[[], Coroutine[Any, Any, T]],
    provider: str,
) -> T:
    cb = get_circuit_breaker(provider)
    cb.check()

    try:
        result = await with_retry(coro_fn, provider)
        cb.record_success()
        return result
    except (GatewayError, Exception):
        cb.record_failure()
        raise
