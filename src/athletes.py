from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import distinct, select

from src.database import get_session
from src.levels import get_level_from_label
from src.models import Athlete
from src.reference_data import SEX_OPTIONS, STYLE_OPTIONS


def _clean_optional_text(value: Any) -> Optional[str]:
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _normalize_birth_date(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value

    if isinstance(value, datetime):
        return value.date()

    if hasattr(value, "to_pydatetime"):
        return value.to_pydatetime().date()

    if isinstance(value, str):
        value = value.strip()
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue

    raise ValueError("Data nascita non valida.")


def create_athlete(
    first_name: str,
    last_name: Optional[str],
    nickname: Optional[str],
    team: Optional[str],
    birth_date: date,
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
            birth_date=birth_date,
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


def list_teams() -> list[str]:
    session = get_session()
    try:
        stmt = (
            select(distinct(Athlete.team))
            .where(Athlete.team.is_not(None))
            .order_by(Athlete.team.asc())
        )
        results = session.execute(stmt).scalars().all()
        return [team for team in results if team and str(team).strip()]
    finally:
        session.close()


def update_athletes_from_rows(rows: list[dict[str, Any]]) -> int:
    session = get_session()
    try:
        with session.begin():
            updated_count = 0

            for row in rows:
                athlete_id = int(row["ID"])
                athlete = session.get(Athlete, athlete_id)

                if athlete is None:
                    raise ValueError(f"Atleta con ID {athlete_id} non trovato.")

                first_name = str(row["Nome"]).strip()
                if not first_name:
                    raise ValueError(f"Il nome è obbligatorio per l'atleta ID {athlete_id}.")

                sex = str(row["Sesso"]).strip()
                if sex not in SEX_OPTIONS:
                    raise ValueError(
                        f"Sesso non valido per l'atleta ID {athlete_id}: {sex}"
                    )

                style = str(row["Stile"]).strip()
                if style not in STYLE_OPTIONS:
                    raise ValueError(
                        f"Stile non valido per l'atleta ID {athlete_id}: {style}"
                    )

                level_label = str(row["Livello"]).strip()
                level = get_level_from_label(level_label)

                default_weight = float(row["Peso"])
                if default_weight <= 0:
                    raise ValueError(
                        f"Peso non valido per l'atleta ID {athlete_id}: {default_weight}"
                    )

                athlete.first_name = first_name
                athlete.last_name = _clean_optional_text(row.get("Cognome"))
                athlete.nickname = _clean_optional_text(row.get("Nickname"))
                athlete.team = _clean_optional_text(row.get("Team"))
                athlete.birth_date = _normalize_birth_date(row.get("Data nascita"))
                athlete.sex = sex
                athlete.style = style
                athlete.level = level
                athlete.default_weight = default_weight
                athlete.active = bool(row.get("Attivo", True))

                updated_count += 1

        return updated_count
    finally:
        session.close()