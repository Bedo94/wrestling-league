from datetime import date
from typing import Optional

from sqlalchemy import select

from src.database import get_session
from src.models import Event


def create_event(
    name: str,
    event_date: date,
    notes: Optional[str] = None,
) -> Event:
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