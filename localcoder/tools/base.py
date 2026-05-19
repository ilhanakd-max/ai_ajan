"""Base tool classes and interfaces."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class SafetyLevel(str, Enum):
    """Safety levels for tool execution."""

    SAFE = "safe"  # No side effects, read-only
    WORKSPACE = "workspace"  # Can modify workspace files
    DANGEROUS = "dangerous"  # Can execute arbitrary code or delete files


@dataclass
class ToolResult:
    """Result from a tool execution."""

    success: bool
    output: str
    error: Optional[str] = None
    data: Optional[Any] = None

    def __str__(self) -> str:
        if self.success:
            return self.output
        return f"Error: {self.error or 'Unknown error'}"


class Tool(ABC):
    """Abstract base class for all tools."""

    name: str = ""
    description: str = ""
    safety_level: SafetyLevel = SafetyLevel.SAFE

    @property
    @abstractmethod
    def input_schema(self) -> dict:
        """Return JSON schema for tool input."""
        pass

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given arguments."""
        pass

    def validate_input(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate input arguments against schema."""
        required = self.input_schema.get("required", [])
        properties = self.input_schema.get("properties", {})

        # Check required fields
        for field in required:
            if field not in kwargs:
                return False, f"Missing required field: {field}"

        # Check types (basic validation)
        for field, value in kwargs.items():
            if field in properties:
                field_type = properties[field].get("type")
                if field_type == "string" and not isinstance(value, str):
                    return False, f"Field '{field}' must be a string"
                elif field_type == "integer" and not isinstance(value, int):
                    return False, f"Field '{field}' must be an integer"
                elif field_type == "boolean" and not isinstance(value, bool):
                    return False, f"Field '{field}' must be a boolean"
                elif field_type == "array" and not isinstance(value, list):
                    return False, f"Field '{field}' must be an array"
                elif field_type == "object" and not isinstance(value, dict):
                    return False, f"Field '{field}' must be an object"

        return True, None

    def get_tool_definition(self) -> dict:
        """Get tool definition for LLM function calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.input_schema,
        }
