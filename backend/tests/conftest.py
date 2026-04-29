"""Shared pytest fixtures for the StudySync backend test suite.

Provides:

- ``_guard_test_db`` (session-scoped): refuses to run if ``DATABASE_URL``
  doesn't point at a database whose name contains ``test``, so the
  destructive ``db`` fixture can never wipe a developer's real data.
  Override with ``ALLOW_DB_RESET_FOR_TESTS=1`` only if you know what
  you're doing.
- ``client``: a FastAPI ``TestClient`` lazily imported after the guard.
- ``db``: a clean SQLAlchemy session, with the schema dropped and
  recreated before each test that requests it.
"""
import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def _guard_test_db():
    """
    Safety guard: these tests reset the database schema.

    Require DATABASE_URL to point at a dedicated test DB (name contains 'test'),
    or explicitly opt-in via ALLOW_DB_RESET_FOR_TESTS=1.
    """
    url = os.getenv("DATABASE_URL", "")
    allow = os.getenv("ALLOW_DB_RESET_FOR_TESTS") == "1"
    if not allow and ("test" not in url.lower()):
        pytest.skip(
            "Refusing to reset non-test database. "
            "Set DATABASE_URL to a dedicated test DB (name contains 'test') "
            "or set ALLOW_DB_RESET_FOR_TESTS=1."
        )


@pytest.fixture()
def client(_guard_test_db):
    # Import after guard so we don't accidentally import the app
    # while pointing at a non-test database.
    from main import app  # noqa: WPS433

    return TestClient(app)


@pytest.fixture()
def db(_guard_test_db):
    """
    Provide a clean database for each test.
    """
    from database import engine, SessionLocal, Base  # noqa: WPS433
    from main import ensure_schema_updates  # noqa: WPS433

    # Reset schema
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    ensure_schema_updates()

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

