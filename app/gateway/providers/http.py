"""Shared httpx client pool for provider egress.

A single AsyncClient per provider is reused across requests so we benefit
from connection pooling and HTTP/2 multiplexing instead of building a new
TLS connection on every call.
"""

from __future__ import annotations

import httpx

_LIMITS = httpx.Limits(max_connections=100, max_keepalive_connections=20)
_TIMEOUT = httpx.Timeout(60.0, connect=10.0)

_clients: dict[str, httpx.AsyncClient] = {}


def get_client(provider: str) -> httpx.AsyncClient:
    client = _clients.get(provider)
    if client is None or client.is_closed:
        client = httpx.AsyncClient(
            timeout=_TIMEOUT,
            limits=_LIMITS,
            follow_redirects=False,
            http2=False,
        )
        _clients[provider] = client
    return client


async def shutdown() -> None:
    for client in _clients.values():
        if not client.is_closed:
            await client.aclose()
    _clients.clear()
