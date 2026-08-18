import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.db.database import Base, get_db
from app.main import app

FAKE_VECTOR = [0.1, 0.2, 0.3]


@pytest.fixture()
def test_engine(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def client(test_engine):
    test_session_local = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = test_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def mock_external_calls(monkeypatch):
    # embed_texts / embed_text return the SAME vector so any saved chunk is a
    # perfect cosine match for any question — keeps retrieval tests deterministic
    monkeypatch.setattr(
        "app.services.ingestion.embed_texts", lambda pieces: [FAKE_VECTOR for _ in pieces]
    )
    monkeypatch.setattr("app.services.retrieval.embed_text", lambda question: FAKE_VECTOR)
    monkeypatch.setattr(
        "app.services.ingestion.generate_suggested_question", lambda content: "mocked question?"
    )
    monkeypatch.setattr(
        "app.services.ingestion.fetch_url_text", lambda url: "mocked fetched page content"
    )
    def fake_generate_answer(question, chunks):
        if not chunks:
            return "I don't have any saved content to answer that yet — add some notes or URLs first."
        return "mocked answer [1]."

    monkeypatch.setattr("app.api.query.generate_answer", fake_generate_answer)
