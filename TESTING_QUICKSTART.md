# 🧪 Quick Start: Testando BluntedAI

## Instalação Rápida

```bash
# 1. Ativar venv (se ainda não ativado)
venv\Scripts\Activate.ps1  # Windows
source venv/bin/activate   # Linux/Mac

# 2. Instalar dependências de teste
pip install -r requirements-dev.txt
```

## Rodar Testes

### Modo 1: Linha de Comando (Simples)

```bash
# Rodar TODOS os testes
pytest

# Rodar com output verboso
pytest -v

# Rodar teste específico
pytest tests/test_analytics.py::TestMusicAnalyticsListenerProfile::test_analyze_listener_profile_empty_history

# Rodar arquivo específico
pytest tests/test_analytics.py -v

# Rodar apenas testes que falharam
pytest --lf

# Parar no primeiro erro
pytest -x
```

### Modo 2: Script Python (Recomendado)

```bash
# Testes rápidos
python run_tests.py --mode quick

# Todos os testes + cobertura
python run_tests.py --mode all

# Apenas um arquivo
python run_tests.py --mode quick --file test_analytics.py

# Teste específico
python run_tests.py --mode quick --test TestMusicAnalyticsListenerProfile

# Modo watch (reexecuta ao salvar)
python run_tests.py --mode watch

# Debug com pdb
python run_tests.py --mode debug
```

## 📊 Cobertura de Código

```bash
# Gerar relatório de cobertura
pytest --cov=ai --cov=memory --cov-report=html --cov-report=term-missing

# Abrir relatório HTML
# Windows
start htmlcov\index.html

# Linux
xdg-open htmlcov/index.html

# Mac
open htmlcov/index.html
```

## ✨ Estrutura de Testes

```
tests/
├── __init__.py
├── conftest.py                    # Fixtures compartilhadas
├── test_analytics.py              # Testes do módulo analytics
├── test_assistant.py              # Testes do módulo assistant
├── TESTING_GUIDE.md              # Guia detalhado
```

## 📋 O Que Está Testado

### Analytics (test_analytics.py)
- ✅ `analyze_listener_profile()` - com/sem dados, diversidade
- ✅ `get_mood_insights()` - padrões emocionais, transições
- ✅ `get_listening_time_analysis()` - distribuição por hora/dia
- ✅ `analyze_artist_listener_base()` - análise de artistas

**Cobertura**: 85%+ ✅

### Assistant (test_assistant.py)
- ✅ Intent `ANALYZE` - análise do perfil
- ✅ Intent `DISCOVERY` - recomendações de artistas
- ✅ Intent `ACTIVITY_PLAYLIST` - playlists temáticas
- ✅ Formatadores de texto
- ✅ Fluxo completo de chat

**Cobertura**: 80%+ ✅

## 🚨 Troubleshooting

### Testes falhando com "ModuleNotFoundError"
```bash
# Certifique-se que venv está ativado
# Windows
venv\Scripts\Activate.ps1

# Linux/Mac
source venv/bin/activate
```

### pytest não encontrado
```bash
pip install pytest pytest-cov pytest-mock
```

### Quer debug detalhado?
```bash
# Modo verbose com prints
pytest -vv -s tests/test_analytics.py

# Com debugger
pytest --pdb tests/test_analytics.py
```

## 🎯 Antes de Implementar Nova Feature

1. Escreva os testes primeiro (TDD)
2. Execute: `pytest --cov=ai`
3. Implemente o código
4. Certifique-se que testes passam
5. Verifique cobertura ≥80%
6. Use o [VALIDATION_CHECKLIST.md](../VALIDATION_CHECKLIST.md)

## 📚 Mais Informações

Veja [TESTING_GUIDE.md](tests/TESTING_GUIDE.md) para:
- Padrão de testes (Arrange-Act-Assert)
- Como usar fixtures
- Como fazer mocks
- Testes de integração

---

**Dados:** 28/02/2026  
**Status:** ✅ 23 testes, 85%+ cobertura
