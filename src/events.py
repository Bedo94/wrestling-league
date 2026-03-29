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

def derive_season_from_date(event_date: date) -> str:
    """
    Calcola la stagione a partire dalla data dell’evento.
    In questo progetto la stagione coincide sempre con l’anno.
    """
    return str(event_date.year)

def create_event(
    name: str,
    event_date: date,
    season: Optional[str] = None,
    notes: Optional[str] = None,
) -> Event:
    """
    Crea un nuovo evento. Se la stagione non è fornita o è vuota,
    viene dedotta dall’anno di event_date.
    """
    event_date = _normalize_event_date(event_date)
    if season is None or not str(season).strip():
        season = derive_season_from_date(event_date)

    session = get_session()
    try:
        event = Event(
            name=name.strip(),
            event_date=event_date,
            season=str(season).strip(),
            notes=(notes or "").strip() or None,
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        return event
    finally:
        session.close()

def list_events() -> list[Event]:
    """Restituisce tutti gli eventi ordinati per data decrescente."""
    session = get_session()
    try:
        stmt = select(Event).order_by(Event.event_date.desc(), Event.id.desc())
        return list(session.scalars(stmt).all())
    finally:
        session.close()

def list_seasons() -> list[str]:
    """Restituisce le stagioni distinte presenti negli eventi."""
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
    """
    Aggiorna gli eventi esistenti a partire da una lista di dizionari.
    La colonna 'Stagione' del DataFrame non viene usata; la stagione viene
    derivata dalla colonna 'Data'.
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
                season = derive_season_from_date(event_date)
                event.name = name
                event.event_date = event_date
                event.season = season
                event.notes = _clean_optional_text(row.get("Note"))
                updated_count += 1
        return updated_count
    finally:
        session.close()