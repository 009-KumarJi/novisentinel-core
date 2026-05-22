"""Tests for app.core.session_store."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

import pytest

from app.core.session_store import SessionStore


@pytest.fixture()
def store(tmp_path: Path) -> SessionStore:
    return SessionStore(root=tmp_path / "sessions", ttl_seconds=3600)


async def test_load_returns_empty_on_missing_session(store: SessionStore) -> None:
    async with store.with_session("nonexistent") as anon_map:
        assert anon_map.is_empty


async def test_save_then_load_roundtrip(store: SessionStore) -> None:
    session_id = "test-session-1"
    async with store.with_session(session_id) as anon_map:
        ph = anon_map.placeholder_for("alice@acme.com", "EMAIL_ADDRESS")

    async with store.with_session(session_id) as anon_map2:
        assert not anon_map2.is_empty
        assert anon_map2.restore(ph) == "alice@acme.com"


async def test_expired_file_returns_empty_and_unlinks(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path / "sessions", ttl_seconds=1)
    session_id = "expiring-session"

    async with store.with_session(session_id) as anon_map:
        anon_map.placeholder_for("bob@example.com", "EMAIL_ADDRESS")

    path = store._path(session_id)
    assert path.exists()

    # backdate mtime to trigger expiry
    old_time = time.time() - 10
    import os

    os.utime(path, (old_time, old_time))

    async with store.with_session(session_id) as anon_map2:
        assert anon_map2.is_empty

    assert not path.exists()


async def test_corrupt_file_returns_empty_and_logs(
    store: SessionStore, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    session_id = "corrupt-session"
    path = store._path(session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not valid json", encoding="utf-8")

    import logging

    with caplog.at_level(logging.WARNING, logger="app.core.session_store"):
        async with store.with_session(session_id) as anon_map:
            assert anon_map.is_empty

    assert any("corrupt" in r.message for r in caplog.records)


async def test_purge_all_removes_every_file(store: SessionStore) -> None:
    for i in range(3):
        async with store.with_session(f"session-{i}") as anon_map:
            anon_map.placeholder_for(f"user{i}@acme.com", "EMAIL_ADDRESS")

    assert store.purge_all() == 3
    assert list(store._root.glob("*.json")) == []


async def test_purge_expired_only_removes_old_files(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path / "sessions", ttl_seconds=3600)

    async with store.with_session("keep") as anon_map:
        anon_map.placeholder_for("keep@acme.com", "EMAIL_ADDRESS")
    async with store.with_session("expire") as anon_map:
        anon_map.placeholder_for("expire@acme.com", "EMAIL_ADDRESS")

    import os

    expire_path = store._path("expire")
    old_time = time.time() - 7200
    os.utime(expire_path, (old_time, old_time))

    removed = store.purge_expired()
    assert removed == 1
    assert store._path("keep").exists()
    assert not expire_path.exists()


async def test_concurrent_access_serialised_per_session(store: SessionStore) -> None:
    """Two concurrent writers on the same session must serialize, not corrupt each other."""
    session_id = "concurrent-session"
    results: list[str] = []

    async def _write(email: str) -> None:
        async with store.with_session(session_id) as anon_map:
            ph = anon_map.placeholder_for(email, "EMAIL_ADDRESS")
            results.append(ph)

    await asyncio.gather(_write("a@acme.com"), _write("b@acme.com"))

    async with store.with_session(session_id) as anon_map:
        assert not anon_map.is_empty
        for ph in results:
            assert anon_map.restore(ph) in ("a@acme.com", "b@acme.com")
