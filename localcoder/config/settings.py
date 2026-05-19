"""Settings and configuration models for LocalCoder."""

from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class PermissionLevel(str, Enum):
    """Permission levels for tool execution."""

    READ_ONLY = "read-only"
    WORKSPACE_WRITE = "workspace-write"
    FULL_ACCESS = "full-access"


class Settings(BaseModel):
    """LocalCoder configuration settings."""

    # Ollama settings
    ollama_url: str = Field(default="http://localhost:11434", description="Ollama API URL")
    default_model: str = Field(default="qwen2.5-coder:7b", description="Default reasoning model")
    needle_model_path: Optional[str] = Field(default=None, description="Path to Needle model")

    # Agent settings
    permission_mode: PermissionLevel = Field(
        default=PermissionLevel.WORKSPACE_WRITE, description="Default permission level"
    )
    auto_confirm: bool = Field(default=False, description="Auto-confirm dangerous actions")
    max_steps: int = Field(default=20, description="Maximum steps per agent loop")
    timeout: int = Field(default=300, description="Timeout in seconds for operations")
    context_limit: int = Field(default=8192, description="Maximum context tokens")

    # Model parameters
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Model temperature")
    top_p: float = Field(default=0.9, ge=0.0, le=1.0, description="Top-p sampling")

    # Memory settings
    enable_memory: bool = Field(default=True, description="Enable persistent memory")
    memory_db_path: Optional[Path] = Field(default=None, description="Path to memory database")

    # Paths
    workspace_root: Optional[Path] = Field(default=None, description="Workspace root directory")
    skills_dir: Optional[Path] = Field(default=None, description="Custom skills directory")

    class Config:
        """Pydantic config."""

        use_enum_values = True
        extra = "ignore"

    @classmethod
    def default(cls) -> "Settings":
        """Create default settings."""
        return cls()

    def get_memory_db_path(self, project_root: Path) -> Path:
        """Get the memory database path."""
        if self.memory_db_path:
            return self.memory_db_path
        return project_root / ".localcoder" / "memory.db"

    def get_skills_dir(self, project_root: Path) -> Path:
        """Get the skills directory path."""
        if self.skills_dir:
            return self.skills_dir
        return project_root / ".localcoder" / "skills"
