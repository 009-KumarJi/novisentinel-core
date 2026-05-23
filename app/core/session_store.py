"""Disk-backed, TTL'd cache of per-conversation AnonymizationMap instances.

Files live under settings.session_dir, one per session, named by
sha256(session_id). Files are read on first access, mutated in memory under
a per-session asyncio.Lock, and persisted on context-manager exit. Expired
files (mtime older than TTL) are deleted lazily on access. Corrupt files
are logged and replaced with a fresh map.

This is a dev-box-only cache: assumes a single proxy process. No cross-
process locking; concurrent writers are last-write-wins.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import logging
import os
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from app.core.anonymizer import AnonymizationMap

logger = logging.getLogger(__name__)


class SessionStore:
    def __init__(self, root: Path, ttl_seconds: int):
        self._root = root
        self._ttl = ttl_seconds
        self._locks: dict[str, asyncio.Lock] = {}
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        with contextlib.suppress(OSError):
            os.chmod(root, 0o700)

    def _path(self, session_id: str) -> Path:
        h = hashlib.sha256(session_id.encode("utf-8")).hexdigest()
        return self._root / f"{h}.json"

    def _lock(self, session_id: str) -> asyncio.Lock:
        if session_id not in self._locks:
            self._locks[session_id] = asyncio.Lock()
        return self._locks[session_id]

    def _is_expired(self, path: Path) -> bool:
        try:
            age = time.time() - path.stat().st_mtime
            return age > self._ttl
        except FileNotFoundError:
            return False

    def _load(self, session_id: str) -> AnonymizationMap:
        path = self._path(session_id)
        if not path.exists():
            return AnonymizationMap()
        if self._is_expired(path):
            with contextlib.suppress(OSError):
                path.unlink()
            return AnonymizationMap()
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return AnonymizationMap(
                mapping=dict(raw.get("mapping", {})),
                reverse=dict(raw.get("reverse", {})),
                counters=dict(raw.get("counters", {})),
            )
        except (json.JSONDecodeError, OSError, TypeError) as exc:
            logger.warning("session_store: corrupt file %s (%s); using fresh map", path, exc)
            return AnonymizationMap()

    def _save(self, session_id: str, anon_map: AnonymizationMap) -> None:
        path = self._path(session_id)
        tmp = path.with_suffix(".json.tmp")
        payload = {
            "mapping": anon_map.mapping,
            "reverse": anon_map.reverse,
            "counters": anon_map.counters,
            "updated_at": time.time(),
        }
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        with contextlib.suppress(OSError):
            os.chmod(tmp, 0o600)
        os.replace(tmp, path)

    @asynccontextmanager
    async def with_session(self, session_id: str) -> AsyncIterator[AnonymizationMap]:
        lock = self._lock(session_id)
        async with lock:
            anon_map = self._load(session_id)
            try:
                yield anon_map
            finally:
                if not anon_map.is_empty:
                    self._save(session_id, anon_map)

    def purge_all(self) -> int:
        n = 0
        for p in self._root.glob("*.json"):
            try:
                p.unlink()
                n += 1
            except OSError:
                pass
        return n

    def purge_expired(self) -> int:
        n = 0
        for p in self._root.glob("*.json"):
            if self._is_expired(p):
                try:
                    p.unlink()
                    n += 1
                except OSError:
                    pass
        return n


_store: SessionStore | None = None


def get_session_store() -> SessionStore:
    global _store
    if _store is None:
        from app.config import settings

        _store = SessionStore(settings.session_dir, settings.session_ttl_hours * 3600)
    return _store
