from fastapi import Depends, Header, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from redis.asyncio import Redis

from app.db.session import get_db
from app.db.models import ApiKey
from app.core.auth import hash_key, _master_key_uuid
from app.core.rate_limit import check_rate_limit
from app.config import settings

bearer_scheme = HTTPBearer()


async def get_redis() -> Redis:
    from app.main import redis_client
    return redis_client


async def get_current_key(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> ApiKey:
    token = credentials.credentials

    if token == settings.master_api_key:
        master_id = _master_key_uuid(settings.master_api_key)
        result = await db.execute(select(ApiKey).where(ApiKey.id == master_id))
        master_row = result.scalar_one_or_none()
        if master_row is None:
            raise HTTPException(status_code=503, detail="Master key not initialized")
        return master_row

    key_hash = hash_key(token)
    result = await db.execute(
        select(ApiKey).where(ApiKey.key_hash == key_hash, ApiKey.is_active == True)
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key")

    allowed = await check_rate_limit(redis, str(api_key.id), settings.default_rate_limit_rpm)
    if not allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    return api_key


async def require_master_key(
    x_master_key: str | None = Header(default=None),
    credentials: HTTPAuthorizationCredentials | None = Security(HTTPBearer(auto_error=False)),
) -> None:
    key = x_master_key or (credentials.credentials if credentials else None)
    if key != settings.master_api_key:
        raise HTTPException(status_code=403, detail="Master API key required")
