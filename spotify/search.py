import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import spotipy
from spotipy.exceptions import SpotifyException
sys.path.append(str(Path(__file__).resolve().parent.parent))
from spotify.auth import get_spotify_client

logger = logging.getLogger(__name__)

@dataclass
class TrackResult:
    track_id: str
    uri: str
    title: str
    artists: list[str]
    album: str
    duration_ms: int
    popularity: int
    explicit: bool
    preview_url: Optional[str]

    @property
    def duration_str(self) -> str:
        total_s = self.duration_ms // 1000
        return f"{total_s // 60}:{total_s % 60:02d}"

    @property
    def artists_str(self) -> str:
        return ", ".join(self.artists)

    def __str__(self) -> str:
        explicit_tag = " [E]" if self.explicit else ""
        return (
            f"{self.title}{explicit_tag} — {self.artists_str}\n"
            f"   💿 {self.album}  ⏱️ {self.duration_str}  "
            f"🔥 popularidade: {self.popularity}/100"
        )

@dataclass
class ArtistResult:
    artist_id: str
    uri: str
    name: str
    genres: list[str]
    popularity: int
    followers: int
    image_url: Optional[str]

    @property
    def genres_str(self) -> str:
        return ", ".join(self.genres) if self.genres else "N/A"

    def __str__(self) -> str:
        return (
            f"{self.name}\n"
            f"   🎸 Gêneros: {self.genres_str}\n"
            f"   👥 Seguidores: {self.followers:,}  "
            f"🔥 popularidade: {self.popularity}/100"
        )

@dataclass
class AlbumResult:
    album_id: str
    uri: str
    title: str
    artists: list[str]
    release_date: str
    total_tracks: int
    album_type: str
    image_url: Optional[str]

    @property
    def artists_str(self) -> str:
        return ", ".join(self.artists)

    def __str__(self) -> str:
        return (
            f"{self.title} — {self.artists_str}\n"
            f"   📅 {self.release_date}  "
            f"🎵 {self.total_tracks} faixas  "
            f"[{self.album_type}]"
        )

@dataclass
class PlaylistResult:
    playlist_id: str
    uri: str
    name: str
    owner: str
    total_tracks: int
    description: str
    public: bool
    image_url: Optional[str]

    def __str__(self) -> str:
        visibility = "pública" if self.public else "privada"
        return (
            f"{self.name} — por {self.owner}\n"
            f"   🎵 {self.total_tracks} faixas  [{visibility}]\n"
            f"   {self.description[:80] + '...' if len(self.description) > 80 else self.description}"
        )

@dataclass
class PodcastResult:
    show_id: str
    uri: str
    name: str
    publisher: str
    description: str
    total_episodes: int
    language: str
    explicit: bool
    image_url: Optional[str]

    def __str__(self) -> str:
        explicit_tag = " [E]" if self.explicit else ""
        return (
            f"{self.name}{explicit_tag} — {self.publisher}\n"
            f"   🎙️ {self.total_episodes} episódios  🌐 {self.language}\n"
            f"   {self.description[:80] + '...' if len(self.description) > 80 else self.description}"
        )

class SpotifySearch:

    def __init__(self, client: Optional[spotipy.Spotify] = None) -> None:
        self._sp = client or get_spotify_client()
        logger.info("SpotifySearch inicializado.")

    def _parse_track(self, item: dict) -> TrackResult:
        return TrackResult(
            track_id=item["id"],
            uri=item["uri"],
            title=item["name"],
            artists=[a["name"] for a in item.get("artists", [])],
            album=item.get("album", {}).get("name", "N/A"),
            duration_ms=item.get("duration_ms", 0),
            popularity=item.get("popularity", 0),
            explicit=item.get("explicit", False),
            preview_url=item.get("preview_url"),
        )

    def _parse_artist(self, item: dict) -> ArtistResult:
        images = item.get("images", [])
        return ArtistResult(
            artist_id=item["id"],
            uri=item["uri"],
            name=item["name"],
            genres=item.get("genres", []),
            popularity=item.get("popularity", 0),
            followers=item.get("followers", {}).get("total", 0),
            image_url=images[0]["url"] if images else None,
        )

    def _parse_album(self, item: dict) -> AlbumResult:
        images = item.get("images", [])
        return AlbumResult(
            album_id=item["id"],
            uri=item["uri"],
            title=item["name"],
            artists=[a["name"] for a in item.get("artists", [])],
            release_date=item.get("release_date", "N/A"),
            total_tracks=item.get("total_tracks", 0),
            album_type=item.get("album_type", "N/A"),
            image_url=images[0]["url"] if images else None,
        )

    def _parse_playlist(self, item: dict) -> PlaylistResult:
        images = item.get("images", [])
        tracks = item.get("tracks", {})
        return PlaylistResult(
            playlist_id=item["id"],
            uri=item["uri"],
            name=item["name"],
            owner=item.get("owner", {}).get("display_name") or item.get("owner", {}).get("id", "N/A"),
            total_tracks=tracks.get("total", 0) if isinstance(tracks, dict) else 0,
            description=item.get("description", ""),
            public=item.get("public", False),
            image_url=images[0]["url"] if images else None,
        )

    def _parse_podcast(self, item: dict) -> PodcastResult:
        images = item.get("images", [])
        return PodcastResult(
            show_id=item["id"],
            uri=item["uri"],
            name=item["name"],
            publisher=item.get("publisher", "N/A"),
            description=item.get("description", ""),
            total_episodes=item.get("total_episodes", 0),
            language=item.get("language", "N/A"),
            explicit=item.get("explicit", False),
            image_url=images[0]["url"] if images else None,
        )

    def tracks(self, query: str, limit: int = 10, market: str = "BR") -> list[TrackResult]:
        try:
            limit = max(1, min(50, limit))
            data = self._sp.search(q=query, type="track", limit=limit, market=market)
            items = data.get("tracks", {}).get("items", [])
            results = [self._parse_track(i) for i in items if i]
            logger.info(f"[Search] Faixas '{query}': {len(results)} resultados.")
            return results
        except SpotifyException as e:
            logger.error(f"[Search] Erro ao buscar faixas: {e}")
            return []

    def artists(self, query: str, limit: int = 10) -> list[ArtistResult]:
        try:
            limit = max(1, min(50, limit))
            data = self._sp.search(q=query, type="artist", limit=limit)
            items = data.get("artists", {}).get("items", [])
            results = [self._parse_artist(i) for i in items if i]
            logger.info(f"[Search] Artistas '{query}': {len(results)} resultados.")
            return results
        except SpotifyException as e:
            logger.error(f"[Search] Erro ao buscar artistas: {e}")
            return []

    def albums(self, query: str, limit: int = 10, market: str = "BR") -> list[AlbumResult]:
        try:
            limit = max(1, min(50, limit))
            data = self._sp.search(q=query, type="album", limit=limit, market=market)
            items = data.get("albums", {}).get("items", [])
            results = [self._parse_album(i) for i in items if i]
            logger.info(f"[Search] Albums '{query}': {len(results)} resultados.")
            return results
        except SpotifyException as e:
            logger.error(f"[Search] Erro ao buscar álbuns: {e}")
            return []

    def playlists(self, query: str, limit: int = 10, market: str = "BR") -> list[PlaylistResult]:
        try:
            limit = max(1, min(50, limit))
            data = self._sp.search(q=query, type="playlist", limit=limit, market=market)
            items = data.get("playlists", {}).get("items", [])
            results = [self._parse_playlist(i) for i in items if i]
            logger.info(f"[Search] Playlists '{query}': {len(results)} resultados.")
            return results
        except SpotifyException as e:
            logger.error(f"[Search] Erro ao buscar playlists: {e}")
            return []

    def podcasts(self, query: str, limit: int = 10, market: str = "BR") -> list[PodcastResult]:
        try:
            limit = max(1, min(50, limit))
            data = self._sp.search(q=query, type="show", limit=limit, market=market)
            items = data.get("shows", {}).get("items", [])
            results = [self._parse_podcast(i) for i in items if i]
            logger.info(f"[Search] Podcasts '{query}': {len(results)} resultados.")
            return results
        except SpotifyException as e:
            logger.error(f"[Search] Erro ao buscar podcasts: {e}")
            return []

    def artist_top_tracks(self, artist_id: str, market: str = "BR") -> list[TrackResult]:
        try:
            data = self._sp.artist_top_tracks(artist_id, country=market)
            items = data.get("tracks", [])
            results = [self._parse_track(i) for i in items if i]
            logger.info(f"[Search] Top tracks do artista {artist_id}: {len(results)} faixas.")
            return results
        except SpotifyException as e:
            logger.error(f"[Search] Erro ao buscar top tracks: {e}")
            return []

    def artist_albums(
        self,
        artist_id: str,
        include_singles: bool = True,
        limit: int = 20,
        market: str = "BR",
    ) -> list[AlbumResult]:
        try:
            album_types = "album,single" if include_singles else "album"
            limit = max(1, min(50, limit))
            data = self._sp.artist_albums(
                artist_id,
                album_type=album_types,
                limit=limit,
                country=market,
            )
            items = data.get("items", [])
            results = [self._parse_album(i) for i in items if i]
            logger.info(f"[Search] Albums do artista {artist_id}: {len(results)} resultados.")
            return results
        except SpotifyException as e:
            logger.error(f"[Search] Erro ao buscar álbuns do artista: {e}")
            return []

    def related_artists(self, artist_id: str) -> list[ArtistResult]:
        try:
            data = self._sp.artist_related_artists(artist_id)
            items = data.get("artists", [])
            results = [self._parse_artist(i) for i in items if i]
            logger.info(f"[Search] Artistas relacionados a {artist_id}: {len(results)} resultados.")
            return results
        except SpotifyException as e:
            logger.error(f"[Search] Erro ao buscar artistas relacionados: {e}")
            return []

    def recently_played(self, limit: int = 20) -> list[TrackResult]:
        try:
            limit = max(1, min(50, limit))
            data = self._sp.current_user_recently_played(limit=limit)
            items = data.get("items", [])
            results = [self._parse_track(i["track"]) for i in items if i.get("track")]
            logger.info(f"[Search] Histórico recente: {len(results)} faixas.")
            return results
        except SpotifyException as e:
            logger.error(f"[Search] Erro ao buscar histórico recente: {e}")
            return []

    def top_tracks(self, limit: int = 20, time_range: str = "medium_term") -> list[TrackResult]:
        valid_ranges = {"short_term", "medium_term", "long_term"}
        if time_range not in valid_ranges:
            logger.warning(f"[Search] time_range inválido '{time_range}'. Usando 'medium_term'.")
            time_range = "medium_term"
        try:
            limit = max(1, min(50, limit))
            data = self._sp.current_user_top_tracks(limit=limit, time_range=time_range)
            items = data.get("items", [])
            results = [self._parse_track(i) for i in items if i]
            logger.info(f"[Search] Top tracks ({time_range}): {len(results)} faixas.")
            return results
        except SpotifyException as e:
            logger.error(f"[Search] Erro ao buscar top tracks: {e}")
            return []

    def top_artists(self, limit: int = 20, time_range: str = "medium_term") -> list[ArtistResult]:
        valid_ranges = {"short_term", "medium_term", "long_term"}
        if time_range not in valid_ranges:
            logger.warning(f"[Search] time_range inválido '{time_range}'. Usando 'medium_term'.")
            time_range = "medium_term"
        try:
            limit = max(1, min(50, limit))
            data = self._sp.current_user_top_artists(limit=limit, time_range=time_range)
            items = data.get("items", [])
            results = [self._parse_artist(i) for i in items if i]
            logger.info(f"[Search] Top artists ({time_range}): {len(results)} artistas.")
            return results
        except SpotifyException as e:
            logger.error(f"[Search] Erro ao buscar top artists: {e}")
            return []

    def liked_tracks(self, limit: int = 50) -> list[TrackResult]:
        try:
            limit = max(1, min(50, limit))
            data = self._sp.current_user_saved_tracks(limit=limit)
            items = data.get("items", [])
            results = [self._parse_track(i["track"]) for i in items if i.get("track")]
            logger.info(f"[Search] Liked songs: {len(results)} faixas.")
            return results
        except SpotifyException as e:
            logger.error(f"[Search] Erro ao buscar liked tracks: {e}")
            return []
