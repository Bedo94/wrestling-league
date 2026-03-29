from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import distinct, select

from src.database import get_session
from src.models import Event


def _clean_optional_text(value: Any) -> Optional[str]:
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _normalize_event_date(value: Any) -> date:
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

    raise ValueError("Data evento non valida.")


def create_event(
    name: str,
    event_date: date,
    season: str,
    notes: Optional[str] = None,
) -> Event:
    if not season.strip():
        raise ValueError("La stagione è obbligatoria.")

    session = get_session()
    try:
        event = Event(
            name=name.strip(),
            event_date=event_date,
            season=season.strip(),
            notes=(notes or "").strip() or None,
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        return event
    finally:
        session.close()


def list_events() -> list[Event]:
    session = get_session()
    try:
        stmt = select(Event).order_by(Event.event_date.desc(), Event.id.desc())
        return list(session.scalars(stmt).all())
    finally:
        session.close()


def list_seasons() -> list[str]:
    session = get_session()
    try:
        stmt = (
            select(distinct(Event.season))
            .where(Event.season.is_not(None))
            .order_by(Event.season.desc())
        )
        results = session.execute(stmt).scalars().all()
        return [season for season in results if season and str(season).strip()]
    finally:
        session.close()


def update_events_from_rows(rows: list[dict[str, Any]]) -> int:
    session = get_session()
    try:
        with session.begin():
            updated_count = 0

            for row in rows:
                event_id = int(row["ID"])
                event = session.get(Event, event_id)

                if event is None:
                    raise ValueError(f"Evento con ID {event_id} non trovato.")

                name = str(row["Nome"]).strip()
                if not name:
                    raise ValueError(f"Il nome è obbligatorio per l'evento ID {event_id}.")

                season = str(row["Stagione"]).strip()
                if not season:
                    raise ValueError(f"La stagione è obbligatoria per l'evento ID {event_id}.")

                event.name = name
                event.event_date = _normalize_event_date(row.get("Data"))
                event.season = season
                event.notes = _clean_optional_text(row.get("Note"))

                updated_count += 1

        return updated_count
    finally:
        session.close()