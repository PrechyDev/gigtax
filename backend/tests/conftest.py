"""Shared test fixtures: a fresh SQLite in-memory DB per test, wired into FastAPI's
get_db dependency, plus a TestClient built on it. No test in this suite should need a
real Postgres connection or a real external network call.
"""
import json
import os
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from db.base import Base
from db.session import get_db
from main import app
from models.category import Category

CATEGORIES_SEED_FILE = os.path.join(
    os.path.dirname(__file__), "..", "db", "seed_data", "categories.json"
)


@pytest.fixture()
def test_engine():
    """Exposed separately from db_session so tests can build additional sessions bound
    to the same in-memory DB — needed for code (like statement background processing)
    that opens its own SessionLocal() rather than using the get_db dependency.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_fk(dbapi_connection, _):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    # knowledge_chunks uses pgvector's Vector column type, which only compiles against
    # a real Postgres+pgvector connection — SQLite can't create that table at all.
    # Tests touching the advisory RAG pipeline mock modules.advisory.retrieval /
    # document_ingestion entirely rather than hitting a real knowledge_chunks table.
    sqlite_tables = [t for t in Base.metadata.sorted_tables if t.name != "knowledge_chunks"]
    Base.metadata.create_all(bind=engine, tables=sqlite_tables)

    try:
        yield engine
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def db_session(test_engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()

    # Real category taxonomy, same source scripts/seed_categories.py loads into
    # Postgres — tests exercise the actual NTA-2025-aligned categories, not stand-ins.
    with open(CATEGORIES_SEED_FILE, "r", encoding="utf-8") as f:
        for entry in json.load(f):
            session.add(Category(
                classification=entry["classification"],
                category_name=entry["category_name"],
                developer_slug=entry["developer_slug"],
                description=entry.get("description"),
                tax_treatment=entry.get("tax_treatment"),
                asset_class=entry.get("asset_class"),
            ))
    session.commit()

    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def run_background_inline(test_engine):
    """Makes core.background.EXECUTOR.submit(fn, *a, **kw) run `fn` immediately and
    synchronously, in-process, instead of on a real thread — and redirects any
    SessionLocal() the background function opens to the same in-memory test engine.
    Deterministic tests, no sleeps/polling, while still exercising the real
    background-processing function end to end.
    """
    TestSessionLocal = sessionmaker(bind=test_engine)

    def fake_submit(fn, *args, **kwargs):
        with patch("api.routes.statements.SessionLocal", TestSessionLocal), \
             patch("api.routes.statements.time.sleep"):  # skip the real batch-stagger delay in tests
            fn(*args, **kwargs)
        return None

    with patch("api.routes.statements.EXECUTOR") as mock_executor:
        mock_executor.submit.side_effect = fake_submit
        yield mock_executor


@pytest.fixture()
def client(db_session):
    def _override_get_db():
        # In real production, get_db() opens a brand-new session per request, so it
        # always sees committed changes from any other session (e.g. a background
        # thread). Reusing one session across a test's simulated "requests" is
        # convenient but doesn't expire on its own between them, so a background
        # commit's fresh values would otherwise be masked by stale identity-mapped
        # objects — expire_all() here restores that real per-request freshness.
        db_session.expire_all()
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    # raise_server_exceptions=False: a real HTTP client never sees a raised Python
    # exception, only the JSON response our global handler (main.py) produces — tests
    # that exercise that handler need the same behavior, not pytest's default of
    # re-raising server errors to surface bugs.
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()
