"""Tests for configuration module."""
import pytest
from unittest.mock import patch
import os


class TestConfig:
    """Test configuration settings."""

    def test_default_settings(self):
        """Test default configuration values."""
        from app.config import Settings
        
        settings = Settings()
        
        assert settings.app_name == "AI Document Q&A"
        assert settings.debug is True
        assert settings.mongodb_url == "mongodb://localhost:27017"
        assert settings.mongodb_db_name == "document_qa"
        assert settings.ollama_base_url == "http://localhost:11434"
        assert settings.upload_dir == "uploads"
        assert settings.max_file_size == 100 * 1024 * 1024
        assert "pdf" in settings.allowed_extensions
        assert "mp3" in settings.allowed_extensions
        assert "mp4" in settings.allowed_extensions

    def test_get_settings_cached(self):
        """Test that get_settings returns cached instance."""
        from app.config import get_settings
        
        settings1 = get_settings()
        settings2 = get_settings()
        
        assert settings1 is settings2

    def test_settings_from_env(self):
        """Test settings can be loaded from environment."""
        from app.config import Settings
        
        with patch.dict(os.environ, {
            "MONGODB_URL": "mongodb://testhost:27017",
            "MONGODB_DB_NAME": "test_db",
        }):
            settings = Settings()
            assert settings.mongodb_url == "mongodb://testhost:27017"
            assert settings.mongodb_db_name == "test_db"

    def test_chunk_settings(self):
        """Test chunking configuration."""
        from app.config import Settings
        
        settings = Settings()
        
        assert settings.chunk_size == 512
        assert settings.chunk_overlap == 50
        assert settings.embedding_model == "all-MiniLM-L6-v2"

    def test_whisper_settings(self):
        """Test Whisper configuration."""
        from app.config import Settings
        
        settings = Settings()
        
        assert settings.whisper_model == "base"
