import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.append(str(Path(__file__).resolve().parent.parent))

from ai.analytics import MusicAnalytics, ListenerAnalytics
from memory.database import TrackPlayed, Interaction


class TestMusicAnalyticsListenerProfile:
    
    def test_analyze_listener_profile_empty_history(self, monkeypatch_db, test_db_session):
        """Testa análise quando não há histórico"""
        analytics = MusicAnalytics()
        result = analytics.analyze_listener_profile(days=30)
        
        assert isinstance(result, ListenerAnalytics)
        assert result.total_tracks_played == 0
        assert result.total_listening_hours == 0
        assert result.favorite_artists == []
        assert result.artist_diversity_score == 0

    def test_analyze_listener_profile_with_data(self, monkeypatch_db, test_db_session, sample_tracks):
        """Testa análise com dados históricos"""
        for track in sample_tracks:
            test_db_session.add(track)
        test_db_session.commit()
        
        analytics = MusicAnalytics()
        result = analytics.analyze_listener_profile(days=30)
        
        assert result.total_tracks_played == 10
        assert result.total_listening_hours > 0
        assert len(result.favorite_genres) > 0
        assert "Artist A" in result.favorite_artists or "Artist B" in result.favorite_artists
        assert result.peak_listening_hour == 14
        assert result.skip_rate >= 0

    def test_analyze_listener_diversity_scores(self, monkeypatch_db, test_db_session, sample_tracks):
        """Testa cálculo de scores de diversidade"""
        for track in sample_tracks:
            test_db_session.add(track)
        test_db_session.commit()
        
        analytics = MusicAnalytics()
        result = analytics.analyze_listener_profile(days=30)
        
        assert 0 <= result.artist_diversity_score <= 100
        assert 0 <= result.genre_diversity_score <= 100

    def test_favorite_tracks_ordering(self, monkeypatch_db, test_db_session):
        """Testa se tracks favoritas estão ordenadas por frequência"""
        now = datetime.now(timezone.utc)
        
        # Cria tracks com diferentes frequências
        for i in range(5):
            for _ in range(5 - i):  # Track 0 tocada 5x, track 1 tocada 4x, etc
                test_db_session.add(TrackPlayed(
                    track_id=f"track_{i}",
                    track_uri=f"spotify:track:track_{i}",
                    title=f"Popular Song {i}",
                    artists='["Artist"]',
                    album=f"Album {i}",
                    duration_ms=240000,
                    played_at=now,
                    hour_of_day=14,
                    day_of_week=2,
                ))
        test_db_session.commit()
        
        analytics = MusicAnalytics()
        result = analytics.analyze_listener_profile(days=30)
        
        assert len(result.favorite_tracks) > 0
        assert result.favorite_tracks[0]["plays"] >= result.favorite_tracks[-1]["plays"]


class TestMusicAnalyticsMoodInsights:
    
    def test_get_mood_insights_empty(self, monkeypatch_db, test_db_session):
        """Testa insights de mood sem dados"""
        analytics = MusicAnalytics()
        result = analytics.get_mood_insights(days=30)
        
        assert result["status"] == "sem_dados"

    def test_get_mood_insights_with_data(self, monkeypatch_db, test_db_session, sample_interactions):
        """Testa insights de mood com dados"""
        analytics = MusicAnalytics()
        result = analytics.get_mood_insights(days=30)
        
        assert result["status"] == "sucesso"
        assert "mood_counts" in result
        assert "most_common_mood" in result
        assert "mood_transitions" in result
        assert "timeline" in result
        assert len(result["timeline"]) > 0

    def test_mood_transitions_detection(self, monkeypatch_db, test_db_session):
        """Testa detecção de transições de mood"""
        now = datetime.now(timezone.utc)
        moods = ["happy", "sad", "happy", "excited", "sad"]
        
        for i, mood in enumerate(moods):
            test_db_session.add(Interaction(
                interaction_type="mood",
                mood=mood,
                created_at=now - timedelta(hours=5-i),
                hour_of_day=14,
                day_of_week=2,
            ))
        test_db_session.commit()
        
        analytics = MusicAnalytics()
        result = analytics.get_mood_insights(days=30)
        
        assert result["status"] == "sucesso"
        assert "mood_transitions" in result


class TestMusicAnalyticsListeningTime:
    
    def test_get_listening_time_analysis_empty(self, monkeypatch_db, test_db_session):
        """Testa análise de tempo sem dados"""
        analytics = MusicAnalytics()
        result = analytics.get_listening_time_analysis(days=30)
        
        assert result["status"] == "sem_dados"

    def test_get_listening_time_analysis_with_data(self, monkeypatch_db, test_db_session, sample_tracks):
        """Testa análise de tempo de escuta"""
        for track in sample_tracks:
            test_db_session.add(track)
        test_db_session.commit()
        
        analytics = MusicAnalytics()
        result = analytics.get_listening_time_analysis(days=30)
        
        assert result["status"] == "sucesso"
        assert "peak_hour" in result
        assert "by_period" in result
        assert "by_day" in result
        assert result["peak_hour"] == 14

    def test_listening_periods_calculation(self, monkeypatch_db, test_db_session):
        """Testa distribuição por períodos do dia"""
        now = datetime.now(timezone.utc)
        
        # Cria tracks em diferentes horas
        hours_and_periods = [
            (2, "madrugada (00-05h)"),
            (9, "manhã (05-12h)"),
            (15, "tarde (12-18h)"),
            (20, "noite (18-23h)"),
        ]
        
        for hour, period in hours_and_periods:
            for _ in range(2):
                test_db_session.add(TrackPlayed(
                    track_id=f"track_{hour}",
                    track_uri=f"spotify:track:track_{hour}",
                    title=f"Song at {hour}h",
                    artists='["Artist"]',
                    album="Album",
                    duration_ms=240000,
                    played_at=now.replace(hour=hour),
                    hour_of_day=hour,
                    day_of_week=2,
                ))
        test_db_session.commit()
        
        analytics = MusicAnalytics()
        result = analytics.get_listening_time_analysis(days=30)
        
        assert all(result["by_period"][p] >= 0 for p in result["by_period"])


class TestMusicAnalyticsArtist:
    
    def test_analyze_artist_listener_base_no_data(self, monkeypatch_db, test_db_session):
        """Testa análise de artista sem dados"""
        analytics = MusicAnalytics()
        result = analytics.analyze_artist_listener_base("The Beatles", days=90)
        
        assert result.artist_name == "The Beatles"
        assert result.total_plays == 0
        assert result.unique_listeners_estimated == 0

    def test_analyze_artist_listener_base_with_data(self, monkeypatch_db, test_db_session):
        """Testa análise de artista com dados"""
        now = datetime.now(timezone.utc)
        
        for i in range(5):
            test_db_session.add(TrackPlayed(
                track_id=f"track_{i}",
                track_uri=f"spotify:track:track_{i}",
                title=f"Artist Song {i}",
                artists='["The Beatles", "John Lennon"]',
                album="Album",
                duration_ms=240000,
                played_at=now - timedelta(days=i),
                hour_of_day=14,
                day_of_week=2,
                mood="happy",
            ))
        test_db_session.commit()
        
        analytics = MusicAnalytics()
        result = analytics.analyze_artist_listener_base("The Beatles", days=90)
        
        assert result.total_plays == 5
        assert result.unique_listeners_estimated > 0
