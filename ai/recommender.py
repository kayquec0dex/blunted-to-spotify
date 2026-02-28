import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
sys.path.append(str(Path(__file__).resolve().parent.parent))
from spotify.auth import get_spotify_client
from spotify.search import SpotifySearch, TrackResult
from memory.history import record_interaction, record_tracks_batch
from memory.profile import build_profile_summary
from ai.llm import get_llm_client
logger = logging.getLogger(__name__)

@dataclass
class RecommendationResult:
    tracks: list[TrackResult]
    mood: Optional[str]
    context: str
    reasoning: str
    not_found: list[str]

    @property
    def uris(self) -> list[str]:
        return [t.uri for t in self.tracks]

    def __str__(self) -> str:
        lines = [f"{len(self.tracks)} musicas recomendadas"]
        if self.mood:
            lines.append(f"   Humor detectado: {self.mood}")
        if self.reasoning:
            lines.append(f"   Raciocinio: {self.reasoning[:120]}")
        lines.append("")
        for i, t in enumerate(self.tracks, 1):
            lines.append(f"   {i}. {t.title} - {t.artists_str}")
        if self.not_found:
            lines.append(f"\n   Nao encontradas no Spotify: {', '.join(self.not_found)}")
        return "\n".join(lines)

RECOMMENDATION_PROMPT = """Voce eh um curador musical de classe mundial especializado em criar recomendacoes hipermencionadas.

CONTEXTO DO USUARIO:
{profile_context}

PEDIDO ATUAL: "{request}"
{mood_line}

Sua tarefa: Recomender EXATAMENTE {n} musicas que:
1. Façam sentido absoluto para esse usuario, nesse momento
2. Equilibrem familiar + descoberta (80% seus estilos, 20% novo)
3. Tenham uma narrativa fluida (inicio -> auge -> resolucao)
4. Variem os artistas (NO repetir o mesmo artista 2x)
5. Sejam REAIS e existam NO Spotify

QUALIDADE > QUANTIDADE: Melhor recomendar 3 musicas perfeitas que 10 genéricas.

ANALISE PROFUNDA:
- Energia: Detecta se o usuario quer energico (80+ BPM) ou suave (60-80 BPM)
- Familiaridade: Mistura artistas conhecidos com novos descobertos
- Coesao: As musicas devem "conversar" entre si musicalmente
- Raciocinio: Explique por que cada musica faz sentido

FORMATO DE RESPOSTA (JSON VALIDO):
{{
  "mood": "humor detectado (ex: energia alta, melancvia, criativo)",
  "reasoning": "porque essas {n} musicas sao perfeitas para esse usuario",
  "recommendations": [
    {{"title": "Nome Exato da Musica", "artist": "Nome do Artista", "why": "conexao com usuario"}},
    {{"title": "...", "artist": "...", "why": "..."}}
  ],
  "narrative_flow": "como a sequencia progride (calmaria -> climax -> resolucao)"
}}

BONUS: Se conseguir conectar com algo pessoal do usuario (baseado no perfil), ganha pontos!
"""

class MusicRecommender:

    def __init__(self, spotify_client=None) -> None:
        self._sp = spotify_client or get_spotify_client()
        self._search = SpotifySearch(client=self._sp)
        self._llm = get_llm_client()
        logger.info(f"[Recommender] Inicializado | LLM: {self._llm.model_name}")

    def _find_track_on_spotify(self, title: str, artist: str) -> Optional[TrackResult]:
        """Tenta query estruturada primeiro, cai em busca simples se não encontrar."""
        results = self._search.tracks(f"track:{title} artist:{artist}", limit=1)
        if results:
            return results[0]
        results = self._search.tracks(f"{title} {artist}", limit=1)
        return results[0] if results else None

    def recommend(
        self,
        request: str,
        n: int = 5,
        mood: Optional[str] = None,
        profile_context: Optional[str] = None,
        save_to_history: bool = True,
    ) -> RecommendationResult:
        n = max(1, min(10, n))

        if profile_context is None:
            profile_context = build_profile_summary()

        mood_line = f"Humor atual do usuario: {mood}" if mood else ""

        prompt = RECOMMENDATION_PROMPT.format(
            n=n,
            profile_context=profile_context,
            request=request,
            mood_line=mood_line,
        )

        logger.info(f"[Recommender] Pedido: '{request}' | n={n} | mood={mood}")

        try:
            llm_data = self._llm.generate_json(prompt=prompt, temperature=0.8, max_tokens=1024)
        except (ValueError, RuntimeError) as e:
            logger.error(f"[Recommender] Falha na chamada ao LLM: {e}")
            return RecommendationResult(
                tracks=[], mood=mood, context=request,
                reasoning="Erro ao obter recomendacoes do LLM.", not_found=[],
            )

        detected_mood = llm_data.get("mood", mood or "")
        reasoning = llm_data.get("reasoning", "")
        suggestions = llm_data.get("recommendations", [])

        logger.info(f"[Recommender] LLM sugeriu {len(suggestions)} musicas. Mood: '{detected_mood}'")

        found_tracks: list[TrackResult] = []
        not_found: list[str] = []

        for suggestion in suggestions:
            title = suggestion.get("title", "").strip()
            artist = suggestion.get("artist", "").strip()

            if not title or not artist:
                continue

            track = self._find_track_on_spotify(title, artist)

            if track:
                found_tracks.append(track)
                logger.debug(f"[Recommender] Encontrada: '{track.title}' - {track.artists_str}")
            else:
                not_found.append(f"{title} - {artist}")
                logger.warning(f"[Recommender] Nao encontrada: '{title}' - {artist}")

        result = RecommendationResult(
            tracks=found_tracks,
            mood=detected_mood,
            context=request,
            reasoning=reasoning,
            not_found=not_found,
        )

        if save_to_history and found_tracks:
            interaction = record_interaction(
                interaction_type="recommendation",
                user_input=request,
                mood=detected_mood,
                assistant_response=reasoning,
                metadata={
                    "n_requested": n,
                    "n_found": len(found_tracks),
                    "not_found": not_found,
                    "uris": result.uris,
                },
            )
            record_tracks_batch(
                tracks=found_tracks,
                context="recommendation",
                mood=detected_mood,
                interaction_id=interaction.id if interaction else None,
            )

        logger.info(
            f"[Recommender] Resultado: {len(found_tracks)}/{len(suggestions)} faixas encontradas."
        )

        return result
