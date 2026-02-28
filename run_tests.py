#!/usr/bin/env python
"""
Script para rodar testes com diferentes configurações e gerar relatórios.
"""

import subprocess
import sys
from pathlib import Path
import argparse


def run_command(cmd, description=""):
    """Executa comando e mostra output"""
    print(f"\n{'='*60}")
    print(f"  {description}")
    print(f"{'='*60}\n")
    result = subprocess.run(cmd, shell=True)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Executar testes do BluntedAI")
    parser.add_argument(
        "--mode",
        choices=["all", "quick", "coverage", "watch", "debug"],
        default="quick",
        help="Modo de execução"
    )
    parser.add_argument(
        "--file",
        help="Arquivo de teste específico (ex: test_analytics.py)"
    )
    parser.add_argument(
        "--test",
        help="Teste específico (ex: TestMusicAnalyticsListenerProfile::test_analyze_listener_profile_empty_history)"
    )
    
    args = parser.parse_args()
    
    if args.mode == "all":
        # Todos os testes com cobertura
        success = run_command(
            "pytest -v --cov=ai --cov=memory --cov-report=term-missing --cov-report=html",
            "Rodando TODOS os testes com cobertura"
        )
        if success:
            print("\n✅ Cobertura HTML gerada em: htmlcov/index.html")
    
    elif args.mode == "quick":
        # Apenas testes rápidos
        if args.file:
            cmd = f"pytest tests/{args.file} -v"
        elif args.test:
            cmd = f"pytest tests/ -k {args.test} -v"
        else:
            cmd = "pytest tests/ -v --tb=short"
        
        run_command(cmd, "Rodando testes (modo rápido)")
    
    elif args.mode == "coverage":
        # Cobertura detalhada
        success = run_command(
            "pytest --cov=ai --cov=memory --cov-report=html --cov-report=term-missing -v",
            "Gerando relatório de cobertura"
        )
        if success:
            print("\n📊 Abra: htmlcov/index.html")
    
    elif args.mode == "watch":
        # Reexecuta testes ao mudar arquivo
        run_command(
            "pytest-watch tests/ -- -v",
            "Modo watch (reexecuta ao salvar)"
        )
    
    elif args.mode == "debug":
        # Modo debug com pdb
        if args.file:
            cmd = f"pytest tests/{args.file} --pdb -s"
        else:
            cmd = "pytest tests/ --pdb -s"
        
        run_command(cmd, "Modo debug (com breakpoints)")


if __name__ == "__main__":
    main()
