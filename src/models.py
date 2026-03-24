from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class Athlete(Base):
    __tablename__ = "athletes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    nickname: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    team: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    birth_year: Mapped[int] = mapped_column(Integer, nullable=False)
    sex: Mapped[str] = mapped_column(String(20), nullable=False)
    style: Mapped[str] = mapped_column(String(30), nullable=False)

    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    default_weight: Mapped[float] = mapped_column(Float, nullable=False)
    rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


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

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)