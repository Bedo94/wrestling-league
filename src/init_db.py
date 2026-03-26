import src.models  # noqa: F401
from src.database import Base, get_engine


def init_db() -> None:
    Base.metadata.create_all(bind=get_engine())