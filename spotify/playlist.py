import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import spotipy
from spotipy.exceptions import SpotifyException
sys.path.append(str(Path(__file__).resolve().parent.parent))
from spotify.auth import get_spotify_client
from spotify.search import TrackResult

logger = logging.getLogger(__name__)

@dataclass
class PlaylistInfo:
    playlist_id: str
    uri: str
    name: str
    description: str
    owner_id: str
    owner_name: str
    total_tracks: int
    public: bool
    collaborative: bool
    snapshot_id: str
    image_url: Optional[str]

    def __str__(self) -> str:
        visibility = "pública" if self.public else ("colaborativa" if self.collaborative else "privada")
        return (
            f"{self.name} [{visibility}]\n"
            f"   🎵 {self.total_tracks} faixas\n"
            f"   👤 {self.owner_name}\n"
            f"   {self.description[:80] + '...' if len(self.description) > 80 else self.description}"
        )

@dataclass
class PlaylistTrack:
    track: TrackResult
    added_at: str
    added_by: str

    def __str__(self) -> str:
        return f"{self.track.title} — {self.track.artists_str}  (adicionado em {self.added_at[:10]})"

class SpotifyPlaylist:
    """
    Limites da API:
      - Máximo de 100 faixas por chamada de adicionar/remover
      - Máximo de 50 playlists por chamada de listagem
      - Criar/editar playlists funciona no plano Free
    """

    _MAX_TRACKS_PER_REQUEST = 100

    def __init__(self, client: Optional[spotipy.Spotify] = None) -> None:
        self._sp = client or get_spotify_client()
        self._user_id: Optional[str] = None
        logger.info("SpotifyPlaylist inicializado.")

    def _get_user_id(self) -> str:
        """Retorna o ID do usuário autenticado, usando cache local para evitar chamadas repetidas."""
        if not self._user_id:
            user = self._sp.current_user()
            self._user_id = user["id"]
        return self._user_id

    def _parse_playlist(self, item: dict) -> PlaylistInfo:
        images = item.get("images") or []
        tracks = item.get("tracks") or {}
        owner = item.get("owner") or {}
        return PlaylistInfo(
            playlist_id=item["id"],
            uri=item["uri"],
            name=item["name"],
            description=item.get("description") or "",
            owner_id=owner.get("id", ""),
            owner_name=owner.get("display_name") or owner.get("id", "N/A"),
            total_tracks=tracks.get("total", 0) if isinstance(tracks, dict) else 0,
            public=item.get("public") or False,
            collaborative=item.get("collaborative") or False,
            snapshot_id=item.get("snapshot_id", ""),
            image_url=images[0]["url"] if images else None,
        )

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

    def _chunk(self, lst: list, size: int) -> list[list]:
        return [lst[i:i + size] for i in range(0, len(lst), size)]

    def create(
        self,
        name: str,
        description: str = "",
        public: bool = False,
        collaborative: bool = False,
    ) -> Optional[PlaylistInfo]:
        # Playlists colaborativas precisam ser privadas — regra da API
        if collaborative and public:
            logger.warning("[Playlist] Playlists colaborativas devem ser privadas. Definindo public=False.")
            public = False

        try:
            user_id = self._get_user_id()
            data = self._sp.user_playlist_create(
                user=user_id,
                name=name,
                public=public,
                collaborative=collaborative,
                description=description,
            )
            result = self._parse_playlist(data)
            logger.info(f"[Playlist] Criada: '{name}' (id: {result.playlist_id})")
            return result
        except SpotifyException as e:
            logger.error(f"[Playlist] Erro ao criar playlist '{name}': {e}")
            return None

    def delete(self, playlist_id: str) -> bool:
        """No Spotify, deletar uma playlist é tecnicamente deixar de segui-la."""
        try:
            self._sp.current_user_unfollow_playlist(playlist_id)
            logger.info(f"[Playlist] Removida: {playlist_id}")
            return True
        except SpotifyException as e:
            logger.error(f"[Playlist] Erro ao remover playlist {playlist_id}: {e}")
            return False

    def update_details(
        self,
        playlist_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        public: Optional[bool] = None,
        collaborative: Optional[bool] = None,
    ) -> bool:
        """Atualiza apenas os campos fornecidos."""
        kwargs: dict = {}
        if name is not None:
            kwargs["name"] = name
        if description is not None:
            kwargs["description"] = description
        if public is not None:
            kwargs["public"] = public
        if collaborative is not None:
            kwargs["collaborative"] = collaborative

        if not kwargs:
            logger.warning("[Playlist] update_details: nenhum campo para atualizar.")
            return False

        try:
            self._sp.playlist_change_details(playlist_id, **kwargs)
            logger.info(f"[Playlist] Detalhes atualizados para {playlist_id}: {kwargs}")
            return True
        except SpotifyException as e:
            logger.error(f"[Playlist] Erro ao atualizar detalhes de {playlist_id}: {e}")
            return False

    def add_tracks(
        self,
        playlist_id: str,
        uris: list[str],
        position: Optional[int] = None,
    ) -> bool:
        """Adiciona em lotes de 100 (limite da API do Spotify)."""
        if not uris:
            logger.warning("[Playlist] add_tracks: lista de URIs vazia.")
            return False

        try:
            chunks = self._chunk(uris, self._MAX_TRACKS_PER_REQUEST)
            for i, chunk in enumerate(chunks):
                pos = position + (i * self._MAX_TRACKS_PER_REQUEST) if position is not None else None
                self._sp.playlist_add_items(playlist_id, chunk, position=pos)
            logger.info(f"[Playlist] {len(uris)} faixas adicionadas a {playlist_id}.")
            return True
        except SpotifyException as e:
            logger.error(f"[Playlist] Erro ao adicionar faixas: {e}")
            return False

    def remove_tracks(self, playlist_id: str, uris: list[str]) -> bool:
        """Remove todas as ocorrências das URIs fornecidas."""
        if not uris:
            logger.warning("[Playlist] remove_tracks: lista de URIs vazia.")
            return False

        try:
            chunks = self._chunk(uris, self._MAX_TRACKS_PER_REQUEST)
            for chunk in chunks:
                self._sp.playlist_remove_all_occurrences_of_items(playlist_id, chunk)
            logger.info(f"[Playlist] {len(uris)} faixas removidas de {playlist_id}.")
            return True
        except SpotifyException as e:
            logger.error(f"[Playlist] Erro ao remover faixas: {e}")
            return False

    def reorder_track(
        self,
        playlist_id: str,
        range_start: int,
        insert_before: int,
        range_length: int = 1,
    ) -> bool:
        """Ex: mover faixa da posição 3 para o início: reorder_track(id, 3, 0)"""
        try:
            self._sp.playlist_reorder_items(
                playlist_id,
                range_start=range_start,
                insert_before=insert_before,
                range_length=range_length,
            )
            logger.info(f"[Playlist] Reordenado em {playlist_id}: {range_start} -> antes de {insert_before}")
            return True
        except SpotifyException as e:
            logger.error(f"[Playlist] Erro ao reordenar faixas: {e}")
            return False

    def replace_tracks(self, playlist_id: str, uris: list[str]) -> bool:
        """Substitui todas as faixas. A API aceita até 100 URIs direto; listas maiores usam lotes."""
        try:
            if len(uris) <= self._MAX_TRACKS_PER_REQUEST:
                self._sp.playlist_replace_items(playlist_id, uris)
            else:
                self._sp.playlist_replace_items(playlist_id, [])
                self.add_tracks(playlist_id, uris)
            logger.info(f"[Playlist] {playlist_id} substituída com {len(uris)} faixas.")
            return True
        except SpotifyException as e:
            logger.error(f"[Playlist] Erro ao substituir faixas: {e}")
            return False

    def get_user_playlists(self, limit: int = 50, fetch_all: bool = False) -> list[PlaylistInfo]:
        try:
            limit = max(1, min(50, limit))
            results: list[PlaylistInfo] = []
            data = self._sp.current_user_playlists(limit=limit)

            while data:
                items = data.get("items") or []
                results.extend([self._parse_playlist(i) for i in items if i])
                if fetch_all and data.get("next"):
                    data = self._sp.next(data)
                else:
                    break

            logger.info(f"[Playlist] {len(results)} playlists do usuário carregadas.")
            return results
        except SpotifyException as e:
            logger.error(f"[Playlist] Erro ao listar playlists: {e}")
            return []

    def get_playlist_tracks(
        self,
        playlist_id: str,
        limit: int = 100,
        fetch_all: bool = False,
    ) -> list[PlaylistTrack]:
        try:
            limit = max(1, min(100, limit))
            results: list[PlaylistTrack] = []
            data = self._sp.playlist_items(
                playlist_id,
                limit=limit,
                fields="items(added_at,added_by.id,track),next,total",
            )

            while data:
                items = data.get("items") or []
                for item in items:
                    # Ignora entradas vazias ou episódios de podcast
                    raw_track = item.get("track")
                    if not raw_track or raw_track.get("type") != "track":
                        continue
                    results.append(PlaylistTrack(
                        track=self._parse_track(raw_track),
                        added_at=item.get("added_at", ""),
                        added_by=(item.get("added_by") or {}).get("id", ""),
                    ))
                if fetch_all and data.get("next"):
                    data = self._sp.next(data)
                else:
                    break

            logger.info(f"[Playlist] {len(results)} faixas carregadas da playlist {playlist_id}.")
            return results
        except SpotifyException as e:
            logger.error(f"[Playlist] Erro ao buscar faixas da playlist {playlist_id}: {e}")
            return []

    def get_playlist_info(self, playlist_id: str) -> Optional[PlaylistInfo]:
        try:
            data = self._sp.playlist(playlist_id)
            return self._parse_playlist(data)
        except SpotifyException as e:
            logger.error(f"[Playlist] Erro ao buscar info da playlist {playlist_id}: {e}")
            return None
