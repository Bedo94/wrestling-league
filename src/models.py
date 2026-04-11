from datetime import date, datetime
from typing import Optional
import uuid

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class Athlete(Base):
    __tablename__ = "athletes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    nickname: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    team: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    sex: Mapped[str] = mapped_column(String(20), nullable=False)
    style: Mapped[str] = mapped_column(String(30), nullable=False)

    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    default_weight: Mapped[float] = mapped_column(Float, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Metadati minimi per sync / merge / concorrenza
    sync_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        unique=True,
        index=True,
        default=lambda: str(uuid.uuid4()),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    version_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    __mapper_args__ = {
        "version_id_col": version_id,
    }


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metadati minimi per sync / merge / concorrenza
    sync_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        unique=True,
        index=True,
        default=lambda: str(uuid.uuid4()),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    version_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    __mapper_args__ = {
        "version_id_col": version_id,
    }


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=False)
    athlete_a_id: Mapped[int] = mapped_column(ForeignKey("athletes.id"), nullable=False)
    athlete_b_id: Mapped[int] = mapped_column(ForeignKey("athletes.id"), nullable=False)

    style: Mapped[str] = mapped_column(String(30), nullable=False)

    weight_a: Mapped[float] = mapped_column(Float, nullable=False)
    weight_b: Mapped[float] = mapped_column(Float, nullable=False)

    level_a: Mapped[int] = mapped_column(Integer, nullable=False)
    level_b: Mapped[int] = mapped_column(Integer, nullable=False)

    raw_score_a: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    raw_score_b: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    winner_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("athletes.id"), nullable=True
    )
    win_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    token_spender_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("athletes.id"), nullable=True
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Riferimenti logici per sync cross-database
    event_sync_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )
    athlete_a_sync_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )
    athlete_b_sync_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )
    winner_sync_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )
    token_spender_sync_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )

    # Metadati minimi per sync / merge / concorrenza
    sync_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        unique=True,
        index=True,
        default=lambda: str(uuid.uuid4()),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    version_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    __mapper_args__ = {
        "version_id_col": version_id,
    }


class FormulaRevision(Base):
    """
    Revisione completa della configurazione formule per un ambiente.
    """

    __tablename__ = "formula_revisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    environment_name: Mapped[str] = mapped_column(String(30), nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_revision_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("formula_revisions.id"),
        nullable=True,
    )
    config_format: Mapped[str] = mapped_column(String(20), nullable=False, default="toml")
    config_text: Mapped[str] = mapped_column(Text, nullable=False)
    config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
