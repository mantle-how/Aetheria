# ============================
# 定位:資料庫ORM映射層
# ============================
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


# ============================
# Base + Helpers
# ============================

class Base(DeclarativeBase):
    """
    Declarative base for all ORM models.
    基礎的資料table定義，所有ORM model都繼承自這個Base。
    """
    pass


def _uuid_pk() -> Mapped[uuid.UUID]:
    """
    UUID primary key helper.
    產生UUID primary key 欄位設定，避免重複的欄位宣告
    - PostgreSQL: native UUID
    - Others: String(36) 也能正常運作
    """
    # 直接使用 PG_UUID(as_uuid=True)。如果你真要跨 SQLite，也可以 fallback String(36)
    return mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _uuid_fk(
    target: str,
    *,
    ondelete: Optional[str] = None,
    nullable: bool = False,
    primary_key: bool = False,
) -> Mapped[uuid.UUID]:
    """UUID foreign key helper with consistent typing."""
    return mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(target, ondelete=ondelete),
        nullable=nullable,
        primary_key=primary_key,
    )


def _json_col(nullable: bool = False):
    """
    JSON column that maps to JSONB on Postgres, JSON on others.
    統一產生JSON欄位宣告
    在 Postgres 建議另外建立 GIN index（在 migration 內處理）。
    """
    return mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=nullable)


# ============================
# Core Tables (核心的初始table建置)
# ============================

class World(Base):
    """
    world的基礎定義
    """
    __tablename__ = "worlds"

    world_id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

    seed: Mapped[int] = mapped_column(BigInteger, nullable=False)
    generator_version: Mapped[str] = mapped_column(String(64), nullable=False)

    current_tick: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    tick_unit_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=60_000)  # 1 tick = 60s
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="CREATED")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    agents: Mapped[List["Agent"]] = relationship(
        back_populates="world",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    events: Mapped[List["EventStore"]] = relationship(
        back_populates="world",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    snapshots: Mapped[List["Snapshot"]] = relationship(
        back_populates="world",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("idx_worlds_status", "status"),
        Index("idx_worlds_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<World id={self.world_id} name={self.name!r} status={self.status}>"


# ============================
# Map Storage Option 1: Tiles (把世界用tile形式存起來，小地圖適用)
# ============================

class WorldTile(Base):
    __tablename__ = "world_tiles"

    world_id: Mapped[uuid.UUID] = _uuid_fk("worlds.world_id", ondelete="CASCADE", primary_key=True)
    x: Mapped[int] = mapped_column(Integer, primary_key=True)
    y: Mapped[int] = mapped_column(Integer, primary_key=True)

    terrain_type: Mapped[int] = mapped_column(Integer, nullable=False)  # 建議用 Enum（見下方建議）
    is_blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    resource_type: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    resource_amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    meta_json = _json_col(nullable=True)

    __table_args__ = (
        Index("idx_tiles_resource", "world_id", "resource_type"),
        Index("idx_tiles_terrain", "world_id", "terrain_type"),
    )

    def __repr__(self) -> str:
        return f"<WorldTile world={self.world_id} ({self.x},{self.y})>"


# ============================
# Map Storage Option 2: Blob (把世界用Blob形式存起來，大地圖適用)
# ============================

class WorldMap(Base):
    __tablename__ = "world_maps"

    world_id: Mapped[uuid.UUID] = _uuid_fk("worlds.world_id", ondelete="CASCADE", primary_key=True)
    format: Mapped[str] = mapped_column(String(32), nullable=False, default="zstd+msgpack")

    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)

    data_blob: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        Index("idx_world_maps_wh", "width", "height"),
    )

    def __repr__(self) -> str:
        return f"<WorldMap world={self.world_id} {self.width}x{self.height} fmt={self.format}>"


# ============================
# Agents / Relationships (agent的狀態和關係投影表，方便快速查詢，避免每次都從event replay計算)
# ============================

class Agent(Base):
    __tablename__ = "agents"

    agent_id: Mapped[uuid.UUID] = _uuid_pk()
    world_id: Mapped[uuid.UUID] = _uuid_fk("worlds.world_id", ondelete="CASCADE", nullable=False)

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    sex: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 建議用 Enum
    birth_tick: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    death_tick: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    x: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    y: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Current state projection (fast query)
    state_json = _json_col(nullable=False)
    personality_json = _json_col(nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    world: Mapped["World"] = relationship(back_populates="agents")

    __table_args__ = (
        Index("idx_agents_world", "world_id"),
        Index("idx_agents_pos", "world_id", "x", "y"),
        Index("idx_agents_alive", "world_id", "death_tick"),
    )

    def __repr__(self) -> str:
        return f"<Agent id={self.agent_id} name={self.name!r} world={self.world_id}>"


class Relationship(Base):
    """
    Projection table for relationship.
    儲存有向邊 (a -> b)。若要無向，在應用層統一排序 (min, max)。
    """
    __tablename__ = "relationships"

    world_id: Mapped[uuid.UUID] = _uuid_fk("worlds.world_id", ondelete="CASCADE", primary_key=True)
    a_agent_id: Mapped[uuid.UUID] = _uuid_fk("agents.agent_id", ondelete="CASCADE", primary_key=True)
    b_agent_id: Mapped[uuid.UUID] = _uuid_fk("agents.agent_id", ondelete="CASCADE", primary_key=True)

    affinity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    trust: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    hostility: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    familiarity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    last_tick: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    meta_json = _json_col(nullable=True)

    __table_args__ = (
        Index("idx_rel_a", "world_id", "a_agent_id"),
        Index("idx_rel_b", "world_id", "b_agent_id"),
    )

    def __repr__(self) -> str:
        return f"<Relationship world={self.world_id} a={self.a_agent_id} b={self.b_agent_id}>"


# ============================
# Event Store (append-only)
# ============================

class EventStore(Base):
    __tablename__ = "event_store"

    event_id: Mapped[uuid.UUID] = _uuid_pk()
    world_id: Mapped[uuid.UUID] = _uuid_fk("worlds.world_id", ondelete="CASCADE", nullable=False)

    tick: Mapped[int] = mapped_column(BigInteger, nullable=False)
    seq_in_tick: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    event_type: Mapped[str] = mapped_column(String(64), nullable=False)

    actor_agent_id: Mapped[Optional[uuid.UUID]] = _uuid_fk(
        "agents.agent_id", ondelete="SET NULL", nullable=True
    )
    target_agent_id: Mapped[Optional[uuid.UUID]] = _uuid_fk(
        "agents.agent_id", ondelete="SET NULL", nullable=True
    )

    x: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    y: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    payload_json = _json_col(nullable=False)

    caused_by_event_id: Mapped[Optional[uuid.UUID]] = _uuid_fk(
        "event_store.event_id", ondelete="SET NULL", nullable=True
    )

    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    world: Mapped["World"] = relationship(back_populates="events")

    __table_args__ = (
        UniqueConstraint("world_id", "tick", "seq_in_tick", name="uq_events_tick_seq"),
        CheckConstraint("seq_in_tick >= 0", name="ck_events_seq_nonneg"),
        Index("idx_events_world_tick", "world_id", "tick"),
        Index("idx_events_type", "world_id", "event_type", "tick"),
        Index("idx_events_actor", "world_id", "actor_agent_id", "tick"),
        Index("idx_events_target", "world_id", "target_agent_id", "tick"),
        # GIN index for payload_json 建議在 migration 內加（見下方）
    )

    def __repr__(self) -> str:
        return f"<EventStore id={self.event_id} world={self.world_id} tick={self.tick}>"


# ============================
# Snapshots
# ============================

class Snapshot(Base):
    __tablename__ = "snapshots"

    snapshot_id: Mapped[uuid.UUID] = _uuid_pk()
    world_id: Mapped[uuid.UUID] = _uuid_fk("worlds.world_id", ondelete="CASCADE", nullable=False)

    tick: Mapped[int] = mapped_column(BigInteger, nullable=False)

    world_state_json = _json_col(nullable=False)
    map_ref: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    world: Mapped["World"] = relationship(back_populates="snapshots")

    agent_snapshots: Mapped[List["AgentSnapshot"]] = relationship(
        back_populates="snapshot",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("idx_snapshots_world_tick_desc", "world_id", "tick"),
        UniqueConstraint("world_id", "tick", name="uq_snapshot_world_tick"),
    )

    def __repr__(self) -> str:
        return f"<Snapshot id={self.snapshot_id} world={self.world_id} tick={self.tick}>"


class AgentSnapshot(Base):
    __tablename__ = "agent_snapshots"

    snapshot_id: Mapped[uuid.UUID] = _uuid_fk("snapshots.snapshot_id", ondelete="CASCADE", primary_key=True)
    agent_id: Mapped[uuid.UUID] = _uuid_fk("agents.agent_id", ondelete="CASCADE", primary_key=True)

    agent_state_json = _json_col(nullable=False)

    snapshot: Mapped["Snapshot"] = relationship(back_populates="agent_snapshots")

    __table_args__ = (
        Index("idx_agent_snapshots_agent", "agent_id", "snapshot_id"),
    )

    def __repr__(self) -> str:
        return f"<AgentSnapshot snap={self.snapshot_id} agent={self.agent_id}>"