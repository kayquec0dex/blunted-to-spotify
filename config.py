import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def _require(var: str) -> str:
    value = os.getenv(var)
    if not value:
        raise EnvironmentError(
            f"\n[BluntedAI] Variavel de ambiente obrigatoria nao encontrada: '{var}'\n"
            f"  -> Copie o arquivo .env.example para .env e preencha as credenciais.\n"
        )
    return value

def _optional(var: str, default: str = "") -> str:
    return os.getenv(var, default)

@dataclass(frozen=True)
class SpotifyConfig:
    client_id: str
    client_secret: str
    redirect_uri: str

    # Referencia completa de escopos: https://developer.spotify.com/documentation/general/guides/authorization/scopes/
    scopes: str = field(default=" ".join([
        "user-read-private",
        "user-read-email",
        "user-library-read",
        "user-library-modify",
        "user-read-recently-played",
        "user-top-read",
        "user-read-playback-state",
        "user-modify-playback-state",
        "user-read-currently-playing",
        "playlist-read-private",
        "playlist-read-collaborative",
        "playlist-modify-public",
        "playlist-modify-private",
    ]))

    cache_path: str = field(default=".spotify_cache")

@dataclass(frozen=True)
class LLMConfig:
    provider: str
    gemini_api_key: str
    groq_api_key: str
    # Opcoes Gemini: gemini-2.0-flash-lite, gemini-2.0-flash, gemini-1.5-pro
    gemini_model: str
    # Opcoes Groq: llama-3.3-70b-versatile, llama-3.1-8b-instant, mixtral-8x7b-32768
    groq_model: str
    ollama_base_url: str
    ollama_model: str

@dataclass(frozen=True)
class DatabaseConfig:
    path: str

    @property
    def resolved_path(self) -> Path:
        p = Path(self.path)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p.resolve()

@dataclass(frozen=True)
class AssistantConfig:
    name: str
    language: str

@dataclass(frozen=True)
class Settings:
    spotify: SpotifyConfig
    llm: LLMConfig
    database: DatabaseConfig
    assistant: AssistantConfig

def _load_settings() -> Settings:
    spotify = SpotifyConfig(
        client_id=_require("SPOTIFY_CLIENT_ID"),
        client_secret=_require("SPOTIFY_CLIENT_SECRET"),
        redirect_uri=_optional("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback"),
    )

    llm = LLMConfig(
        provider=_optional("LLM_PROVIDER", "groq"),
        gemini_api_key=_optional("GEMINI_API_KEY"),
        gemini_model=_optional("GEMINI_MODEL", "gemini-2.0-flash-lite"),
        groq_api_key=_optional("GROQ_API_KEY"),
        groq_model=_optional("GROQ_MODEL", "llama-3.3-70b-versatile"),
        ollama_base_url=_optional("OLLAMA_BASE_URL", "http://localhost:11434"),
        ollama_model=_optional("OLLAMA_MODEL", "llama3"),
    )

    database = DatabaseConfig(
        path=_optional("DATABASE_PATH", "./memory/bluntedai.db"),
    )

    assistant = AssistantConfig(
        name=_optional("ASSISTANT_NAME", "BluntedAI"),
        language=_optional("ASSISTANT_LANGUAGE", "pt-BR"),
    )

    return Settings(spotify=spotify, llm=llm, database=database, assistant=assistant)

settings = _load_settings()

if __name__ == "__main__":
    print(f"\n{'=' * 50}")
    print(f"  {settings.assistant.name} -- Diagnostico de Configuracoes")
    print(f"{'=' * 50}")

    print(f"\n[Spotify]")
    print(f"  Client ID     : {settings.spotify.client_id[:8]}...")
    print(f"  Client Secret : {settings.spotify.client_secret[:4]}****")
    print(f"  Redirect URI  : {settings.spotify.redirect_uri}")

    print(f"\n[LLM]")
    print(f"  Provedor : {settings.llm.provider}")
    if settings.llm.provider == "gemini":
        key = settings.llm.gemini_api_key
        print(f"  API Key  : {key[:6]}..." if key else "  API Key  : NAO DEFINIDA")
        print(f"  Modelo   : {settings.llm.gemini_model}")
    elif settings.llm.provider == "groq":
        key = settings.llm.groq_api_key
        print(f"  API Key  : {key[:6]}..." if key else "  API Key  : NAO DEFINIDA")
        print(f"  Modelo   : {settings.llm.groq_model}")
    elif settings.llm.provider == "ollama":
        print(f"  URL      : {settings.llm.ollama_base_url}")
        print(f"  Modelo   : {settings.llm.ollama_model}")

    print(f"\n[Banco de Dados]")
    print(f"  Caminho  : {settings.database.resolved_path}")

    print(f"\n[Assistente]")
    print(f"  Nome     : {settings.assistant.name}")
    print(f"  Idioma   : {settings.assistant.language}")

    print(f"\n{'=' * 50}\n")
