from datetime import date, datetime
from functools import lru_cache
from typing import Any, Optional

from sqlalchemy import distinct, func, or_, select

from src.database import get_database_url, get_session
from src.levels import get_level_from_label
from src.models import Athlete, Match
from src.query_cache import DOMAIN_ATHLETES, bump_cache_version, get_cache_version
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


def get_token_scope_label(
    *,
    event_id: Optional[int] = None,
) -> str:
    if event_id is None:
        return "questo evento"
    return f"questo evento (ID {event_id})"


def _get_tokens_used_in_event(
    session,
    athlete_id: int,
    event_id: int,
    exclude_match_id: Optional[int] = None,
) -> int:
    stmt = select(func.count(Match.id)).where(
        Match.token_spender_id == athlete_id,
        Match.event_id == event_id,
    )

    if exclude_match_id is not None:
        stmt = stmt.where(Match.id != exclude_match_id)

    total = session.execute(stmt).scalar_one()
    return int(total or 0)


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
            active=True,
        )
        session.add(athlete)
        session.commit()
        session.refresh(athlete)
        bump_cache_version(DOMAIN_ATHLETES)
        return athlete
    finally:
        session.close()


@lru_cache(maxsize=32)
def _list_athletes_cached(
    database_url: str,
    include_inactive: bool,
    version: int,
) -> tuple[Athlete, ...]:
    session = get_session()
    try:
        stmt = select(Athlete).order_by(Athlete.last_name, Athlete.first_name)
        if not include_inactive:
            stmt = stmt.where(Athlete.active.is_(True))
        return tuple(session.scalars(stmt).all())
    finally:
        session.close()


def list_athletes(include_inactive: bool = True) -> list[Athlete]:
    return list(
        _list_athletes_cached(
            get_database_url(hide_password=False),
            include_inactive,
            get_cache_version(DOMAIN_ATHLETES),
        )
    )


@lru_cache(maxsize=16)
def _list_teams_cached(database_url: str, version: int) -> tuple[str, ...]:
    session = get_session()
    try:
        stmt = (
            select(distinct(Athlete.team))
            .where(Athlete.team.is_not(None))
            .order_by(Athlete.team.asc())
        )
        results = session.execute(stmt).scalars().all()
        return tuple(team for team in results if team and str(team).strip())
    finally:
        session.close()


def list_teams() -> list[str]:
    return list(
        _list_teams_cached(
            get_database_url(hide_password=False),
            get_cache_version(DOMAIN_ATHLETES),
        )
    )


def get_tokens_remaining(
    athlete_id: int,
    *,
    event_id: Optional[int] = None,
    exclude_match_id: Optional[int] = None,
) -> int:
    session = get_session()
    try:
        athlete = session.get(Athlete, athlete_id)
        if athlete is None:
            return 0

        if event_id is None:
            raise ValueError("event_id obbligatorio per calcolare i token residui.")

        used_tokens = _get_tokens_used_in_event(
            session=session,
            athlete_id=athlete_id,
            event_id=event_id,
            exclude_match_id=exclude_match_id,
        )

        remaining = int(TOKEN_SETTINGS["default_token_budget_per_event"]) - int(
            used_tokens or 0
        )
        return max(0, remaining)
    finally:
        session.close()


def _count_athlete_match_references(session, athlete_id: int) -> int:
    stmt = select(func.count(Match.id)).where(
        or_(
            Match.athlete_a_id == athlete_id,
            Match.athlete_b_id == athlete_id,
            Match.winner_id == athlete_id,
            Match.token_spender_id == athlete_id,
        )
    )
    total = session.execute(stmt).scalar_one()
    return int(total or 0)


def _format_athlete_display_name(athlete: Athlete) -> str:
    full_name = f"{athlete.first_name} {athlete.last_name or ''}".strip()
    return full_name or f"ID {athlete.id}"


def delete_athletes_if_unused(athlete_ids: list[int]) -> list[str]:
    normalized_ids = list(dict.fromkeys(int(athlete_id) for athlete_id in athlete_ids))
    if not normalized_ids:
        return []

    session = get_session()
    try:
        deleted_names: list[str] = []

        with session.begin():
            for athlete_id in normalized_ids:
                athlete = session.get(Athlete, athlete_id)
                if athlete is None:
                    raise ValueError(f"Atleta con ID {athlete_id} non trovato.")

                reference_count = _count_athlete_match_references(session, athlete_id)
                if reference_count > 0:
                    raise ValueError(
                        f"Non puoi eliminare {_format_athlete_display_name(athlete)}: "
                        "compare già in uno o più incontri."
                    )

                deleted_names.append(_format_athlete_display_name(athlete))
                session.delete(athlete)

        if deleted_names:
            bump_cache_version(DOMAIN_ATHLETES)

        return deleted_names
    finally:
        session.close()


def delete_athletes_if_unused(athlete_ids: list[int]) -> list[str]:
    normalized_ids = list(dict.fromkeys(int(athlete_id) for athlete_id in athlete_ids))
    if not normalized_ids:
        return []

    session = get_session()
    try:
        deleted_names: list[str] = []

        with session.begin():
            athletes = list(
                session.scalars(
                    select(Athlete).where(Athlete.id.in_(normalized_ids))
                ).all()
            )
            athletes_by_id = {athlete.id: athlete for athlete in athletes}

            for athlete_id in normalized_ids:
                if athlete_id not in athletes_by_id:
                    raise ValueError(f"Atleta con ID {athlete_id} non trovato.")

            reference_rows = session.execute(
                select(
                    Match.athlete_a_id,
                    Match.athlete_b_id,
                    Match.winner_id,
                    Match.token_spender_id,
                ).where(
                    or_(
                        Match.athlete_a_id.in_(normalized_ids),
                        Match.athlete_b_id.in_(normalized_ids),
                        Match.winner_id.in_(normalized_ids),
                        Match.token_spender_id.in_(normalized_ids),
                    )
                )
            ).all()

            referenced_ids = {
                referenced_id
                for row in reference_rows
                for referenced_id in row
                if referenced_id in athletes_by_id
            }

            if referenced_ids:
                blocking_athlete = athletes_by_id[next(iter(referenced_ids))]
                raise ValueError(
                    f"Non puoi eliminare {_format_athlete_display_name(blocking_athlete)}: "
                    "compare giÃ  in uno o piÃ¹ incontri."
                )

            for athlete_id in normalized_ids:
                athlete = athletes_by_id[athlete_id]
                deleted_names.append(_format_athlete_display_name(athlete))
                session.delete(athlete)

        if deleted_names:
            bump_cache_version(DOMAIN_ATHLETES)

        return deleted_names
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

                level_label = str(
                    row.get("Livello assegnato", row.get("Livello", ""))
                ).strip()
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

        if updated_count:
            bump_cache_version(DOMAIN_ATHLETES)

        return updated_count
    finally:
        session.close()
