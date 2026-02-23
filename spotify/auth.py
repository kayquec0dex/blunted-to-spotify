import sys
import logging
from pathlib import Path
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.exceptions import SpotifyException
sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import settings

logger = logging.getLogger(__name__)

def create_oauth_manager() -> SpotifyOAuth:
    return SpotifyOAuth(
        client_id=settings.spotify.client_id,
        client_secret=settings.spotify.client_secret,
        redirect_uri=settings.spotify.redirect_uri,
        scope=settings.spotify.scopes,
        cache_path=settings.spotify.cache_path,
        open_browser=True,
        show_dialog=False,
    )

def get_spotify_client() -> spotipy.Spotify:
    logger.info("Iniciando autenticacao com o Spotify...")

    try:
        oauth_manager = create_oauth_manager()
        token_info = oauth_manager.get_cached_token()

        if token_info:
            logger.info("Token cacheado encontrado. Nenhum login necessario.")
        else:
            logger.info("Nenhum token em cache. Iniciando fluxo de autorizacao...")
            token_info = oauth_manager.get_access_token(as_dict=True)

        if not token_info:
            raise SpotifyException(
                http_status=401,
                code=-1,
                msg="Nao foi possivel obter o token de acesso do Spotify."
            )

        client = spotipy.Spotify(auth_manager=oauth_manager)
        user = client.current_user()
        display_name = user.get("display_name") or user.get("id", "Usuario")
        logger.info(f"Autenticado com sucesso! Ola, {display_name}")

        return client

    except SpotifyException as e:
        logger.error(f"Erro na autenticacao com o Spotify: {e}")
        sys.exit(1)

    except KeyboardInterrupt:
        logger.warning("Autenticacao cancelada pelo usuario.")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Erro inesperado durante a autenticacao: {e}", exc_info=True)
        sys.exit(1)

def is_token_valid() -> bool:
    try:
        oauth_manager = create_oauth_manager()
        token_info = oauth_manager.get_cached_token()
        return token_info is not None
    except Exception:
        return False

def revoke_token() -> None:
    cache_path = Path(settings.spotify.cache_path)
    if cache_path.exists():
        cache_path.unlink()
        logger.info(f"Token removido. Arquivo: {cache_path}")
    else:
        logger.warning("Nenhum token cacheado encontrado.")

def get_token_info() -> dict | None:
    try:
        oauth_manager = create_oauth_manager()
        return oauth_manager.get_cached_token()
    except Exception as e:
        logger.warning(f"Nao foi possivel ler o token cacheado: {e}")
        return None

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    token = get_token_info()
    if token:
        import time
        expires_at = token.get("expires_at", 0)
        remaining = max(0, int(expires_at - time.time()))
        minutes, seconds = divmod(remaining, 60)
        print(f"Token: {'Valido' if remaining > 0 else 'Expirado'} | Expira em: {minutes}m {seconds}s")
    else:
        print("Nenhum token em cache. Iniciando login...")

    sp = get_spotify_client()
    user = sp.current_user()
    print(f"\nID      : {user['id']}")
    print(f"Nome    : {user.get('display_name', 'N/A')}")
    print(f"Pais    : {user.get('country', 'N/A')}")
    print(f"Plano   : {user.get('product', 'N/A')}")
