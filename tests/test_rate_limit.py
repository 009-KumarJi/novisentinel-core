"""
Rate limiter unit tests — Redis is mocked at the pipeline level.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.rate_limit import check_rate_limit


def _make_redis(current_count: int):
    """Build a Redis mock that reports `current_count` requests in the window."""
    check_pipe = MagicMock()
    check_pipe.zremrangebyscore = MagicMock()
    check_pipe.zcard = MagicMock()
    check_pipe.execute = AsyncMock(return_value=[None, current_count])

    add_pipe = MagicMock()
    add_pipe.zadd = MagicMock()
    add_pipe.expire = MagicMock()
    add_pipe.execute = AsyncMock(return_value=[1, 1])

    redis = MagicMock()
    redis.pipeline = MagicMock(side_effect=[check_pipe, add_pipe])
    return redis, check_pipe, add_pipe


def _make_blocked_redis(current_count: int):
    """Build a Redis mock that will cause the rate limiter to block (no add_pipe needed)."""
    check_pipe = MagicMock()
    check_pipe.zremrangebyscore = MagicMock()
    check_pipe.zcard = MagicMock()
    check_pipe.execute = AsyncMock(return_value=[None, current_count])

    redis = MagicMock()
    redis.pipeline = MagicMock(return_value=check_pipe)
    return redis, check_pipe


@pytest.mark.asyncio
async def test_rate_limit_allowed_when_empty():
    redis, _, _ = _make_redis(0)
    assert await check_rate_limit(redis, "key-123", 60) is True


@pytest.mark.asyncio
async def test_rate_limit_allowed_one_under_limit():
    redis, _, _ = _make_redis(59)
    assert await check_rate_limit(redis, "key-123", 60) is True


@pytest.mark.asyncio
async def test_rate_limit_blocked_at_limit():
    redis, _ = _make_blocked_redis(60)
    assert await check_rate_limit(redis, "key-123", 60) is False


@pytest.mark.asyncio
async def test_rate_limit_blocked_over_limit():
    redis, _ = _make_blocked_redis(999)
    assert await check_rate_limit(redis, "key-123", 60) is False


@pytest.mark.asyncio
async def test_rate_limit_uses_correct_redis_key():
    redis, check_pipe, add_pipe = _make_redis(0)
    await check_rate_limit(redis, "my-key-id", 100)

    check_pipe.zremrangebyscore.assert_called_once()
    assert check_pipe.zremrangebyscore.call_args[0][0] == "ratelimit:my-key-id"
    check_pipe.zcard.assert_called_once_with("ratelimit:my-key-id")

    add_pipe.zadd.assert_called_once()
    zadd_key = next(iter(add_pipe.zadd.call_args[0]))
    assert zadd_key == "ratelimit:my-key-id"
    add_pipe.expire.assert_called_once_with("ratelimit:my-key-id", 120)
