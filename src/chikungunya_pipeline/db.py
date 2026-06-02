"""SQLAlchemy engine / connection helpers.

A single lazily-created engine is shared across the process. Both the pipeline
and the Streamlit app use :func:`get_engine`.
"""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy import Engine, create_engine, text

from .config import get_settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Return a cached SQLAlchemy engine built from settings.DATABASE_URL."""
    settings = get_settings()
    return create_engine(settings.database_url, pool_pre_ping=True, future=True)


def ping() -> bool:
    """Return True if the database is reachable."""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
