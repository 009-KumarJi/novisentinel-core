import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import generate_api_key
from app.db.models import ApiKey
from app.dependencies import get_db, require_master_key

router = APIRouter()


class CreateKeyRequest(BaseModel):
    name: str
    owner: str


@router.post("/v1/keys", dependencies=[Depends(require_master_key)])
async def create_key(body: CreateKeyRequest, db: AsyncSession = Depends(get_db)):
    raw_key, prefix, key_hash = generate_api_key()
    record = ApiKey(
        id=uuid.uuid4(),
        key_prefix=prefix,
        key_hash=key_hash,
        name=body.name,
        owner=body.owner,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return {
        "key": raw_key,
        "key_id": str(record.id),
        "prefix": prefix,
        "message": "Store this key securely — it will not be shown again.",
    }


@router.get("/v1/keys", dependencies=[Depends(require_master_key)])
async def list_keys(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ApiKey))
    return [
        {
            "key_id": str(k.id),
            "prefix": k.key_prefix,
            "name": k.name,
            "owner": k.owner,
            "is_active": k.is_active,
            "created_at": k.created_at.isoformat(),
        }
        for k in result.scalars().all()
    ]


@router.delete("/v1/keys/{key_id}", dependencies=[Depends(require_master_key)])
async def revoke_key(key_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ApiKey).where(ApiKey.id == key_id))
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    key.is_active = False
    await db.commit()
    return {"message": "Key revoked", "key_id": str(key_id)}
