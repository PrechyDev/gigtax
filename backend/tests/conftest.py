"""Shared test fixtures: a fresh SQLite in-memory DB per test, wired into FastAPI's
get_db dependency, plus a TestClient built on it. No test in this suite should need a
real Postgres connection or a real external network call.
"""
import json
import os

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
def db_session():
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
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
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
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def client(db_session):
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
