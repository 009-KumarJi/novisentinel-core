from __future__ import annotations

import httpx

from .models import ScanResult

_DEFAULT_BASE = "https://api.novisentinel.com"
_TIMEOUT = httpx.Timeout(30.0)


def _build_body(text: str, context: str | None, config: dict | None) -> dict:
    body: dict = {"text": text}
    if context is not None:
        body["context"] = context
    if config:
        body["config"] = config
    return body


class Client:
    """Synchronous NoviSentinel client."""

    def __init__(self, api_key: str, base_url: str = _DEFAULT_BASE) -> None:
        self._http = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=_TIMEOUT,
        )

    def scan(
        self,
        text: str,
        context: str | None = None,
        config: dict | None = None,
    ) -> ScanResult:
        resp = self._http.post("/v1/scan", json=_build_body(text, context, config))
        resp.raise_for_status()
        return ScanResult.model_validate(resp.json())

    def scan_batch(
        self,
        texts: list[str],
        context: str | None = None,
        config: dict | None = None,
    ) -> list[ScanResult]:
        body = {"texts": [_build_body(t, context, config) for t in texts]}
        resp = self._http.post("/v1/scan/batch", json=body)
        resp.raise_for_status()
        return [ScanResult.model_validate(r) for r in resp.json()]

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> Client:
        return self

    def __exit__(self, *_) -> None:
        self.close()


class AsyncClient:
    """Async NoviSentinel client."""

    def __init__(self, api_key: str, base_url: str = _DEFAULT_BASE) -> None:
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=_TIMEOUT,
        )

    async def scan(
        self,
        text: str,
        context: str | None = None,
        config: dict | None = None,
    ) -> ScanResult:
        resp = await self._http.post("/v1/scan", json=_build_body(text, context, config))
        resp.raise_for_status()
        return ScanResult.model_validate(resp.json())

    async def scan_batch(
        self,
        texts: list[str],
        context: str | None = None,
        config: dict | None = None,
    ) -> list[ScanResult]:
        body = {"texts": [_build_body(t, context, config) for t in texts]}
        resp = await self._http.post("/v1/scan/batch", json=body)
        resp.raise_for_status()
        return [ScanResult.model_validate(r) for r in resp.json()]

    async def close(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> AsyncClient:
        return self

    async def __aexit__(self, *_) -> None:
        await self.close()
