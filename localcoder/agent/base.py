"""Base agent class for LocalCoder."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from localcoder.config.settings import Settings
from localcoder.models.message import ConversationState, Message, MessageRole
from localcoder.providers.ollama import OllamaProvider, OllamaMessage
from localcoder.tools.base import Tool


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(
        self,
        settings: Settings,
        project_root: Path,
        dry_run: bool = False,
    ):
        self.settings = settings
        self.project_root = project_root
        self.dry_run = dry_run
        self.provider = OllamaProvider(
            base_url=settings.ollama_url,
            model=settings.default_model,
            timeout=float(settings.timeout),
        )
        self.conversation = ConversationState(
            system_prompt=self._get_system_prompt(),
            project_root=str(project_root),
        )
        self._tools: dict[str, Tool] = {}
        self._register_tools()

    @abstractmethod
    def _get_system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        pass

    @abstractmethod
    def _register_tools(self) -> None:
        """Register available tools."""
        pass

    def register_tool(self, tool: Tool) -> None:
        """Register a single tool."""
        # Initialize tool with workspace root if it supports it
        if hasattr(tool, "workspace_root"):
            tool.workspace_root = self.project_root
        self._tools[tool.name] = tool

    def get_available_tools(self) -> list[Tool]:
        """Get list of available tools."""
        return list(self._tools.values())

    def get_tool_definitions(self) -> list[dict]:
        """Get tool definitions for LLM."""
        return [tool.get_tool_definition() for tool in self.get_available_tools()]

    async def execute_tool(self, tool_name: str, **kwargs) -> tuple[bool, str]:
        """Execute a tool by name."""
        if tool_name not in self._tools:
            return False, f"Unknown tool: {tool_name}"

        tool = self._tools[tool_name]

        # Validate input
        valid, error = tool.validate_input(**kwargs)
        if not valid:
            return False, f"Invalid input: {error}"

        # Execute
        result = await tool.execute(**kwargs)
        return result.success, result.output if result.success else result.error

    async def chat(self, user_message: str) -> str:
        """Send a message and get a response."""
        # Add user message to conversation
        self.conversation.add_message(Message.user(user_message))

        # Get response from model
        response = await self.provider.chat(
            messages=[
                OllamaMessage(role=m.role.value, content=m.content)
                for m in self.conversation.messages
            ],
            system_prompt=self.conversation.system_prompt,
            temperature=self.settings.temperature,
            top_p=self.settings.top_p,
        )

        # Add assistant response to conversation
        self.conversation.add_message(
            Message.assistant(response.message.content)
        )

        return response.message.content

    async def close(self) -> None:
        """Clean up resources."""
        await self.provider.close()

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation.clear()

    def set_model(self, model: str) -> None:
        """Change the model being used."""
        self.provider.set_model(model)
        self.settings.default_model = model
