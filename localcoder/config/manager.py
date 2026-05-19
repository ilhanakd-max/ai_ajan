"""Configuration manager for LocalCoder."""

import os
from pathlib import Path
from typing import Optional

import tomlkit

from localcoder.config.settings import PermissionLevel, Settings


class ConfigManager:
    """Manages configuration loading and saving."""

    GLOBAL_CONFIG_DIR = Path.home() / ".config" / "localcoder"
    GLOBAL_CONFIG_FILE = GLOBAL_CONFIG_DIR / "config.toml"
    PROJECT_CONFIG_FILE = Path(".localcoder") / "config.toml"

    def __init__(self):
        self.global_config: Optional[Settings] = None
        self.project_config: Optional[Settings] = None
        self._merged_config: Optional[Settings] = None

    def load_global_config(self) -> Settings:
        """Load global configuration from ~/.config/localcoder/config.toml."""
        if self.global_config is not None:
            return self.global_config

        if self.GLOBAL_CONFIG_FILE.exists():
            try:
                content = self.GLOBAL_CONFIG_FILE.read_text()
                data = tomlkit.parse(content)
                self.global_config = self._parse_toml(data)
            except Exception as e:
                print(f"Warning: Failed to load global config: {e}")
                self.global_config = Settings.default()
        else:
            self.global_config = Settings.default()

        return self.global_config

    def load_project_config(self, project_root: Path) -> Settings:
        """Load project-specific configuration."""
        if self.project_config is not None:
            return self.project_config

        config_file = project_root / self.PROJECT_CONFIG_FILE
        if config_file.exists():
            try:
                content = config_file.read_text()
                data = tomlkit.parse(content)
                self.project_config = self._parse_toml(data)
            except Exception as e:
                print(f"Warning: Failed to load project config: {e}")
                self.project_config = Settings.default()
        else:
            self.project_config = Settings.default()

        self.project_config.workspace_root = project_root
        return self.project_config

    def get_config(self, project_root: Optional[Path] = None) -> Settings:
        """Get merged configuration (project overrides global)."""
        if self._merged_config is not None:
            return self._merged_config

        global_config = self.load_global_config()

        if project_root:
            project_config = self.load_project_config(project_root)
            # Merge configs: project settings override global
            merged_dict = global_config.model_dump()
            project_dict = project_config.model_dump(exclude_unset=True)
            merged_dict.update(project_dict)
            self._merged_config = Settings(**merged_dict)
        else:
            self._merged_config = global_config

        return self._merged_config

    def save_global_config(self, settings: Settings) -> None:
        """Save settings to global configuration file."""
        self.GLOBAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        data = self._to_toml(settings)
        self.GLOBAL_CONFIG_FILE.write_text(tomlkit.dumps(data))

    def save_project_config(self, settings: Settings, project_root: Path) -> None:
        """Save settings to project configuration file."""
        config_dir = project_root / ".localcoder"
        config_dir.mkdir(parents=True, exist_ok=True)

        config_file = config_dir / "config.toml"
        data = self._to_toml(settings)
        config_file.write_text(tomlkit.dumps(data))

    def _parse_toml(self, data: dict) -> Settings:
        """Parse TOML data into Settings object."""
        settings_dict = {}

        if "ollama" in data:
            ollama = data["ollama"]
            if "url" in ollama:
                settings_dict["ollama_url"] = str(ollama["url"])
            if "model" in ollama:
                settings_dict["default_model"] = ollama["model"]
            if "needle_model_path" in ollama:
                settings_dict["needle_model_path"] = ollama["needle_model_path"]

        if "agent" in data:
            agent = data["agent"]
            if "permission_mode" in agent:
                settings_dict["permission_mode"] = PermissionLevel(agent["permission_mode"])
            if "auto_confirm" in agent:
                settings_dict["auto_confirm"] = agent["auto_confirm"]
            if "max_steps" in agent:
                settings_dict["max_steps"] = agent["max_steps"]
            if "timeout" in agent:
                settings_dict["timeout"] = agent["timeout"]

        if "model" in data:
            model = data["model"]
            if "temperature" in model:
                settings_dict["temperature"] = model["temperature"]
            if "top_p" in model:
                settings_dict["top_p"] = model["top_p"]

        if "memory" in data:
            memory = data["memory"]
            if "enable" in memory:
                settings_dict["enable_memory"] = memory["enable"]
            if "db_path" in memory:
                settings_dict["memory_db_path"] = Path(memory["db_path"])

        return Settings(**settings_dict)

    def _to_toml(self, settings: Settings) -> dict:
        """Convert Settings object to TOML-compatible dict."""
        data = tomlkit.document()

        data["ollama"] = tomlkit.table()
        data["ollama"]["url"] = settings.ollama_url
        data["ollama"]["model"] = settings.default_model
        if settings.needle_model_path:
            data["ollama"]["needle_model_path"] = settings.needle_model_path

        data["agent"] = tomlkit.table()
        data["agent"]["permission_mode"] = settings.permission_mode.value
        data["agent"]["auto_confirm"] = settings.auto_confirm
        data["agent"]["max_steps"] = settings.max_steps
        data["agent"]["timeout"] = settings.timeout

        data["model"] = tomlkit.table()
        data["model"]["temperature"] = settings.temperature
        data["model"]["top_p"] = settings.top_p

        data["memory"] = tomlkit.table()
        data["memory"]["enable"] = settings.enable_memory
        if settings.memory_db_path:
            data["memory"]["db_path"] = str(settings.memory_db_path)

        return data

    def reset(self) -> None:
        """Reset cached configurations."""
        self.global_config = None
        self.project_config = None
        self._merged_config = None


# Global config manager instance
config_manager = ConfigManager()


def get_settings(project_root: Optional[Path] = None) -> Settings:
    """Get settings for the given project root."""
    return config_manager.get_config(project_root)
