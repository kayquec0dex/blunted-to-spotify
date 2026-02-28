import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import settings
from memory.profile import build_profile_summary
from memory.history import get_recent_tracks, get_recent_interactions
from memory.database import init_db
logger = logging.getLogger(__name__)

SYSTEM_PROMPT_BASE = """Voce e o {name}, um assistente musical inteligente integrado ao Spotify.

Sua personalidade:
- Apaixonado por musica, com conhecimento amplo de generos, artistas e historia musical
- Comunicativo, descontraido e levemente irreverente, mas sempre util
- Proativo: sugere musicas mesmo quando o pedido eh vago ou ambiguo
- Aprende com os gostos do usuario ao longo do tempo
- Entende tanto ouvintes casuais quanto musicos e produtores

Suas super-poderes:
- Recomendar musicas com precision cirurgica (humor, energia, periodo do dia)
- Controlar Spotify como um maestro (play, pause, skip, volume, modo shuffle/repeat)
- Criar playlists tematizadas automaticamente com narrativa musical
- Buscar em tempo real no catalogo completo do Spotify
- Analisar seus padroes de escuta e revelar insights surpreendentes
- Explorar territorios musicais desconhecidos baseado no seu estilo

Sua abordagem:
1. OUÇA - entenda o contexto da mensagem (humor, momento do dia, atividade)
2. ANALISE - use o perfil do usuario para personalizar respostas
3. REVELE - sempre explique por que essa recomendacao faz sentido
4. EXECUTE - toque, crie, organize com precision

Regras importantes:
- Responda em {language}
- Seja conciso: respostas curtas e objetivas sao melhores que longos textos
- Quando recomendar, inclua TITULO + ARTISTA
- Quando não conseguir algo, explique claramente o motivo
- Assuma que o usuario quer descobrir novas musicas (seja proativo!)
- Se o usuario informar um humor, leve isso em conta nas proximas acoes
- Para artistas/produtores, foque em insights e tendencias

Capacidades especiais de deteccao:
- Se menciona "trabalho/estudo" → ACTIVITY_PLAYLIST com BPM 120-130
- Se menciona "encontro/festa" → DISCOVER artistas trending + RECOMMEND energetic
- Se menciona "correr/academia" → ACTIVITY_PLAYLIST com progressao de energia
- Se menciona "relaxar/dormir" → RECOMMEND calming + setvolume lower
- Se menciona "artista X" → ANALYZE ese artista + DISCOVERY similar artists
- Se menciona numeros + "%" → ANALYZE com especifico ou SET_VOLUME
"""

class ContextBuilder:
    def __init__(self) -> None:
        self._name = settings.assistant.name
        self._language = settings.assistant.language

    def build_system_prompt(self, current_mood: Optional[str] = None) -> str:
        prompt = SYSTEM_PROMPT_BASE.format(name=self._name, language=self._language)

        profile_summary = build_profile_summary()
        if profile_summary:
            prompt += f"\n\n{profile_summary}"

        if current_mood:
            prompt += f"\n\nHumor atual do usuario: {current_mood}"

        return prompt

    def build_player_context(
        self,
        current_track_str: Optional[str] = None,
        device_name: Optional[str] = None,
    ) -> str:
        if not current_track_str:
            return "Player: nenhuma faixa em reproducao no momento."

        lines = ["Estado atual do Spotify:", f"  {current_track_str}"]
        if device_name:
            lines.append(f"  Dispositivo: {device_name}")

        return "\n".join(lines)

    def build_history_context(self, limit: int = 5) -> str:
        try:
            interactions = get_recent_interactions(limit=limit, days=1)
            if not interactions:
                return ""

            lines = ["Historico recente desta sessao:"]
            for interaction in reversed(interactions):
                if interaction.user_input:
                    lines.append(f"  Usuario: {interaction.user_input}")
                if interaction.assistant_response:
                    response = interaction.assistant_response
                    if len(response) > 200:
                        response = response[:200] + "..."
                    lines.append(f"  {self._name}: {response}")

            return "\n".join(lines)

        except Exception as e:
            logger.warning(f"[Context] Erro ao buscar historico: {e}")
            return ""

    def build_recent_tracks_context(self, limit: int = 5) -> str:
        try:
            tracks = get_recent_tracks(limit=limit, days=1)
            if not tracks:
                return ""

            lines = ["Musicas tocadas recentemente (evite repetir):"]
            for t in tracks:
                artists_str = ", ".join(json.loads(t.artists) if t.artists else [])
                lines.append(f"  - {t.title} - {artists_str}")

            return "\n".join(lines)

        except Exception as e:
            logger.warning(f"[Context] Erro ao buscar faixas recentes: {e}")
            return ""

    def build_full_context(
        self,
        current_mood: Optional[str] = None,
        current_track_str: Optional[str] = None,
        device_name: Optional[str] = None,
        include_history: bool = True,
        include_recent_tracks: bool = True,
    ) -> dict:
        system_prompt = self.build_system_prompt(current_mood=current_mood)
        context_parts: list[str] = []

        player_ctx = self.build_player_context(current_track_str, device_name)
        if player_ctx:
            context_parts.append(player_ctx)

        if include_recent_tracks:
            recent_ctx = self.build_recent_tracks_context()
            if recent_ctx:
                context_parts.append(recent_ctx)

        if include_history:
            history_ctx = self.build_history_context()
            if history_ctx:
                context_parts.append(history_ctx)

        hour = datetime.now(timezone.utc).hour
        if 5 <= hour < 12:
            period = "manha"
        elif 12 <= hour < 18:
            period = "tarde"
        elif 18 <= hour < 23:
            period = "noite"
        else:
            period = "madrugada"

        context_parts.append(f"Horario atual: {hour}h ({period})")

        return {
            "system_prompt": system_prompt,
            "context_block": "\n\n".join(context_parts),
        }
