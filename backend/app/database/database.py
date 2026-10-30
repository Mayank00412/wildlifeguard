from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        connect_args = {}
        if settings.resolved_database_url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
        _engine = create_engine(
            settings.resolved_database_url,
            connect_args=connect_args,
            future=True,
        )
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, future=True)
    return _SessionLocal


def reset_engine() -> None:
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


def init_db() -> None:
    from app.database import models  # noqa: F401

    engine = get_engine()
    Base.metadata.create_all(bind=engine)

    # Lightweight auto-migration for SQLite to ensure newer columns exist
    if str(engine.url).startswith("sqlite"):
        with engine.connect() as conn:
            cursor = conn.exec_driver_sql("PRAGMA table_info(videos)")
            existing_cols = {row[1] for row in cursor.fetchall()}
            needed_cols = {
                "fps": "FLOAT",
                "width": "INTEGER",
                "height": "INTEGER",
                "duration_seconds": "FLOAT",
                "total_frames": "INTEGER",
                "processed_fps": "INTEGER",
            }
            for col_name, col_type in needed_cols.items():
                if col_name not in existing_cols:
                    conn.exec_driver_sql(f"ALTER TABLE videos ADD COLUMN {col_name} {col_type}")
            conn.commit()


def get_db() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
