import sys
import logging
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker, Session
sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import settings

logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

class TrackPlayed(Base):
    __tablename__ = "tracks_played"

    id = Column(Integer, primary_key=True, autoincrement=True)
    track_id = Column(String(64), nullable=False, index=True)
    track_uri = Column(String(128), nullable=False)
    title = Column(String(512), nullable=False)
    artists = Column(String(512), nullable=False)
    album = Column(String(512), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    genres = Column(Text, nullable=True)
    popularity = Column(Integer, nullable=True)
    played_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    hour_of_day = Column(Integer, nullable=True)
    day_of_week = Column(Integer, nullable=True)
    context = Column(String(256), nullable=True)
    mood = Column(String(128), nullable=True)
    interaction_id = Column(Integer, ForeignKey("interactions.id"), nullable=True)
    interaction = relationship("Interaction", back_populates="tracks_played")

    __table_args__ = (
        Index("ix_tracks_played_at", "played_at"),
        Index("ix_tracks_hour_dow", "hour_of_day", "day_of_week"),
        Index("ix_tracks_track_id_played_at", "track_id", "played_at"),
    )

    def __repr__(self) -> str:
        return f"<TrackPlayed id={self.id} title='{self.title}'>"

class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    interaction_type = Column(String(64), nullable=False, index=True)
    user_input = Column(Text, nullable=True)
    mood = Column(String(128), nullable=True)
    assistant_response = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)
    feedback_positive = Column(Boolean, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    hour_of_day = Column(Integer, nullable=True)
    day_of_week = Column(Integer, nullable=True)
    tracks_played = relationship("TrackPlayed", back_populates="interaction")

    __table_args__ = (
        Index("ix_interactions_created_at", "created_at"),
        Index("ix_interactions_type_created", "interaction_type", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Interaction id={self.id} type='{self.interaction_type}'>"

class UserProfile(Base):
    __tablename__ = "user_profile"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(128), nullable=False, unique=True, index=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<UserProfile key='{self.key}'>"

class PlaylistCreated(Base):
    __tablename__ = "playlists_created"

    id = Column(Integer, primary_key=True, autoincrement=True)
    playlist_id = Column(String(64), nullable=False, unique=True, index=True)
    playlist_uri = Column(String(128), nullable=False)
    name = Column(String(512), nullable=False)
    description = Column(Text, nullable=True)
    context = Column(String(256), nullable=True)
    mood = Column(String(128), nullable=True)
    track_uris_json = Column(Text, nullable=True)
    total_tracks = Column(Integer, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_playlists_context_mood", "context", "mood"),
        Index("ix_playlists_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<PlaylistCreated id={self.id} name='{self.name}'>"

engine = create_engine(
    f"sqlite:///{settings.database.resolved_path}",
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

def init_db() -> None:
    logger.info(f"[Database] Inicializando banco em: {settings.database.resolved_path}")
    Base.metadata.create_all(bind=engine)
    logger.info(f"[Database] Tabelas: {list(Base.metadata.tables.keys())}")

def get_session() -> Session:
    return SessionLocal()
