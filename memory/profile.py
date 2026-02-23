import json
import logging
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
sys.path.append(str(Path(__file__).resolve().parent.parent))
from memory.database import get_session, init_db, UserProfile, TrackPlayed

logger = logging.getLogger(__name__)

class ProfileKey:
    FAVORITE_GENRES      = "favorite_genres"
    FAVORITE_ARTISTS     = "favorite_artists"
    FAVORITE_TRACKS      = "favorite_tracks"
    PEAK_LISTENING_HOUR  = "peak_listening_hour"
    PREFERRED_ENERGY     = "preferred_energy"
    SKIP_RATE            = "skip_rate"
    TOTAL_TRACKS_PLAYED  = "total_tracks_played"
    LAST_MOOD            = "last_mood"
    LAST_SYNC_SPOTIFY    = "last_sync_spotify"
    LAST_PROFILE_UPDATE  = "last_profile_update"
    LISTENING_HOURS_DIST = "listening_hours_dist"

def set_profile_value(key: str, value: Any) -> bool:
    try:
        serialized = json.dumps(value, ensure_ascii=False)
        now = datetime.now(timezone.utc)

        with get_session() as session:
            record = session.query(UserProfile).filter_by(key=key).first()
            if record:
                record.value = serialized
                record.updated_at = now
            else:
                record = UserProfile(key=key, value=serialized, created_at=now, updated_at=now)
                session.add(record)
            session.commit()

        logger.debug(f"[Profile] Salvo: '{key}'")
        return True

    except Exception as e:
        logger.error(f"[Profile] Erro ao salvar '{key}': {e}", exc_info=True)
        return False

def get_profile_value(key: str, default: Any = None) -> Any:
    try:
        with get_session() as session:
            record = session.query(UserProfile).filter_by(key=key).first()

        if record is None:
            return default

        return json.loads(record.value)

    except Exception as e:
        logger.error(f"[Profile] Erro ao ler '{key}': {e}", exc_info=True)
        return default

def get_full_profile() -> dict[str, Any]:
    try:
        with get_session() as session:
            records = session.query(UserProfile).all()
        return {r.key: json.loads(r.value) for r in records}

    except Exception as e:
        logger.error(f"[Profile] Erro ao carregar perfil: {e}", exc_info=True)
        return {}

def delete_profile_value(key: str) -> bool:
    try:
        with get_session() as session:
            record = session.query(UserProfile).filter_by(key=key).first()
            if record:
                session.delete(record)
                session.commit()
        return True

    except Exception as e:
        logger.error(f"[Profile] Erro ao remover '{key}': {e}", exc_info=True)
        return False

def compute_profile_from_history(days: int = 30) -> dict[str, Any]:
    from datetime import timedelta

    logger.info(f"[Profile] Calculando perfil dos ultimos {days} dias...")

    try:
        since = datetime.now(timezone.utc) - timedelta(days=days)

        with get_session() as session:
            tracks = session.query(TrackPlayed).filter(TrackPlayed.played_at >= since).all()

        if not tracks:
            logger.warning("[Profile] Nenhuma faixa no historico.")
            return {}

        computed: dict[str, Any] = {}

        artist_counter: Counter = Counter()
        for t in tracks:
            for artist in (json.loads(t.artists) if t.artists else []):
                artist_counter[artist] += 1

        top_artists = [a for a, _ in artist_counter.most_common(10)]
        set_profile_value(ProfileKey.FAVORITE_ARTISTS, top_artists)
        computed[ProfileKey.FAVORITE_ARTISTS] = top_artists

        genre_counter: Counter = Counter()
        for t in tracks:
            if t.genres:
                for genre in json.loads(t.genres):
                    genre_counter[genre] += 1

        if genre_counter:
            top_genres = [g for g, _ in genre_counter.most_common(10)]
            set_profile_value(ProfileKey.FAVORITE_GENRES, top_genres)
            computed[ProfileKey.FAVORITE_GENRES] = top_genres

        hour_counter: Counter = Counter()
        for t in tracks:
            if t.hour_of_day is not None:
                hour_counter[t.hour_of_day] += 1

        if hour_counter:
            peak_hour = hour_counter.most_common(1)[0][0]
            set_profile_value(ProfileKey.PEAK_LISTENING_HOUR, peak_hour)
            computed[ProfileKey.PEAK_LISTENING_HOUR] = peak_hour
            dist = {str(h): c for h, c in hour_counter.items()}
            set_profile_value(ProfileKey.LISTENING_HOURS_DIST, dist)
            computed[ProfileKey.LISTENING_HOURS_DIST] = dist

        track_counter: Counter = Counter()
        track_meta: dict[str, dict] = {}
        for t in tracks:
            track_counter[t.track_id] += 1
            if t.track_id not in track_meta:
                track_meta[t.track_id] = {
                    "track_id": t.track_id,
                    "title": t.title,
                    "artists": json.loads(t.artists) if t.artists else [],
                }

        top_tracks = [track_meta[tid] for tid, _ in track_counter.most_common(10) if tid in track_meta]
        set_profile_value(ProfileKey.FAVORITE_TRACKS, top_tracks)
        computed[ProfileKey.FAVORITE_TRACKS] = top_tracks

        set_profile_value(ProfileKey.TOTAL_TRACKS_PLAYED, len(tracks))
        computed[ProfileKey.TOTAL_TRACKS_PLAYED] = len(tracks)

        now_str = datetime.now(timezone.utc).isoformat()
        set_profile_value(ProfileKey.LAST_PROFILE_UPDATE, now_str)
        computed[ProfileKey.LAST_PROFILE_UPDATE] = now_str

        logger.info(
            f"[Profile] Atualizado: {len(top_artists)} artistas, "
            f"{len(genre_counter) if genre_counter else 0} generos, "
            f"pico: {computed.get(ProfileKey.PEAK_LISTENING_HOUR, 'N/A')}h"
        )

        return computed

    except Exception as e:
        logger.error(f"[Profile] Erro ao calcular perfil: {e}", exc_info=True)
        return {}

def sync_from_spotify(top_tracks: list, top_artists: list) -> bool:
    try:
        if top_artists:
            set_profile_value("spotify_top_artists", [
                {"artist_id": a.artist_id, "name": a.name, "genres": a.genres, "popularity": a.popularity}
                for a in top_artists
            ])

            genre_counter: Counter = Counter()
            for a in top_artists:
                for genre in a.genres:
                    genre_counter[genre] += 1

            if genre_counter:
                set_profile_value(ProfileKey.FAVORITE_GENRES, [g for g, _ in genre_counter.most_common(10)])

        if top_tracks:
            set_profile_value("spotify_top_tracks", [
                {"track_id": t.track_id, "title": t.title, "artists": t.artists, "album": t.album, "uri": t.uri}
                for t in top_tracks
            ])

        set_profile_value(ProfileKey.LAST_SYNC_SPOTIFY, datetime.now(timezone.utc).isoformat())
        logger.info(f"[Profile] Sincronizado: {len(top_tracks)} tracks, {len(top_artists)} artistas.")
        return True

    except Exception as e:
        logger.error(f"[Profile] Erro ao sincronizar: {e}", exc_info=True)
        return False

def build_profile_summary() -> str:
    profile = get_full_profile()

    if not profile:
        return "Perfil do usuario ainda nao foi construido. Esta e a primeira sessao."

    lines: list[str] = ["=== Perfil Musical do Usuario ===\n"]

    artists = profile.get(ProfileKey.FAVORITE_ARTISTS, [])
    if artists:
        lines.append(f"Artistas favoritos: {', '.join(artists[:5])}")

    genres = profile.get(ProfileKey.FAVORITE_GENRES, [])
    if genres:
        lines.append(f"Generos favoritos: {', '.join(genres[:5])}")

    fav_tracks = profile.get(ProfileKey.FAVORITE_TRACKS, [])
    if fav_tracks:
        track_strs = [f"{t['title']} ({', '.join(t['artists'])})" for t in fav_tracks[:5]]
        lines.append(f"Musicas mais tocadas: {'; '.join(track_strs)}")

    peak_hour = profile.get(ProfileKey.PEAK_LISTENING_HOUR)
    if peak_hour is not None:
        lines.append(f"Horario de pico de escuta: {peak_hour}h")

    last_mood = profile.get(ProfileKey.LAST_MOOD)
    if last_mood:
        lines.append(f"Ultimo humor registrado: {last_mood}")

    total = profile.get(ProfileKey.TOTAL_TRACKS_PLAYED, 0)
    if total:
        lines.append(f"Total de musicas tocadas: {total}")

    last_update = profile.get(ProfileKey.LAST_PROFILE_UPDATE, "")
    if last_update:
        lines.append(f"\nPerfil atualizado em: {last_update[:19].replace('T', ' ')} UTC")

    return "\n".join(lines)
