import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock

sys.path.append(str(Path(__file__).resolve().parent.parent))

from memory.database import Base, TrackPlayed, Interaction
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session


@pytest.fixture
def test_db_session():
    """Cria banco de dados em memória para testes"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def mock_spotify_client():
    """Mock do cliente Spotify"""
    mock = MagicMock()
    mock.current_user = MagicMock(return_value={"id": "test_user", "display_name": "Test User"})
    return mock


@pytest.fixture
def mock_llm_client():
    """Mock do cliente LLM"""
    mock = MagicMock()
    mock.model_name = "gemini-2.0-flash"
    mock.generate_json = MagicMock(return_value={
        "intent": "CHAT",
        "mood": None,
        "query": None,
        "value": None,
        "response": "Olá! Como posso ajudar?"
    })
    return mock


@pytest.fixture
def sample_tracks():
    """Tracks de exemplo para testes"""
    now = datetime.now(timezone.utc)
    return [
        TrackPlayed(
            track_id=f"track_{i}",
            track_uri=f"spotify:track:track_{i}",
            title=f"Song {i}",
            artists='["Artist A", "Artist B"]',
            album=f"Album {i}",
            duration_ms=240000,
            genres='["indie", "rock"]',
            popularity=75,
            played_at=now - timedelta(days=j),
            hour_of_day=14,
            day_of_week=2,
            context="play",
            mood="happy",
        )
        for i, j in enumerate(range(1, 11), 1)
    ]


@pytest.fixture
def sample_interactions(test_db_session):
    """Interações de exemplo para testes"""
    now = datetime.now(timezone.utc)
    interactions = [
        Interaction(
            interaction_type="recommend",
            user_input=f"Recomenda musica {i}",
            mood="happy" if i % 2 == 0 else "sad",
            assistant_response=f"Aqui está sua recomendação {i}",
            metadata_json='{"tracks": 5}',
            created_at=now - timedelta(days=i),
            hour_of_day=14,
            day_of_week=2,
        )
        for i in range(1, 6)
    ]
    for interaction in interactions:
        test_db_session.add(interaction)
    test_db_session.commit()
    return interactions


@pytest.fixture
def monkeypatch_db(monkeypatch, test_db_session):
    """Substitui get_session por test_db_session"""
    def mock_get_session():
        return test_db_session
    monkeypatch.setattr("memory.database.get_session", lambda: test_db_session)
    return monkeypatch
