from datetime import date, datetime
from functools import lru_cache
from typing import Any, Optional

from sqlalchemy import func, select

from src.database import get_database_url, get_session
from src.models import Event, Match
from src.query_cache import DOMAIN_EVENTS, bump_cache_version, get_cache_version


def _clean_optional_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_event_date(value: Any) -> date:
    """
    Normalizza un valore data/ora in un oggetto date.

    Accetta date, datetime, oggetti con to_pydatetime e stringhe nei formati
    'YYYY-MM-DD' o 'DD/MM/YYYY'. Solleva ValueError se non può convertire.
    """
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
    notes: Optional[str] = None,
) -> Event:
    event_date = _normalize_event_date(event_date)

    session = get_session()
    try:
        event = Event(
            name=name.strip(),
            event_date=event_date,
            notes=(notes or "").strip() or None,
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        bump_cache_version(DOMAIN_EVENTS)
        return event
    finally:
        session.close()


@lru_cache(maxsize=32)
def _list_events_cached(database_url: str, version: int) -> tuple[Event, ...]:
    session = get_session()
    try:
        stmt = select(Event).order_by(Event.event_date.desc(), Event.id.desc())
        return tuple(session.scalars(stmt).all())
    finally:
        session.close()


def list_events() -> list[Event]:
    """Restituisce tutti gli eventi ordinati per data decrescente."""
    return list(
        _list_events_cached(
            get_database_url(hide_password=False),
            get_cache_version(DOMAIN_EVENTS),
        )
    )


def _count_event_match_references(session, event_id: int) -> int:
    stmt = select(func.count(Match.id)).where(Match.event_id == event_id)
    total = session.execute(stmt).scalar_one()
    return int(total or 0)


def delete_events_if_unused(event_ids: list[int]) -> list[str]:
    normalized_ids = list(dict.fromkeys(int(event_id) for event_id in event_ids))
    if not normalized_ids:
        return []

    session = get_session()
    try:
        deleted_names: list[str] = []

        with session.begin():
            for event_id in normalized_ids:
                event = session.get(Event, event_id)
                if event is None:
                    raise ValueError(f"Evento con ID {event_id} non trovato.")

                reference_count = _count_event_match_references(session, event_id)
                if reference_count > 0:
                    raise ValueError(
                        f"Non puoi eliminare l'evento '{event.name}': "
                        "ha già incontri associati."
                    )

                deleted_names.append(event.name)
                session.delete(event)

        if deleted_names:
            bump_cache_version(DOMAIN_EVENTS)

        return deleted_names
    finally:
        session.close()


def update_events_from_rows(rows: list[dict[str, Any]]) -> int:
    """
    Aggiorna gli eventi esistenti a partire da una lista di dizionari.
    """
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
                event_date = _normalize_event_date(row.get("Data"))
                event.name = name
                event.event_date = event_date
                event.notes = _clean_optional_text(row.get("Note"))
                updated_count += 1
        if updated_count:
            bump_cache_version(DOMAIN_EVENTS)

        return updated_count
    finally:
        session.close()
