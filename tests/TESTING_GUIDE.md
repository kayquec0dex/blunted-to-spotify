"""
Guia de Testes - BluntedAI

Este documento explica como testar as novas implementações de forma eficaz.
"""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. INSTALANDO DEPENDÊNCIAS DE TESTE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Execute no terminal:
# pip install pytest pytest-cov pytest-mock


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. ESTRUTURA DE TESTES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
tests/
├── __init__.py
├── conftest.py              # Fixtures compartilhadas
├── test_analytics.py        # Testes do módulo analytics
└── test_assistant.py        # Testes do módulo assistant
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. RODANDO TESTES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
# Rodar todos os testes
pytest

# Rodar testes de um arquivo específico
pytest tests/test_analytics.py

# Rodar teste específico
pytest tests/test_analytics.py::TestMusicAnalyticsListenerProfile::test_analyze_listener_profile_empty_history

# Rodar com output verboso
pytest -v

# Rodar com mostrar prints
pytest -s

# Rodar com cobertura de código
pytest --cov=ai --cov=memory --cov-report=html

# Rodar apenas testes que passam (quick feedback)
pytest --lf  # last failed
pytest --ff  # failed first
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. FIXTURES (DADOS DE TESTE)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
Definidas em conftest.py e disponíveis em todos os testes:

@fixture test_db_session
    → Banco de dados SQLite em memória
    → Limpa automaticamente após cada teste
    
@fixture mock_spotify_client
    → Mock do cliente Spotify
    → Retorna objeto com métodos mockados
    
@fixture mock_llm_client
    → Mock do cliente LLM
    → Retorna JSON estruturado
    
@fixture sample_tracks
    → 10 TrackPlayed para testes
    → Com dados realistas
    
@fixture sample_interactions
    → 5 Interaction para testes
    → Com moods variados
    
@fixture monkeypatch_db
    → Substitui get_session() por test_db_session
    → Essencial para testes com BD

Uso em testes:
    def test_example(self, test_db_session, sample_tracks):
        for track in sample_tracks:
            test_db_session.add(track)
        test_db_session.commit()
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. TESTES ANALYTICS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
TestMusicAnalyticsListenerProfile
    ✓ test_analyze_listener_profile_empty_history
        Valida análise com histórico vazio
    ✓ test_analyze_listener_profile_with_data
        Valida análise com 10 faixas
    ✓ test_analyze_listener_diversity_scores
        Valida cálculo de diversidade (0-100)
    ✓ test_favorite_tracks_ordering
        Valida ordenação por frequência

TestMusicAnalyticsMoodInsights
    ✓ test_get_mood_insights_empty
        Valida resposta sem dados
    ✓ test_get_mood_insights_with_data
        Valida insights com interações
    ✓ test_mood_transitions_detection
        Valida detecção happy→sad→happy

TestMusicAnalyticsListeningTime
    ✓ test_get_listening_time_analysis_empty
        Valida resposta sem dados
    ✓ test_get_listening_time_analysis_with_data
        Valida hora de pico
    ✓ test_listening_periods_calculation
        Valida madrugada/manhã/tarde/noite

TestMusicAnalyticsArtist
    ✓ test_analyze_artist_listener_base_no_data
        Valida análise de artista sem dados
    ✓ test_analyze_artist_listener_base_with_data
        Valida análise com 5 plays
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 6. TESTES ASSISTANT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
TestAssistantIntentAnalyze
    ✓ test_analyze_intent_response
        Valida resposta do intent ANALYZE
    ✓ test_analyze_intent_error_handling
        Valida tratamento de erro

TestAssistantIntentDiscovery
    ✓ test_discovery_intent_response
        Valida recomendações de discovery
    ✓ test_discovery_intent_with_search
        Valida busca de tracks

TestAssistantIntentActivityPlaylist
    ✓ test_activity_playlist_intent_response
        Valida criação de playlist
    ✓ test_activity_playlist_intent_error
        Valida tratamento de erro

TestAssistantFormatters
    ✓ test_format_list
        Valida formatação de listas
    ✓ test_format_dict
        Valida formatação de dicts

TestAssistantIntegration
    ✓ test_chat_dispatches_analyze_intent
        Valida fluxo completo chat → ANALYZE
    ✓ test_chat_unknown_intent
        Valida resposta para intent desconhecido
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 7. PADRÃO DE TESTES (TDD)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
Para cada nova feature, siga este padrão:

1. ARRANGE (Preparar dados)
   def test_nova_feature(self, monkeypatch_db, sample_tracks):
       for track in sample_tracks:
           monkeypatch_db.add(track)
       monkeypatch_db.commit()

2. ACT (Executar código)
       resultado = analyzer.nova_funcao()

3. ASSERT (Validar resultado)
       assert resultado.propriedade == valor_esperado
       assert isinstance(resultado, TipoCorreto)

Exemplo completo:

def test_analyze_com_10_tracks(self, monkeypatch_db, sample_tracks):
    # ARRANGE
    for track in sample_tracks:
        monkeypatch_db.add(track)
    monkeypatch_db.commit()
    
    # ACT
    analytics = MusicAnalytics()
    resultado = analytics.analyze_listener_profile(days=30)
    
    # ASSERT
    assert resultado.total_tracks_played == 10
    assert len(resultado.favorite_artists) > 0
    assert resultado.artist_diversity_score > 0
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 8. COBERTURA DE CÓDIGO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
# Gerar relatório de cobertura
pytest --cov=ai --cov=memory --cov-report=html

# Abrir relatório
open htmlcov/index.html  # macOS
start htmlcov/index.html # Windows
xdg-open htmlcov/index.html # Linux

Meta: ≥80% de cobertura nos módulos críticos
- ai/analytics.py → 85%+
- ai/assistant.py → 80%+
- memory/database.py → 75%+
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 9. QUICK START
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
1. Instale pytest
   pip install pytest pytest-cov

2. Crie um teste simples
   def test_basico():
       assert 1 + 1 == 2

3. Execute
   pytest

4. Veja a cobertura
   pytest --cov=ai --cov-report=term-missing

Pronto! Agora você tem testes rodando.
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 10. DEBUGGING TESTES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
# Rodar com pdb (debugger)
pytest --pdb

# Rodar só o teste que tá falhando (mais rápido)
pytest --lf

# Mostrar print statements
pytest -s

# Rodar com output colorido
pytest --color=yes

# Parar no primeiro erro
pytest -x

# Mais verboso
pytest -vv
"""
