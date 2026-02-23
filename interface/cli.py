import sys
import logging
import time
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.rule import Rule
from rich.prompt import Prompt
from rich import box
from config import settings
from ai.assistant import BluntedAI, AssistantResponse
from spotify.player import TrackInfo, DeviceInfo
sys.path.append(str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.WARNING)
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("groq").setLevel(logging.ERROR)
logging.getLogger("spotipy").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("googleapiclient").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

console = Console()

class Colors:
    PRIMARY    = "green"
    SECONDARY  = "cyan"
    ACCENT     = "magenta"
    DIM        = "grey50"
    WARNING    = "yellow"
    ERROR      = "red"
    TRACK      = "bright_white"
    ARTIST     = "cyan"
    PLAYING    = "green"
    PAUSED     = "yellow"

def render_header() -> Panel:
    title = Text()
    title.append("  B", style="bold bright_green")
    title.append("lun", style="bold green")
    title.append("ted", style="bold cyan")
    title.append("AI  ", style="bold bright_cyan")

    subtitle = Text(
        f"Assistente Musical com IA  |  Powered by {settings.llm.provider.capitalize()} + Spotify",
        style=Colors.DIM,
    )

    content = Text()
    content.append_text(title)
    content.append("\n")
    content.append_text(subtitle)

    return Panel(content, box=box.DOUBLE, border_style=Colors.PRIMARY, padding=(0, 2))

def render_now_playing(track: Optional[TrackInfo], device: Optional[DeviceInfo]) -> Panel:
    if not track:
        return Panel(
            Text("  Nenhuma faixa em reproducao", style=Colors.DIM),
            title="[grey50] Tocando Agora [/grey50]",
            border_style=Colors.DIM,
            box=box.ROUNDED,
            padding=(0, 1),
        )

    status_icon = "[green]>[/green]" if track.is_playing else "[yellow]||[/yellow]"
    status_label = "Tocando" if track.is_playing else "Pausado"
    border_color = Colors.PLAYING if track.is_playing else Colors.PAUSED

    total_s = track.duration_ms // 1000
    progress_s = track.progress_ms // 1000
    bar_width = 30
    filled = int((progress_s / total_s) * bar_width) if total_s > 0 else 0
    bar = "[green]" + "=" * filled + "[/green]" + "[grey30]" + "-" * (bar_width - filled) + "[/grey30]"

    content = Text()
    content.append(f"  {track.title}\n", style="bold bright_white")
    content.append(f"  {track.artists_str}\n", style=Colors.ARTIST)
    content.append(f"  {track.album}\n", style=Colors.DIM)
    content.append(f"\n  {track.progress_str}  ", style=Colors.DIM)
    content.append_text(Text.from_markup(bar))
    content.append(f"  {track.duration_str}\n", style=Colors.DIM)

    if device:
        content.append(
            f"\n  [{device.device_type}] {device.name}  |  Vol: {device.volume_percent}%",
            style=Colors.DIM,
        )

    return Panel(
        content,
        title=f"[{border_color}] {status_icon} {status_label} [/{border_color}]",
        border_style=border_color,
        box=box.ROUNDED,
        padding=(0, 1),
    )

def render_track_table(tracks: list, title: str = "Faixas Recomendadas") -> Table:
    table = Table(
        box=box.SIMPLE_HEAVY,
        border_style=Colors.DIM,
        header_style=f"bold {Colors.SECONDARY}",
        show_edge=True,
        padding=(0, 1),
        title=f"[bold {Colors.PRIMARY}]{title}[/bold {Colors.PRIMARY}]",
        title_justify="left",
    )

    table.add_column("#", style=Colors.DIM, width=3, justify="right")
    table.add_column("Musica", style=Colors.TRACK, min_width=25)
    table.add_column("Artista", style=Colors.ARTIST, min_width=20)
    table.add_column("Album", style=Colors.DIM, min_width=20)
    table.add_column("Dur.", style=Colors.DIM, width=7, justify="right")

    for i, track in enumerate(tracks, 1):
        table.add_row(
            str(i),
            track.title[:40] + ("..." if len(track.title) > 40 else ""),
            track.artists_str[:30] + ("..." if len(track.artists_str) > 30 else ""),
            track.album[:25] + ("..." if len(track.album) > 25 else ""),
            track.duration_str,
        )

    return table

def render_message_user(text: str) -> None:
    label = Text("  Voce  ", style=f"bold {Colors.SECONDARY}")
    msg = Text(f" {text}", style="bright_white")
    console.print()
    console.print(label, end="")
    console.print(msg)

def render_message_assistant(text: str, action: Optional[str] = None) -> None:
    label = Text(f"  {settings.assistant.name}  ", style=f"bold {Colors.PRIMARY}")
    console.print()
    console.print(label)

    for line in text.split("\n"):
        console.print(f"    {line}", style="white")

    if action and action not in {"chat", "mood_registered"}:
        console.print(f"    [grey50][ {action} ][/grey50]")

def render_error(text: str) -> None:
    console.print(Panel(Text(text, style=Colors.ERROR), border_style=Colors.ERROR, box=box.ROUNDED))

def render_help() -> None:
    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    table.add_column("Categoria", style=f"bold {Colors.SECONDARY}", width=18)
    table.add_column("Exemplos", style="white")

    table.add_row("Recomendacao",  "toca algo para relaxar | musicas para academia | jazz dos anos 60")
    table.add_row("Player",        "pausa | continua | proxima | anterior")
    table.add_row("Volume",        "aumenta o volume | volume 50 | muta")
    table.add_row("Shuffle",       "ativa shuffle | desativa modo aleatório")
    table.add_row("Playlist",      "cria uma playlist de rock anos 90")
    table.add_row("Busca",         "busca: Bohemian Rhapsody Queen")
    table.add_row("Humor",         "estou feliz hoje | to com vontade de chorar")
    table.add_row("Sair",          "sair | exit | quit")

    console.print(Panel(
        table,
        title=f"[bold {Colors.PRIMARY}] Comandos disponiveis [/bold {Colors.PRIMARY}]",
        border_style=Colors.DIM,
        box=box.ROUNDED,
    ))

def render_status_bar(track: Optional[TrackInfo]) -> Text:
    status = Text()
    if track:
        icon = ">" if track.is_playing else "||"
        status.append(f" {icon} ", style=Colors.PLAYING if track.is_playing else Colors.PAUSED)
        status.append(f"{track.title} - {track.artists_str}", style=Colors.DIM)
    else:
        status.append(" -- sem reproducao", style=Colors.DIM)
    return status

class BluntedCLI:

    def __init__(self) -> None:
        self._assistant: Optional[BluntedAI] = None

    def _boot(self) -> bool:
        console.print()
        console.print(render_header())
        console.print()

        try:
            with console.status(
                f"[{Colors.PRIMARY}] Inicializando {settings.assistant.name}...",
                spinner="dots",
            ):
                self._assistant = BluntedAI()
            console.print(f"  [{Colors.PRIMARY}]OK[/{Colors.PRIMARY}]  Assistente pronto!\n")
            return True
        except EnvironmentError as e:
            render_error(str(e))
            return False
        except Exception as e:
            render_error(f"Erro ao inicializar: {e}")
            return False

    def _refresh_player_panel(self) -> tuple[Optional[TrackInfo], Optional[DeviceInfo]]:
        try:
            track = self._assistant._player.get_current_track()
            device = self._assistant._player.get_active_device()
            return track, device
        except Exception:
            return None, None

    def _process_input(self, user_input: str) -> None:
        render_message_user(user_input)

        response: Optional[AssistantResponse] = None
        with console.status(
            f"[{Colors.DIM}] {settings.assistant.name} pensando...",
            spinner="dots2",
        ):
            response = self._assistant.chat(user_input)

        render_message_assistant(response.text, response.action_taken)

        if response.tracks:
            console.print()
            console.print(render_track_table(response.tracks))

        PLAYBACK_ACTIONS = {"play_resume", "skip", "previous", "shuffle_on", "shuffle_off"}
        if (
            response.action_taken
            and (
                response.action_taken.startswith("play:")
                or response.action_taken.startswith("recommend_and_play")
                or response.action_taken in PLAYBACK_ACTIONS
            )
        ):
            time.sleep(0.8)
            track, device = self._refresh_player_panel()
            console.print()
            console.print(render_now_playing(track, device))

        if response.error:
            console.print(
                f"\n  [{Colors.WARNING}] Dica: verifique se o Spotify esta aberto em algum dispositivo.[/{Colors.WARNING}]"
            )

    def run(self) -> None:
        if not self._boot():
            sys.exit(1)

        track, device = self._refresh_player_panel()
        console.print(render_now_playing(track, device))
        console.print()

        render_help()
        console.print()

        console.print(Rule(style=Colors.DIM))
        console.print()

        while True:
            try:
                user_input = Prompt.ask(
                    f"[bold {Colors.SECONDARY}]  Voce[/bold {Colors.SECONDARY}]",
                    console=console,
                ).strip()
            except (KeyboardInterrupt, EOFError):
                console.print(f"\n\n  [{Colors.PRIMARY}] Ate logo! [/{Colors.PRIMARY}]\n")
                break

            if not user_input:
                continue

            if user_input.lower() in {"sair", "exit", "quit", "q"}:
                console.print(f"\n  [{Colors.PRIMARY}] Ate logo! [/{Colors.PRIMARY}]\n")
                break

            if user_input.lower() in {"status", "agora", "now"}:
                track, device = self._refresh_player_panel()
                console.print()
                console.print(render_now_playing(track, device))
                console.print()
                continue

            if user_input.lower() in {"ajuda", "help", "?"}:
                console.print()
                render_help()
                console.print()
                continue

            try:
                self._process_input(user_input)
            except KeyboardInterrupt:
                console.print(f"\n  [{Colors.WARNING}] Interrompido.[/{Colors.WARNING}]")

            console.print()
            console.print(Rule(style=Colors.DIM))
            console.print()

if __name__ == "__main__":
    cli = BluntedCLI()
    cli.run()
