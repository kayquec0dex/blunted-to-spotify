import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import settings
from spotify.auth import get_spotify_client
from spotify.player import SpotifyPlayer
from spotify.search import SpotifySearch
from spotify.playlist import SpotifyPlaylist
from ai.context import ContextBuilder
from ai.recommender import MusicRecommender
from ai.llm import get_llm_client
from memory.database import init_db
from memory.history import record_interaction
from memory.profile import (
    compute_profile_from_history,
    sync_from_spotify,
    set_profile_value,
    ProfileKey,
)

logger = logging.getLogger(__name__)

@dataclass
class AssistantResponse:
    text: str
    action_taken: Optional[str] = None
    tracks: list = field(default_factory=list)
    mood: Optional[str] = None
    error: bool = False

    def __str__(self) -> str:
        return self.text

INTENT_SYSTEM_PROMPT = """Voce e o {name}, um assistente musical integrado ao Spotify.

{profile_and_context}

Voce pode executar as seguintes acoes:
- RECOMMEND: recomendar musicas com base em pedido, humor ou contexto
- PLAY: iniciar reproducao (pode incluir busca de uma musica especifica)
- PAUSE: pausar a reproducao
- SKIP: pular para a proxima faixa
- PREVIOUS: voltar para a faixa anterior
- VOLUME_UP: aumentar o volume
- VOLUME_DOWN: diminuir o volume
- VOLUME_SET: definir volume em valor especifico (0-100)
- SHUFFLE_ON: ativar modo aleatorio
- SHUFFLE_OFF: desativar modo aleatorio
- REPEAT: definir modo de repeticao (off, track, context)
- CREATE_PLAYLIST: criar uma playlist automaticamente
- SEARCH: buscar uma musica, artista ou album sem tocar
- MOOD: registrar o humor do usuario
- CHAT: conversar, responder perguntas sobre musica, sem acao no Spotify

REGRAS:
1. Responda APENAS com um objeto JSON valido, sem texto antes ou depois.
2. Formato obrigatorio:
{{
  "intent": "UMA_DAS_ACOES_ACIMA",
  "mood": "humor detectado ou null",
  "query": "termo de busca ou pedido especifico, ou null",
  "value": valor numerico quando necessario (ex: volume), ou null,
  "response": "sua resposta em texto para o usuario em {language}"
}}
3. O campo "response" deve ser natural, descontraido e em {language}.
4. Para RECOMMEND, "query" deve conter o pedido de recomendacao completo.
5. Para PLAY com musica especifica, "query" deve conter "titulo + artista".
6. Para VOLUME_SET, "value" deve ser um numero de 0 a 100.
"""

class BluntedAI:
    def __init__(self) -> None:
        logger.info(f"[Assistant] Inicializando {settings.assistant.name}...")

        init_db()

        self._sp = get_spotify_client()
        self._player = SpotifyPlayer(client=self._sp)
        self._search = SpotifySearch(client=self._sp)
        self._playlist = SpotifyPlaylist(client=self._sp)
        self._context_builder = ContextBuilder()
        self._recommender = MusicRecommender(spotify_client=self._sp)
        self._llm = get_llm_client()
        self._current_mood: Optional[str] = None

        self._sync_profile_on_startup()

        logger.info(f"[Assistant] {settings.assistant.name} pronto! LLM: {self._llm.model_name}")

    def _sync_profile_on_startup(self) -> None:
        try:
            logger.info("[Assistant] Sincronizando perfil com o Spotify...")
            top_tracks = self._search.top_tracks(limit=20, time_range="medium_term")
            top_artists = self._search.top_artists(limit=20, time_range="medium_term")
            sync_from_spotify(top_tracks=top_tracks, top_artists=top_artists)
            compute_profile_from_history(days=30)
        except Exception as e:
            logger.warning(f"[Assistant] Sincronização do perfil falhou: {e}")

    def _analyze_intent(self, user_message: str) -> dict:
        current_track = self._player.get_current_track()
        current_track_str = str(current_track) if current_track else None
        active_device = self._player.get_active_device()
        device_name = active_device.name if active_device else None

        ctx = self._context_builder.build_full_context(
            current_mood=self._current_mood,
            current_track_str=current_track_str,
            device_name=device_name,
        )

        system_prompt = INTENT_SYSTEM_PROMPT.format(
            name=settings.assistant.name,
            language=settings.assistant.language,
            profile_and_context=ctx["system_prompt"] + "\n\n" + ctx["context_block"],
        )

        prompt = f'Mensagem do usuario: "{user_message}"'

        try:
            return self._llm.generate_json(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.4,
                max_tokens=512,
            )
        except (ValueError, RuntimeError) as e:
            logger.warning(f"[Assistant] Resposta de intencao invalida: {e}")
            return {
                "intent": "CHAT",
                "mood": None,
                "query": None,
                "value": None,
                "response": str(e),
            }

    def _execute_action(self, intent_data: dict) -> AssistantResponse:
        intent = intent_data.get("intent", "CHAT")
        query = intent_data.get("query")
        value = intent_data.get("value")
        mood = intent_data.get("mood")
        response_text = intent_data.get("response", "")

        if mood:
            self._current_mood = mood
            set_profile_value(ProfileKey.LAST_MOOD, mood)

        if intent == "CHAT":
            return AssistantResponse(text=response_text, action_taken="chat", mood=mood)

        elif intent == "MOOD":
            return AssistantResponse(text=response_text, action_taken="mood_registered", mood=mood)

        elif intent == "RECOMMEND":
            result = self._recommender.recommend(
                request=query or "músicas variadas",
                n=5,
                mood=mood,
                save_to_history=False,
            )

            if result.tracks:
                self._player.play(uris=result.uris)
                action = f"recommend_and_play:{len(result.tracks)}_tracks"
            else:
                action = "recommend_failed"
                response_text += "\n\nInfelizmente não consegui encontrar essas músicas no Spotify agora."

            return AssistantResponse(
                text=response_text,
                action_taken=action,
                tracks=result.tracks,
                mood=result.mood or mood,
            )

        elif intent == "PLAY":
            if query:
                tracks = self._search.tracks(query, limit=1)
                if tracks:
                    self._player.play(uris=[tracks[0].uri])
                    return AssistantResponse(
                        text=response_text,
                        action_taken=f"play:{tracks[0].title}",
                        tracks=tracks,
                        mood=mood,
                    )
                else:
                    return AssistantResponse(
                        text=f"Não encontrei '{query}' no Spotify. Tente outro nome.",
                        action_taken="play_not_found",
                        mood=mood,
                        error=True,
                    )
            else:
                self._player.play()
                return AssistantResponse(text=response_text, action_taken="play_resume", mood=mood)

        elif intent == "PAUSE":
            self._player.pause()
            return AssistantResponse(text=response_text, action_taken="pause", mood=mood)

        elif intent == "SKIP":
            self._player.skip()
            return AssistantResponse(text=response_text, action_taken="skip", mood=mood)

        elif intent == "PREVIOUS":
            self._player.previous()
            return AssistantResponse(text=response_text, action_taken="previous", mood=mood)

        elif intent == "VOLUME_UP":
            self._player.volume_up()
            return AssistantResponse(text=response_text, action_taken="volume_up", mood=mood)

        elif intent == "VOLUME_DOWN":
            self._player.volume_down()
            return AssistantResponse(text=response_text, action_taken="volume_down", mood=mood)

        elif intent == "VOLUME_SET":
            vol = int(value) if value is not None else 50
            self._player.set_volume(vol)
            return AssistantResponse(text=response_text, action_taken=f"volume_set:{vol}", mood=mood)

        elif intent == "SHUFFLE_ON":
            self._player.set_shuffle(True)
            return AssistantResponse(text=response_text, action_taken="shuffle_on", mood=mood)

        elif intent == "SHUFFLE_OFF":
            self._player.set_shuffle(False)
            return AssistantResponse(text=response_text, action_taken="shuffle_off", mood=mood)

        elif intent == "REPEAT":
            mode = str(query).lower() if query else "context"
            if mode not in {"off", "track", "context"}:
                mode = "context"
            self._player.set_repeat(mode)
            return AssistantResponse(text=response_text, action_taken=f"repeat:{mode}", mood=mood)

        elif intent == "CREATE_PLAYLIST":
            result = self._recommender.recommend(
                request=query or "músicas variadas",
                n=10,
                mood=mood,
                save_to_history=False,
            )

            if result.tracks:
                playlist_name = query or f"BluntedAI — {mood or 'Mix'}"
                playlist = self._playlist.create(
                    name=playlist_name,
                    description=f"Criada pelo BluntedAI | Contexto: {query}",
                    public=False,
                )
                if playlist:
                    self._playlist.add_tracks(playlist.playlist_id, result.uris)
                    action = f"playlist_created:{playlist.playlist_id}"
                else:
                    action = "playlist_creation_failed"
            else:
                action = "playlist_no_tracks"

            return AssistantResponse(
                text=response_text,
                action_taken=action,
                tracks=result.tracks,
                mood=mood,
            )

        elif intent == "SEARCH":
            tracks = self._search.tracks(query or "", limit=5)
            if tracks:
                track_list = "\n".join(
                    f"  {i}. {t.title} — {t.artists_str}"
                    for i, t in enumerate(tracks, 1)
                )
                response_text += f"\n\n{track_list}"
            return AssistantResponse(
                text=response_text,
                action_taken="search",
                tracks=tracks,
                mood=mood,
            )

        else:
            logger.warning(f"[Assistant] Intenção desconhecida: {intent}")
            return AssistantResponse(
                text=response_text or "Não entendi o que você quis dizer. Pode reformular?",
                action_taken="unknown",
                mood=mood,
            )

    def chat(self, message: str) -> AssistantResponse:
        if not message.strip():
            return AssistantResponse(text="Pode falar! O que você quer ouvir? 🎵")

        logger.info(f"[Assistant] Mensagem recebida: '{message}'")

        try:
            intent_data = self._analyze_intent(message)
            logger.info(f"[Assistant] Intenção detectada: {intent_data.get('intent')}")

            response = self._execute_action(intent_data)

            record_interaction(
                interaction_type=intent_data.get("intent", "CHAT").lower(),
                user_input=message,
                mood=response.mood,
                assistant_response=response.text,
                metadata={
                    "intent": intent_data.get("intent"),
                    "action_taken": response.action_taken,
                    "n_tracks": len(response.tracks),
                },
            )

            return response

        except Exception as e:
            logger.error(f"[Assistant] Erro ao processar mensagem: {e}", exc_info=True)
            return AssistantResponse(
                text="Ocorreu um erro interno. Tente novamente em instantes.",
                error=True,
            )

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    import io

    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if sys.stdin.encoding and sys.stdin.encoding.lower() != "utf-8":
        sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace")

    print(f"\n{'=' * 60}")
    print(f"  BluntedAI - Assistente Musical com IA")
    print(f"  Powered by Gemini + Spotify")
    print(f"{'=' * 60}")
    print("  Digite sua mensagem e pressione Enter.")
    print("  Use 'sair' ou Ctrl+C para encerrar.")
    print(f"{'=' * 60}\n")

    assistant = BluntedAI()

    print(f"\n[BluntedAI] {settings.assistant.name} esta pronto! O que voce quer ouvir?\n")

    while True:
        try:
            user_input = input("Voce: ").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n\nAte logo!")
            break

        if not user_input:
            continue

        if user_input.lower() in {"sair", "exit", "quit"}:
            print(f"\nAte logo!")
            break

        response = assistant.chat(user_input)

        print(f"\n{settings.assistant.name}: {response.text}")

        if response.tracks:
            print(f"\n  [Faixas]")
            for i, t in enumerate(response.tracks[:5], 1):
                print(f"     {i}. {t.title} - {t.artists_str}")

        if response.action_taken and response.action_taken != "chat":
            print(f"\n  [OK] Acao: {response.action_taken}")

        print()
