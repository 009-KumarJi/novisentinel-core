import time
import uuid as _uuid
from redis.asyncio import Redis


async def check_rate_limit(redis: Redis, key_id: str, limit_rpm: int) -> bool:
    now = time.time()
    window_start = now - 60
    redis_key = f"ratelimit:{key_id}"

    check_pipe = redis.pipeline()
    check_pipe.zremrangebyscore(redis_key, 0, window_start)
    check_pipe.zcard(redis_key)
    results = await check_pipe.execute()
    current_count = results[1]

    if current_count >= limit_rpm:
        return False

    member = f"{now}:{_uuid.uuid4().hex}"
    add_pipe = redis.pipeline()
    add_pipe.zadd(redis_key, {member: now})
    add_pipe.expire(redis_key, 120)
    await add_pipe.execute()
    return True
