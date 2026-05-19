"""Message and conversation models."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class MessageRole(str, Enum):
    """Role of a message sender."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class ToolCall:
    """A tool call request."""

    name: str
    arguments: dict
    call_id: Optional[str] = None


@dataclass
class ToolResult:
    """Result from a tool execution."""

    tool_name: str
    success: bool
    output: str
    error: Optional[str] = None
    call_id: Optional[str] = None


@dataclass
class Message:
    """A message in the conversation."""

    role: MessageRole
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_result: Optional[ToolResult] = None
    timestamp: float = field(default_factory=lambda: __import__("time").time())

    def to_ollama_message(self) -> dict:
        """Convert to Ollama message format."""
        msg = {"role": self.role.value, "content": self.content}
        if self.tool_calls:
            msg["tool_calls"] = [
                {"name": tc.name, "arguments": tc.arguments} for tc in self.tool_calls
            ]
        return msg

    @classmethod
    def system(cls, content: str) -> "Message":
        """Create a system message."""
        return cls(role=MessageRole.SYSTEM, content=content)

    @classmethod
    def user(cls, content: str) -> "Message":
        """Create a user message."""
        return cls(role=MessageRole.USER, content=content)

    @classmethod
    def assistant(cls, content: str, tool_calls: Optional[list[ToolCall]] = None) -> "Message":
        """Create an assistant message."""
        return cls(
            role=MessageRole.ASSISTANT,
            content=content,
            tool_calls=tool_calls or [],
        )

    @classmethod
    def tool_result(cls, tool_name: str, output: str, success: bool = True) -> "Message":
        """Create a tool result message."""
        return cls(
            role=MessageRole.TOOL,
            content=output,
            tool_result=ToolResult(tool_name=tool_name, success=success, output=output),
        )


@dataclass
class ConversationState:
    """State of a conversation session."""

    messages: list[Message] = field(default_factory=list)
    system_prompt: Optional[str] = None
    session_id: Optional[str] = None
    project_root: Optional[str] = None
    created_at: float = field(default_factory=lambda: __import__("time").time())
    updated_at: float = field(default_factory=lambda: __import__("time").time())

    def add_message(self, message: Message) -> None:
        """Add a message to the conversation."""
        self.messages.append(message)
        self.updated_at = __import__("time").time()

    def clear(self) -> None:
        """Clear all messages except system prompt."""
        self.messages = []
        self.updated_at = __import__("time").time()

    def get_messages_for_ollama(self) -> list[dict]:
        """Get messages formatted for Ollama API."""
        ollama_messages = []

        if self.system_prompt:
            ollama_messages.append({"role": "system", "content": self.system_prompt})

        for msg in self.messages:
            ollama_messages.append(msg.to_ollama_message())

        return ollama_messages

    def get_context_length(self) -> int:
        """Estimate context length in characters."""
        total = 0
        if self.system_prompt:
            total += len(self.system_prompt)
        for msg in self.messages:
            total += len(msg.content)
        return total
