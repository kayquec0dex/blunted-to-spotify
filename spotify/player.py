import logging
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import spotipy
from spotipy.exceptions import SpotifyException
sys.path.append(str(Path(__file__).resolve().parent.parent))
from spotify.auth import get_spotify_client

logger = logging.getLogger(__name__)

@dataclass
class TrackInfo:
    track_id: str
    title: str
    artists: list[str]
    album: str
    duration_ms: int
    progress_ms: int
    is_playing: bool
    uri: str

    @property
    def duration_str(self) -> str:
        total_s = self.duration_ms // 1000
        return f"{total_s // 60}:{total_s % 60:02d}"

    @property
    def progress_str(self) -> str:
        total_s = self.progress_ms // 1000
        return f"{total_s // 60}:{total_s % 60:02d}"

    @property
    def artists_str(self) -> str:
        return ", ".join(self.artists)

    def __str__(self) -> str:
        status = "▶️" if self.is_playing else "⏸️"
        return (
            f"{status} {self.title} — {self.artists_str}\n"
            f"   💿 {self.album}\n"
            f"   ⏱️  {self.progress_str} / {self.duration_str}"
        )

@dataclass
class DeviceInfo:
    device_id: str
    name: str
    device_type: str
    is_active: bool
    is_private_session: bool
    volume_percent: int

    def __str__(self) -> str:
        active_marker = " ← ativo" if self.is_active else ""
        return f"[{self.device_type}] {self.name} (vol: {self.volume_percent}%){active_marker}"

class SpotifyPlayer:

    def __init__(self, client: Optional[spotipy.Spotify] = None) -> None:
        self._sp = client or get_spotify_client()
        logger.info("SpotifyPlayer inicializado.")

    def _call(self, action: str, fn, *args, **kwargs) -> bool:
        """
        Wrapper para chamadas à API. Trata erros HTTP comuns:
          - 403: Premium necessário
          - 404: Nenhum dispositivo ativo
          - 429: Rate limit atingido
        """
        try:
            fn(*args, **kwargs)
            logger.info(f"[Player] {action} — OK")
            return True
        except SpotifyException as e:
            if e.http_status == 403:
                logger.error(f"[Player] {action} falhou: acesso negado (403). Requer Spotify Premium.")
            elif e.http_status == 404:
                logger.error(f"[Player] {action} falhou: nenhum dispositivo ativo (404).")
            elif e.http_status == 429:
                logger.error(f"[Player] {action} falhou: rate limit atingido (429).")
            else:
                logger.error(f"[Player] {action} falhou: {e}")
            return False
        except Exception as e:
            logger.error(f"[Player] {action} — erro inesperado: {e}", exc_info=True)
            return False

    def play(
        self,
        uris: Optional[list[str]] = None,
        context_uri: Optional[str] = None,
        device_id: Optional[str] = None,
        offset: Optional[int] = None,
    ) -> bool:
        """
        Inicia ou retoma a reprodução.
          1. Sem argumentos: retoma a reprodução pausada
          2. Com `uris`: toca uma lista de faixas específicas
          3. Com `context_uri`: toca um álbum, playlist ou artista
        """
        kwargs: dict = {"device_id": device_id}
        if uris:
            kwargs["uris"] = uris
        if context_uri:
            kwargs["context_uri"] = context_uri
        if offset is not None:
            kwargs["offset"] = {"position": offset}
        return self._call("Play", self._sp.start_playback, **kwargs)

    def pause(self, device_id: Optional[str] = None) -> bool:
        return self._call("Pause", self._sp.pause_playback, device_id=device_id)

    def toggle_play_pause(self) -> bool:
        current = self.get_current_track()
        if current is None:
            logger.warning("[Player] Toggle play/pause: nenhuma faixa em reprodução.")
            return False
        return self.pause() if current.is_playing else self.play()

    def skip(self, device_id: Optional[str] = None) -> bool:
        return self._call("Skip (próxima)", self._sp.next_track, device_id=device_id)

    def previous(self, device_id: Optional[str] = None) -> bool:
        """
        Volta para a faixa anterior.
        Nota: se o progresso atual for maior que ~3s, o Spotify reinicia
        a faixa atual em vez de voltar para a anterior (comportamento padrão).
        """
        return self._call("Anterior", self._sp.previous_track, device_id=device_id)

    def seek(self, position_ms: int, device_id: Optional[str] = None) -> bool:
        if position_ms < 0:
            logger.warning("[Player] Seek: posição não pode ser negativa. Usando 0.")
            position_ms = 0
        return self._call(
            f"Seek ({position_ms}ms)",
            self._sp.seek_track,
            position_ms=position_ms,
            device_id=device_id,
        )

    def set_volume(self, volume: int, device_id: Optional[str] = None) -> bool:
        volume = max(0, min(100, volume))
        return self._call(
            f"Volume ({volume}%)",
            self._sp.volume,
            volume_percent=volume,
            device_id=device_id,
        )

    def volume_up(self, step: int = 10) -> bool:
        current = self.get_current_track()
        if current is None:
            logger.warning("[Player] Volume up: não foi possível obter o estado atual.")
            return False
        devices = self.get_devices()
        active = next((d for d in devices if d.is_active), None)
        if not active:
            logger.warning("[Player] Volume up: nenhum dispositivo ativo encontrado.")
            return False
        return self.set_volume(min(100, active.volume_percent + step))

    def volume_down(self, step: int = 10) -> bool:
        devices = self.get_devices()
        active = next((d for d in devices if d.is_active), None)
        if not active:
            logger.warning("[Player] Volume down: nenhum dispositivo ativo encontrado.")
            return False
        return self.set_volume(max(0, active.volume_percent - step))

    def mute(self) -> bool:
        return self.set_volume(0)

    def set_shuffle(self, state: bool, device_id: Optional[str] = None) -> bool:
        label = "ativado" if state else "desativado"
        return self._call(f"Shuffle {label}", self._sp.shuffle, state=state, device_id=device_id)

    def set_repeat(self, mode: str, device_id: Optional[str] = None) -> bool:
        """mode: 'off', 'track' ou 'context'."""
        valid_modes = {"off", "track", "context"}
        if mode not in valid_modes:
            logger.error(f"[Player] Repeat: modo inválido '{mode}'. Use: {valid_modes}")
            return False
        return self._call(f"Repeat ({mode})", self._sp.repeat, state=mode, device_id=device_id)

    def add_to_queue(self, uri: str, device_id: Optional[str] = None) -> bool:
        return self._call(
            f"Adicionar à fila ({uri})",
            self._sp.add_to_queue,
            uri=uri,
            device_id=device_id,
        )

    def get_queue(self) -> dict:
        """Retorna a fila atual. Chaves: 'currently_playing' e 'queue'."""
        try:
            return self._sp.queue() or {}
        except SpotifyException as e:
            logger.error(f"[Player] Erro ao buscar fila: {e}")
            return {}

    def get_current_track(self) -> Optional[TrackInfo]:
        try:
            data = self._sp.current_playback()
            if not data or not data.get("item"):
                logger.debug("[Player] Nenhuma faixa em reprodução no momento.")
                return None
            item = data["item"]
            return TrackInfo(
                track_id=item["id"],
                title=item["name"],
                artists=[a["name"] for a in item["artists"]],
                album=item["album"]["name"],
                duration_ms=item["duration_ms"],
                progress_ms=data.get("progress_ms", 0),
                is_playing=data.get("is_playing", False),
                uri=item["uri"],
            )
        except SpotifyException as e:
            logger.error(f"[Player] Erro ao buscar faixa atual: {e}")
            return None

    def get_devices(self) -> list[DeviceInfo]:
        try:
            data = self._sp.devices()
            devices = data.get("devices", [])
            result = [
                DeviceInfo(
                    device_id=d["id"],
                    name=d["name"],
                    device_type=d["type"],
                    is_active=d["is_active"],
                    is_private_session=d["is_private_session"],
                    volume_percent=d.get("volume_percent", 0),
                )
                for d in devices
            ]
            if not result:
                logger.warning("[Player] Nenhum dispositivo ativo. Abra o Spotify em algum dispositivo.")
            return result
        except SpotifyException as e:
            logger.error(f"[Player] Erro ao listar dispositivos: {e}")
            return []

    def transfer_playback(self, device_id: str, force_play: bool = False) -> bool:
        """force_play=True inicia a reprodução imediatamente no novo dispositivo."""
        return self._call(
            f"Transferir para dispositivo ({device_id})",
            self._sp.transfer_playback,
            device_id=device_id,
            force_play=force_play,
        )

    def get_active_device(self) -> Optional[DeviceInfo]:
        devices = self.get_devices()
        return next((d for d in devices if d.is_active), None)
