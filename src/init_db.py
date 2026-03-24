from src.database import engine
from src.models import Base


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    print("Database inizializzato correttamente.")


if __name__ == "__main__":
    init_db()