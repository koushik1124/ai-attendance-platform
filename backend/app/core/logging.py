import logging

from app.core.config import get_settings


def configure_logging() -> None:
    """Configure a small, consistent application log format."""

    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
