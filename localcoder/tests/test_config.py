"""Tests for configuration module."""

import pytest
from pathlib import Path

from localcoder.config.settings import Settings, PermissionLevel
from localcoder.config.manager import ConfigManager


class TestSettings:
    """Test Settings model."""

    def test_default_settings(self):
        """Test default settings creation."""
        settings = Settings.default()
        assert settings.ollama_url == "http://localhost:11434"
        assert settings.default_model == "qwen2.5-coder:7b"
        assert settings.permission_mode == PermissionLevel.WORKSPACE_WRITE
        assert settings.max_steps == 20
        assert settings.temperature == 0.7

    def test_custom_settings(self):
        """Test custom settings creation."""
        settings = Settings(
            ollama_url="http://custom:11434",
            default_model="deepseek-coder",
            max_steps=50,
        )
        assert settings.ollama_url == "http://custom:11434"
        assert settings.default_model == "deepseek-coder"
        assert settings.max_steps == 50

    def test_permission_level_enum(self):
        """Test permission level enum values."""
        assert PermissionLevel.READ_ONLY.value == "read-only"
        assert PermissionLevel.WORKSPACE_WRITE.value == "workspace-write"
        assert PermissionLevel.FULL_ACCESS.value == "full-access"

    def test_memory_db_path(self):
        """Test memory database path resolution."""
        settings = Settings.default()
        project_root = Path("/tmp/test_project")
        db_path = settings.get_memory_db_path(project_root)
        assert db_path == project_root / ".localcoder" / "memory.db"


class TestConfigManager:
    """Test ConfigManager."""

    def test_get_config_no_files(self, tmp_path):
        """Test getting config when no files exist."""
        manager = ConfigManager()
        manager.reset()
        
        # Should return default settings
        settings = manager.get_config(tmp_path)
        assert settings is not None

    def test_save_and_load_project_config(self, tmp_path):
        """Test saving and loading project config."""
        manager = ConfigManager()
        manager.reset()
        
        settings = Settings(
            ollama_url="http://test:11434",
            default_model="test-model",
        )
        
        manager.save_project_config(settings, tmp_path)
        
        # Load it back
        manager.reset()
        loaded = manager.load_project_config(tmp_path)
        assert loaded.ollama_url == "http://test:11434"
        assert loaded.default_model == "test-model"
