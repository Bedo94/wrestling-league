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
from src.settings import TOKEN_SETTINGS


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
    rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    token_budget: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=TOKEN_SETTINGS["default_token_budget_per_season"],
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


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    season: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=lambda: str(date.today().year),
    )
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

    points_a: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    points_b: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    is_token_match: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    token_spender_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("athletes.id"), nullable=True
    )
    token_cost: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Riferimenti logici per sync cross-database
    # Tengo naming coerente con la struttura attuale (a/b) invece di red/blue
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


class FormulaParameter(Base):
    """
    Store user-configurable parameters for scoring, matchmaking, ratings
    and other derived formulas. Each parameter is identified by a group
    (section) and a key. Values are stored as strings along with their
    original type to allow parsing back into Python types.
    """

    __tablename__ = "formula_parameters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_name: Mapped[str] = mapped_column(String(50), nullable=False)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str] = mapped_column(String(100), nullable=False)
    value_type: Mapped[str] = mapped_column(String(20), nullable=False, default="float")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
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
    version_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    __mapper_args__ = {
        "version_id_col": version_id,
    }


class FormulaVersion(Base):
    """
    Versione pubblicabile di una formula/configurazione.
    Serve per storicizzare i parametri usati nei ricalcoli.
    """

    __tablename__ = "formula_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_name: Mapped[str] = mapped_column(String(50), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    config_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

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


class CalculationRun(Base):
    """
    Traccia un ricalcolo eseguito su un certo ambiente e scope.
    """

    __tablename__ = "calculation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    formula_version_id: Mapped[int] = mapped_column(
        ForeignKey("formula_versions.id"),
        nullable=False,
    )
    environment_name: Mapped[str] = mapped_column(String(30), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(20), nullable=False, default="all")
    scope_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    started_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

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