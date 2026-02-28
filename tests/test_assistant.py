import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.append(str(Path(__file__).resolve().parent.parent))

from ai.assistant import BluntedAI, AssistantResponse


class TestAssistantIntentAnalyze:
    
    @patch("ai.assistant.get_spotify_client")
    @patch("ai.assistant.get_llm_client")
    @patch("ai.assistant.compute_profile_from_history")
    @patch("ai.assistant.sync_from_spotify")
    def test_analyze_intent_response(
        self,
        mock_sync,
        mock_compute,
        mock_llm,
        mock_spotify,
    ):
        """Testa intent ANALYZE retorna AssistantResponse correto"""
        mock_llm.return_value = MagicMock()
        mock_llm.return_value.model_name = "test-model"
        mock_llm.return_value.generate_json = MagicMock(return_value={
            "response": "Análise gerada com sucesso"
        })
        
        mock_spotify.return_value = MagicMock()
        
        assistant = BluntedAI()
        response = assistant._handle_analyze_intent(mood="happy")
        
        assert isinstance(response, AssistantResponse)
        assert response.action_taken == "analyze_profile"
        assert response.mood == "happy"
        assert response.text is not None

    @patch("ai.assistant.get_spotify_client")
    @patch("ai.assistant.get_llm_client")
    def test_analyze_intent_error_handling(self, mock_llm, mock_spotify):
        """Testa tratamento de erro em ANALYZE"""
        mock_llm.return_value = MagicMock()
        mock_llm.return_value.model_name = "test-model"
        mock_llm.return_value.generate_json = MagicMock(side_effect=Exception("LLM Error"))
        
        mock_spotify.return_value = MagicMock()
        
        assistant = BluntedAI()
        response = assistant._handle_analyze_intent()
        
        assert response.error is True
        assert response.action_taken == "analyze_failed"


class TestAssistantIntentDiscovery:
    
    @patch("ai.assistant.get_spotify_client")
    @patch("ai.assistant.get_llm_client")
    def test_discovery_intent_response(self, mock_llm, mock_spotify):
        """Testa intent DISCOVERY retorna recomendações"""
        mock_llm.return_value = MagicMock()
        mock_llm.return_value.model_name = "test-model"
        mock_llm.return_value.generate_json = MagicMock(return_value={
            "recommendations": ["Artist1", "Artist2", "Artist3"],
            "response": "Descobertas geradas!",
            "reasoning": "Baseado em seu estilo"
        })
        
        mock_spotify.return_value = MagicMock()
        mock_spotify.return_value.search = MagicMock(return_value=[])
        
        assistant = BluntedAI()
        response = assistant._handle_discovery_intent(query="indie rock", mood="creative")
        
        assert isinstance(response, AssistantResponse)
        assert response.action_taken == "discovery"
        assert response.mood == "creative"

    @patch("ai.assistant.get_spotify_client")
    @patch("ai.assistant.get_llm_client")
    def test_discovery_intent_with_search(self, mock_llm, mock_spotify):
        """Testa DISCOVERY busca tracks no Spotify"""
        mock_llm.return_value = MagicMock()
        mock_llm.return_value.model_name = "test-model"
        mock_llm.return_value.generate_json = MagicMock(return_value={
            "recommendations": ["Test Artist"],
            "response": "Discovery response"
        })
        
        mock_search = MagicMock()
        mock_search.tracks = MagicMock(return_value=[
            MagicMock(title="Test Song", uri="spotify:track:123", artists_str="Test Artist")
        ])
        
        mock_spotify.return_value = MagicMock()
        
        assistant = BluntedAI()
        response = assistant._handle_discovery_intent(query="test")
        
        assert isinstance(response, AssistantResponse)


class TestAssistantIntentActivityPlaylist:
    
    @patch("ai.assistant.get_spotify_client")
    @patch("ai.assistant.get_llm_client")
    def test_activity_playlist_intent_response(self, mock_llm, mock_spotify):
        """Testa intent ACTIVITY_PLAYLIST cria playlist"""
        mock_llm.return_value = MagicMock()
        mock_llm.return_value.model_name = "test-model"
        mock_llm.return_value.generate_json = MagicMock(return_value={
            "playlist_name": "Workout Mix",
            "response": "Playlist criada para treino!",
            "bpm_range": "130-150"
        })
        
        mock_spotify.return_value = MagicMock()
        
        assistant = BluntedAI()
        response = assistant._handle_activity_playlist_intent(query="workout", mood="energetic")
        
        assert isinstance(response, AssistantResponse)
        assert response.mood == "energetic"

    @patch("ai.assistant.get_spotify_client")
    @patch("ai.assistant.get_llm_client")
    def test_activity_playlist_intent_error(self, mock_llm, mock_spotify):
        """Testa tratamento de erro em ACTIVITY_PLAYLIST"""
        mock_llm.return_value = MagicMock()
        mock_llm.return_value.model_name = "test-model"
        mock_llm.return_value.generate_json = MagicMock(side_effect=Exception("LLM Error"))
        
        mock_spotify.return_value = MagicMock()
        
        assistant = BluntedAI()
        response = assistant._handle_activity_playlist_intent(query="workout")
        
        assert response.error is True
        assert response.action_taken == "activity_playlist_failed"


class TestAssistantFormatters:
    
    @patch("ai.assistant.get_spotify_client")
    @patch("ai.assistant.get_llm_client")
    def test_format_list(self, mock_llm, mock_spotify):
        """Testa formatação de lista"""
        mock_llm.return_value = MagicMock()
        mock_llm.return_value.model_name = "test-model"
        mock_spotify.return_value = MagicMock()
        
        assistant = BluntedAI()
        
        items = ["Item 1", "Item 2", "Item 3"]
        result = assistant._format_list(items, max_items=2)
        
        assert "Item 1" in result
        assert "Item 2" in result
        assert "Item 3" not in result

    @patch("ai.assistant.get_spotify_client")
    @patch("ai.assistant.get_llm_client")
    def test_format_dict(self, mock_llm, mock_spotify):
        """Testa formatação de dicionário"""
        mock_llm.return_value = MagicMock()
        mock_llm.return_value.model_name = "test-model"
        mock_spotify.return_value = MagicMock()
        
        assistant = BluntedAI()
        
        data = {"key1": "value1", "key2": "value2"}
        result = assistant._format_dict(data, max_items=1)
        
        assert "key1" in result
        assert "value1" in result


class TestAssistantIntegration:
    
    @patch("ai.assistant.get_spotify_client")
    @patch("ai.assistant.get_llm_client")
    def test_chat_dispatches_analyze_intent(self, mock_llm, mock_spotify):
        """Testa se chat identifica intent ANALYZE"""
        mock_llm.return_value = MagicMock()
        mock_llm.return_value.model_name = "test-model"
        
        # Primeira chamada: identifica intent
        # Segunda chamada: gera insights
        mock_llm.return_value.generate_json = MagicMock(side_effect=[
            {
                "intent": "ANALYZE",
                "mood": None,
                "query": None,
                "value": None,
                "response": "Analisando..."
            },
            {
                "headline_insight": "Análise",
                "response": "Insights gerados"
            }
        ])
        
        mock_spotify.return_value = MagicMock()
        
        assistant = BluntedAI()
        response = assistant.chat("Analisa meu perfil")
        
        assert isinstance(response, AssistantResponse)
        assert response.action_taken == "analyze_profile"

    @patch("ai.assistant.get_spotify_client")
    @patch("ai.assistant.get_llm_client")
    def test_chat_unknown_intent(self, mock_llm, mock_spotify):
        """Testa resposta para intent desconhecido"""
        mock_llm.return_value = MagicMock()
        mock_llm.return_value.model_name = "test-model"
        mock_llm.return_value.generate_json = MagicMock(return_value={
            "intent": "UNKNOWN_ACTION",
            "mood": None,
            "query": None,
            "value": None,
            "response": "Não entendi"
        })
        
        mock_spotify.return_value = MagicMock()
        
        assistant = BluntedAI()
        response = assistant.chat("faça algo aleatório")
        
        assert response.action_taken == "unknown"
        assert response.error is False
