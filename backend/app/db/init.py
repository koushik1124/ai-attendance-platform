from app.db.base import Base
from app.db.session import engine
from app import models  # noqa: F401  # register all model metadata


def init_db() -> None:
    """Create the current MVP schema for a fresh local database.

    A versioned migration workflow will replace create_all before production deployment.
    """

    Base.metadata.create_all(bind=engine)
