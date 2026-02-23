import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))

def main() -> None:
    try:
        from config import settings
    except EnvironmentError as e:
        print("\n" + "=" * 55)
        print("  ERRO DE CONFIGURACAO -- BluntedAI nao pode iniciar")
        print("=" * 55)
        print(e)
        print("Dica: copie o arquivo .env.example para .env e preencha")
        print("      as credenciais do Spotify Developer Dashboard.\n")
        sys.exit(1)

    from interface.cli import BluntedCLI
    cli = BluntedCLI()
    cli.run()

if __name__ == "__main__":
    main()
