import logging
import sys
import json
from dataclasses import dataclass
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Any
sys.path.append(str(Path(__file__).resolve().parent.parent))

from memory.database import get_session, TrackPlayed, Interaction
from memory.profile import (
    get_profile_value,
    ProfileKey,
    build_profile_summary,
)

logger = logging.getLogger(__name__)


@dataclass
class ListenerAnalytics:
    total_tracks_played: int
    total_listening_hours: float
    favorite_genres: list[str]
    favorite_artists: list[str]
    favorite_tracks: list[dict]
    peak_listening_hour: int
    listening_hours_distribution: dict[int, int]
    mood_distribution: dict[str, int]
    mood_trend: list[tuple[str, int]]
    skip_rate: float
    artist_diversity_score: float
    genre_diversity_score: float
    emerging_artists: list[str]
    recommendations_for_discovery: list[str]


@dataclass
class ArtistAnalytics:
    artist_name: str
    total_plays: int
    unique_listeners_estimated: int
    favorite_tracks: list[dict]
    listening_times: dict[str, int]
    mood_associated: list[str]
    skip_rate: float
    listener_demographics: dict[str, Any]
    similar_artists_in_rotation: list[str]
    trending_with_artist: list[str]


class MusicAnalytics:

    def __init__(self) -> None:
        logger.info("[Analytics] Inicializando módulo de análises...")

    def analyze_listener_profile(self, days: int = 30) -> ListenerAnalytics:
        try:
            since = datetime.now(timezone.utc) - timedelta(days=days)

            with get_session() as session:
                tracks = session.query(TrackPlayed).filter(
                    TrackPlayed.played_at >= since
                ).all()
                interactions = session.query(Interaction).filter(
                    Interaction.created_at >= since
                ).all()

            if not tracks:
                logger.warning("[Analytics] Nenhuma faixa no histórico")
                return self._empty_listener_analytics()

            total_ms = sum(t.duration_ms or 0 for t in tracks)
            total_hours = round(total_ms / (1000 * 60 * 60), 1)

            artist_counter = Counter()
            genre_counter = Counter()
            mood_counter = Counter()
            hour_distribution = Counter()

            for t in tracks:
                artists = json.loads(t.artists) if t.artists else []
                for artist in artists:
                    artist_counter[artist] += 1

                if t.genres:
                    for genre in json.loads(t.genres):
                        genre_counter[genre] += 1

                if t.mood:
                    mood_counter[t.mood] += 1

                if t.hour_of_day is not None:
                    hour_distribution[t.hour_of_day] += 1

            favorite_artists = [a for a, _ in artist_counter.most_common(10)]
            favorite_genres = [g for g, _ in genre_counter.most_common(10)]
            mood_distribution = dict(mood_counter.most_common(10))

            skip_count = sum(1 for i in interactions if "skip" in i.interaction_type.lower())
            skip_rate = (skip_count / len(interactions) * 100) if interactions else 0

            artist_diversity = min(100, (len(artist_counter) / max(len(tracks) / 10, 1)) * 100)
            genre_diversity = min(100, (len(genre_counter) / max(len(tracks) / 5, 1)) * 100)

            week_ago = datetime.now(timezone.utc) - timedelta(days=7)
            recent_tracks = [t for t in tracks if t.played_at >= week_ago]
            recent_artists = Counter()
            for t in recent_tracks:
                artists = json.loads(t.artists) if t.artists else []
                for artist in artists:
                    recent_artists[artist] += 1

            emerging = [
                a for a, _ in recent_artists.most_common(10)
                if a not in favorite_artists[:5]
            ]

            track_counter = Counter()
            track_meta = {}
            for t in tracks:
                track_counter[t.track_id] += 1
                if t.track_id not in track_meta:
                    track_meta[t.track_id] = {
                        "title": t.title,
                        "artists": json.loads(t.artists) if t.artists else [],
                        "album": t.album,
                        "plays": 0,
                    }
                track_meta[t.track_id]["plays"] += 1

            favorite_tracks = sorted(
                [{"id": tid, **meta} for tid, meta in track_meta.items()],
                key=lambda x: x["plays"],
                reverse=True,
            )[:10]

            peak_hour = max(hour_distribution.items(), key=lambda x: x[1])[0] \
                if hour_distribution else 12

            mood_trend = [
                (i.mood, i.id) for i in interactions[-7:]
                if i.mood
            ]

            recommendations = self._suggest_discovery(
                favorite_artists=favorite_artists,
                favorite_genres=favorite_genres,
            )

            return ListenerAnalytics(
                total_tracks_played=len(tracks),
                total_listening_hours=total_hours,
                favorite_genres=favorite_genres,
                favorite_artists=favorite_artists,
                favorite_tracks=favorite_tracks,
                peak_listening_hour=peak_hour,
                listening_hours_distribution={h: c for h, c in hour_distribution.items()},
                mood_distribution=mood_distribution,
                mood_trend=mood_trend,
                skip_rate=round(skip_rate, 2),
                artist_diversity_score=round(artist_diversity, 1),
                genre_diversity_score=round(genre_diversity, 1),
                emerging_artists=emerging,
                recommendations_for_discovery=recommendations,
            )

        except Exception as e:
            logger.error(f"[Analytics] Erro ao analisar listener: {e}", exc_info=True)
            return self._empty_listener_analytics()

    def get_mood_insights(self, days: int = 30) -> dict[str, Any]:
        try:
            since = datetime.now(timezone.utc) - timedelta(days=days)

            with get_session() as session:
                interactions = session.query(Interaction).filter(
                    Interaction.created_at >= since
                ).order_by(Interaction.created_at).all()

            if not interactions:
                return {"status": "sem_dados"}

            moods = [i.mood for i in interactions if i.mood]
            if not moods:
                return {"status": "sem_dados"}

            mood_counter = Counter(moods)
            mood_timeline = [(i.created_at, i.mood) for i in interactions if i.mood]

            transitions = Counter()
            for i in range(len(moods) - 1):
                transition = f"{moods[i]} → {moods[i + 1]}"
                transitions[transition] += 1

            return {
                "status": "sucesso",
                "mood_counts": dict(mood_counter),
                "most_common_mood": mood_counter.most_common(1)[0][0],
                "mood_transitions": dict(transitions.most_common(5)),
                "timeline": [
                    {"timestamp": ts.isoformat(), "mood": mood}
                    for ts, mood in mood_timeline[-20:]
                ],
                "insight": self._generate_mood_insight(moods),
            }

        except Exception as e:
            logger.error(f"[Analytics] Erro ao analisar moods: {e}", exc_info=True)
            return {"status": "erro", "error": str(e)}

    def get_listening_time_analysis(self, days: int = 30) -> dict[str, Any]:
        try:
            since = datetime.now(timezone.utc) - timedelta(days=days)

            with get_session() as session:
                tracks = session.query(TrackPlayed).filter(
                    TrackPlayed.played_at >= since,
                    TrackPlayed.hour_of_day.isnot(None)
                ).all()

            if not tracks:
                return {"status": "sem_dados"}

            hour_counter = Counter(t.hour_of_day for t in tracks)
            day_counter = Counter(t.day_of_week for t in tracks)

            periods = {
                "madrugada (00-05h)": sum(c for h, c in hour_counter.items() if 0 <= h < 5),
                "manhã (05-12h)": sum(c for h, c in hour_counter.items() if 5 <= h < 12),
                "tarde (12-18h)": sum(c for h, c in hour_counter.items() if 12 <= h < 18),
                "noite (18-23h)": sum(c for h, c in hour_counter.items() if 18 <= h < 23),
            }

            day_names = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]
            day_analysis = {
                day_names[d % 7]: day_counter.get(d, 0)
                for d in range(7)
            }

            return {
                "status": "sucesso",
                "peak_hour": max(hour_counter.items(), key=lambda x: x[1])[0],
                "peak_day": day_names[max(day_counter.items(), key=lambda x: x[1])[0] % 7],
                "by_hour": {h: c for h, c in sorted(hour_counter.items())},
                "by_period": periods,
                "by_day": day_analysis,
                "quietest_hour": min(hour_counter.items(), key=lambda x: x[1])[0],
            }

        except Exception as e:
            logger.error(f"[Analytics] Erro ao analisar tempo: {e}", exc_info=True)
            return {"status": "erro", "error": str(e)}

    def analyze_artist_listener_base(
        self, 
        artist_name: str,
        days: int = 90
    ) -> ArtistAnalytics:
        try:
            since = datetime.now(timezone.utc) - timedelta(days=days)

            with get_session() as session:
                artist_tracks = session.query(TrackPlayed).filter(
                    TrackPlayed.played_at >= since
                ).all()

            tracks = [
                t for t in artist_tracks
                if artist_name.lower() in (json.loads(t.artists) if t.artists else [])
            ]

            if not tracks:
                logger.warning(f"[Analytics] Nenhuma track de {artist_name}")
                return self._empty_artist_analytics(artist_name)

            total_plays = len(tracks)
            unique_listeners = len(set(t.track_id for t in tracks))  # Aproximado

            hour_counter = Counter(t.hour_of_day for t in tracks if t.hour_of_day)
            listening_times = {h: c for h, c in hour_counter.items()}

            mood_counter = Counter(t.mood for t in tracks if t.mood)
            associated_moods = [m for m, _ in mood_counter.most_common(5)]

            skip_count = sum(1 for t in tracks if t.context == "skip")
            skip_rate = (skip_count / total_plays * 100) if total_plays > 0 else 0

            co_artists = Counter()
            for t in tracks:
                artists = json.loads(t.artists) if t.artists else []
                for artist in artists:
                    if artist.lower() != artist_name.lower():
                        co_artists[artist] += 1

            similar_artists = [a for a, _ in co_artists.most_common(5)]

            return ArtistAnalytics(
                artist_name=artist_name,
                total_plays=total_plays,
                unique_listeners_estimated=unique_listeners,
                favorite_tracks=[{"title": t.title, "plays": 1} for t in tracks[:5]],
                listening_times=listening_times,
                mood_associated=associated_moods,
                skip_rate=round(skip_rate, 2),
                listener_demographics={},
                similar_artists_in_rotation=similar_artists,
                trending_with_artist=[],
            )

        except Exception as e:
            logger.error(f"[Analytics] Erro ao analisar artista: {e}", exc_info=True)
            return self._empty_artist_analytics(artist_name)

    def _suggest_discovery(
        self,
        favorite_artists: list[str],
        favorite_genres: list[str],
    ) -> list[str]:
        suggestions = []

        if favorite_artists:
            suggestions.append(
                f"Artistas similares a {favorite_artists[0]}"
            )
            suggestions.append(
                f"Colaborações com {favorite_artists[0]}"
            )

        if favorite_genres:
            suggestions.append(
                f"Subestimados em {favorite_genres[0]}"
            )
            suggestions.append(
                f"Subgêneros de {favorite_genres[0]}"
            )

        suggestions.append("Artistas viralizando no seu gosto")
        suggestions.append("Remixes e versões alternativas")
        suggestions.append("Influências históricas do seu estilo")

        return suggestions[:5]

    def _generate_mood_insight(self, moods: list[str]) -> str:
        if not moods:
            return "Sem dados de humor"

        counter = Counter(moods)
        top_mood = counter.most_common(1)[0][0]
        diversity = len(counter)

        if diversity > 5:
            return f"Seu humor é variável! Você alternou entre {diversity} moods diferentes. Recentemente mais {top_mood}."
        elif diversity <= 2:
            return f"Seu humor tem sido consistentemente {top_mood}."
        else:
            return f"Você alterna principalmente entre {', '.join([m for m, _ in counter.most_common(2)])}."

    def _empty_listener_analytics(self) -> ListenerAnalytics:
        return ListenerAnalytics(
            total_tracks_played=0,
            total_listening_hours=0,
            favorite_genres=[],
            favorite_artists=[],
            favorite_tracks=[],
            peak_listening_hour=12,
            listening_hours_distribution={},
            mood_distribution={},
            mood_trend=[],
            skip_rate=0,
            artist_diversity_score=0,
            genre_diversity_score=0,
            emerging_artists=[],
            recommendations_for_discovery=[],
        )

    def _empty_artist_analytics(self, artist_name: str) -> ArtistAnalytics:
        return ArtistAnalytics(
            artist_name=artist_name,
            total_plays=0,
            unique_listeners_estimated=0,
            favorite_tracks=[],
            listening_times={},
            mood_associated=[],
            skip_rate=0,
            listener_demographics={},
            similar_artists_in_rotation=[],
            trending_with_artist=[],
        )
