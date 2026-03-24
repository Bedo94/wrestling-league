from typing import Optional

from sqlalchemy import select

from src.database import get_session
from src.models import Athlete


def create_athlete(
    first_name: str,
    last_name: Optional[str],
    nickname: Optional[str],
    team: Optional[str],
    birth_year: int,
    sex: str,
    style: str,
    level: int,
    default_weight: float,
    rating: Optional[float] = None,
) -> Athlete:
    session = get_session()
    try:
        athlete = Athlete(
            first_name=first_name.strip(),
            last_name=(last_name or "").strip() or None,
            nickname=(nickname or "").strip() or None,
            team=(team or "").strip() or None,
            birth_year=birth_year,
            sex=sex,
            style=style,
            level=level,
            default_weight=default_weight,
            rating=rating,
            active=True,
        )
        session.add(athlete)
        session.commit()
        session.refresh(athlete)
        return athlete
    finally:
        session.close()


def list_athletes(include_inactive: bool = True) -> list[Athlete]:
    session = get_session()
    try:
        stmt = select(Athlete).order_by(Athlete.last_name, Athlete.first_name)
        if not include_inactive:
            stmt = stmt.where(Athlete.active.is_(True))
        return list(session.scalars(stmt).all())
    finally:
        session.close()