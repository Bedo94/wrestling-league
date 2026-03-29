from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import distinct, func, select

from src.database import get_session
from src.levels import get_level_from_label
from src.models import Athlete, Event, Match
from src.reference_data import SEX_OPTIONS, STYLE_OPTIONS
from src.settings import TOKEN_SETTINGS


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
    token_budget: int = TOKEN_SETTINGS["default_token_budget_per_season"],
    rating: Optional[float] = None,
) -> Athlete:
    if token_budget < 0:
        raise ValueError("Il budget token non può essere negativo.")

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
            token_budget=int(token_budget),
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


def get_tokens_remaining_for_season(
    athlete_id: int,
    season: str,
    exclude_match_id: Optional[int] = None,
) -> int:
    session = get_session()
    try:
        athlete = session.get(Athlete, athlete_id)
        if athlete is None:
            return 0

        stmt = (
            select(func.coalesce(func.sum(Match.token_cost), 0))
            .join(Event, Match.event_id == Event.id)
            .where(
                Match.is_token_match.is_(True),
                Match.token_spender_id == athlete_id,
                Event.season == season,
            )
        )

        if exclude_match_id is not None:
            stmt = stmt.where(Match.id != exclude_match_id)

        used_tokens = session.execute(stmt).scalar_one()
        remaining = int(athlete.token_budget) - int(used_tokens or 0)
        return max(0, remaining)
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

                token_budget = int(row["Token budget"])
                if token_budget < 0:
                    raise ValueError(
                        f"Budget token non valido per l'atleta ID {athlete_id}: {token_budget}"
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
                athlete.token_budget = token_budget
                athlete.active = bool(row.get("Attivo", True))

                updated_count += 1

        return updated_count
    finally:
        session.close()