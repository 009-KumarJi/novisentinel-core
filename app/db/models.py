import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase


def utcnow():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key_prefix = Column(String(8), nullable=False)
    key_hash = Column(String(64), nullable=False, unique=True)
    name = Column(Text, nullable=False)
    owner = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class ScanLog(Base):
    __tablename__ = "scan_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=False)
    context = Column(Text, nullable=True)          # "input" | "output"
    text_hash = Column(String(64), nullable=False)  # SHA256, raw text never stored
    safe = Column(Boolean, nullable=False)
    risk_level = Column(Text, nullable=False)       # none/low/medium/high/critical
    action = Column(Text, nullable=False)           # allow/warn/redact/block
    pii_count = Column(Integer, default=0)
    injection_count = Column(Integer, default=0)
    secrets_count = Column(Integer, default=0)
    toxicity_count = Column(Integer, default=0)
    total_detections = Column(Integer, default=0)
    scan_duration_ms = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)


class WebhookConfig(Base):
    __tablename__ = "webhook_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=False, index=True)
    url = Column(Text, nullable=False)
    secret = Column(Text, nullable=False)
    trigger_actions = Column(JSON, nullable=False, default=list)      # e.g. ["block", "warn"]
    trigger_risk_levels = Column(JSON, nullable=False, default=list)  # e.g. ["critical", "high"]
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)
