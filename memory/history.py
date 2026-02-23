import json
import logging
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
sys.path.append(str(Path(__file__).resolve().parent.parent))
from memory.database import get_session, init_db, TrackPlayed, Interaction
from spotify.search import TrackResult

logger = logging.getLogger(__name__)

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)

def _extract_time_fields(dt: datetime) -> tuple[int, int]:
    return dt.hour, dt.weekday()

def record_track(
    track: TrackResult,
    context: str = "user_request",
    mood: Optional[str] = None,
    genres: Optional[list[str]] = None,
    interaction_id: Optional[int] = None,
    played_at: Optional[datetime] = None,
) -> Optional[TrackPlayed]:
    try:
        ts = played_at or _now_utc()
        hour, dow = _extract_time_fields(ts)

        record = TrackPlayed(
            track_id=track.track_id,
            track_uri=track.uri,
            title=track.title,
            artists=json.dumps(track.artists, ensure_ascii=False),
            album=track.album,
            duration_ms=track.duration_ms,
            genres=json.dumps(genres, ensure_ascii=False) if genres else None,
            popularity=track.popularity,
            played_at=ts,
            hour_of_day=hour,
            day_of_week=dow,
            context=context,
            mood=mood,
            interaction_id=interaction_id,
        )

        with get_session() as session:
            session.add(record)
            session.commit()

        logger.debug(f"[History] Faixa registrada: '{track.title}' (contexto: {context})")
        return record

    except Exception as e:
        logger.error(f"[History] Erro ao registrar faixa '{track.title}': {e}", exc_info=True)
        return None

def record_tracks_batch(
    tracks: list[TrackResult],
    context: str = "recommendation",
    mood: Optional[str] = None,
    interaction_id: Optional[int] = None,
) -> int:
    if not tracks:
        return 0

    try:
        ts = _now_utc()
        hour, dow = _extract_time_fields(ts)

        records = [
            TrackPlayed(
                track_id=t.track_id,
                track_uri=t.uri,
                title=t.title,
                artists=json.dumps(t.artists, ensure_ascii=False),
                album=t.album,
                duration_ms=t.duration_ms,
                popularity=t.popularity,
                played_at=ts,
                hour_of_day=hour,
                day_of_week=dow,
                context=context,
                mood=mood,
                interaction_id=interaction_id,
            )
            for t in tracks
        ]

        with get_session() as session:
            session.add_all(records)
            session.commit()

        logger.info(f"[History] {len(records)} faixas registradas em lote (contexto: {context})")
        return len(records)

    except Exception as e:
        logger.error(f"[History] Erro ao registrar faixas em lote: {e}", exc_info=True)
        return 0

def record_interaction(
    interaction_type: str,
    user_input: Optional[str] = None,
    mood: Optional[str] = None,
    assistant_response: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> Optional[Interaction]:
    try:
        ts = _now_utc()
        hour, dow = _extract_time_fields(ts)

        record = Interaction(
            interaction_type=interaction_type,
            user_input=user_input,
            mood=mood,
            assistant_response=assistant_response,
            metadata_json=json.dumps(metadata, ensure_ascii=False) if metadata else None,
            created_at=ts,
            hour_of_day=hour,
            day_of_week=dow,
        )

        with get_session() as session:
            session.add(record)
            session.commit()

        logger.debug(f"[History] Interacao registrada: tipo='{interaction_type}'")
        return record

    except Exception as e:
        logger.error(f"[History] Erro ao registrar interacao: {e}", exc_info=True)
        return None

def update_interaction_feedback(interaction_id: int, positive: bool) -> bool:
    try:
        with get_session() as session:
            record = session.get(Interaction, interaction_id)
            if not record:
                logger.warning(f"[History] Interacao {interaction_id} nao encontrada.")
                return False
            record.feedback_positive = positive
            session.commit()

        logger.debug(f"[History] Feedback {interaction_id}: {'positivo' if positive else 'negativo'}")
        return True

    except Exception as e:
        logger.error(f"[History] Erro ao atualizar feedback: {e}", exc_info=True)
        return False

def get_recent_tracks(
    limit: int = 20,
    days: int = 7,
    context: Optional[str] = None,
) -> list[TrackPlayed]:
    try:
        since = _now_utc() - timedelta(days=days)

        with get_session() as session:
            query = session.query(TrackPlayed).filter(TrackPlayed.played_at >= since)
            if context:
                query = query.filter(TrackPlayed.context == context)
            results = query.order_by(TrackPlayed.played_at.desc()).limit(limit).all()

        return results

    except Exception as e:
        logger.error(f"[History] Erro ao consultar faixas recentes: {e}", exc_info=True)
        return []

def get_most_played_tracks(limit: int = 20, days: int = 30) -> list[dict]:
    try:
        from sqlalchemy import func

        since = _now_utc() - timedelta(days=days)

        with get_session() as session:
            rows = (
                session.query(
                    TrackPlayed.track_id,
                    TrackPlayed.title,
                    TrackPlayed.artists,
                    func.count(TrackPlayed.id).label("play_count"),
                )
                .filter(TrackPlayed.played_at >= since)
                .group_by(TrackPlayed.track_id)
                .order_by(func.count(TrackPlayed.id).desc())
                .limit(limit)
                .all()
            )

        return [
            {
                "track_id": r.track_id,
                "title": r.title,
                "artists": json.loads(r.artists) if r.artists else [],
                "play_count": r.play_count,
            }
            for r in rows
        ]

    except Exception as e:
        logger.error(f"[History] Erro ao consultar faixas mais tocadas: {e}", exc_info=True)
        return []

def get_recent_interactions(
    limit: int = 20,
    interaction_type: Optional[str] = None,
    days: int = 7,
) -> list[Interaction]:
    try:
        since = _now_utc() - timedelta(days=days)

        with get_session() as session:
            query = session.query(Interaction).filter(Interaction.created_at >= since)
            if interaction_type:
                query = query.filter(Interaction.interaction_type == interaction_type)
            results = query.order_by(Interaction.created_at.desc()).limit(limit).all()

        return results

    except Exception as e:
        logger.error(f"[History] Erro ao consultar interacoes recentes: {e}", exc_info=True)
        return []

def get_listening_hours_distribution(days: int = 30) -> dict[int, int]:
    try:
        from sqlalchemy import func

        since = _now_utc() - timedelta(days=days)

        with get_session() as session:
            rows = (
                session.query(
                    TrackPlayed.hour_of_day,
                    func.count(TrackPlayed.id).label("count"),
                )
                .filter(TrackPlayed.played_at >= since)
                .filter(TrackPlayed.hour_of_day.isnot(None))
                .group_by(TrackPlayed.hour_of_day)
                .all()
            )

        return {r.hour_of_day: r.count for r in rows}

    except Exception as e:
        logger.error(f"[History] Erro ao calcular distribuicao por hora: {e}", exc_info=True)
        return {}

def get_total_counts() -> dict[str, int]:
    try:
        from sqlalchemy import func

        with get_session() as session:
            total_played = session.query(func.count(TrackPlayed.id)).scalar() or 0
            total_interactions = session.query(func.count(Interaction.id)).scalar() or 0
            unique_tracks = session.query(func.count(func.distinct(TrackPlayed.track_id))).scalar() or 0

        return {
            "total_tracks_played": total_played,
            "total_interactions": total_interactions,
            "unique_tracks": unique_tracks,
        }

    except Exception as e:
        logger.error(f"[History] Erro ao contar registros: {e}", exc_info=True)
        return {"total_tracks_played": 0, "total_interactions": 0, "unique_tracks": 0}
