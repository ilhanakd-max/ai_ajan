"""Ollama provider for LocalCoder."""

import asyncio
from dataclasses import dataclass, field
from typing import AsyncGenerator, Callable, Optional

import httpx


@dataclass
class OllamaMessage:
    """A message in the conversation."""

    role: str  # "system", "user", or "assistant"
    content: str


@dataclass
class OllamaResponse:
    """Response from Ollama API."""

    message: OllamaMessage
    done: bool = True
    total_duration: int = 0
    load_duration: int = 0
    prompt_eval_count: int = 0
    eval_count: int = 0
    eval_duration: int = 0


@dataclass
class StreamChunk:
    """A chunk of streamed response."""

    content: str
    done: bool = False


class OllamaProvider:
    """Provider for Ollama LLM API."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen2.5-coder:7b",
        timeout: float = 300.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def list_models(self) -> list[dict]:
        """List available models."""
        client = await self._get_client()
        response = await client.get("/api/tags")
        response.raise_for_status()
        data = response.json()
        return data.get("models", [])

    async def chat(
        self,
        messages: list[OllamaMessage],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stream: bool = False,
    ) -> OllamaResponse:
        """Send a chat request to Ollama."""
        client = await self._get_client()

        # Build request payload
        ollama_messages = []
        if system_prompt:
            ollama_messages.append({"role": "system", "content": system_prompt})
        for msg in messages:
            ollama_messages.append({"role": msg.role, "content": msg.content})

        payload = {
            "model": self.model,
            "messages": ollama_messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
            },
        }

        response = await client.post("/api/chat", json=payload)
        response.raise_for_status()

        if stream:
            # This shouldn't happen as we're not streaming
            raise ValueError("Use chat_stream for streaming responses")

        data = response.json()
        message_data = data.get("message", {})

        return OllamaResponse(
            message=OllamaMessage(
                role=message_data.get("role", "assistant"),
                content=message_data.get("content", ""),
            ),
            done=data.get("done", True),
            total_duration=data.get("total_duration", 0),
            load_duration=data.get("load_duration", 0),
            prompt_eval_count=data.get("prompt_eval_count", 0),
            eval_count=data.get("eval_count", 0),
            eval_duration=data.get("eval_duration", 0),
        )

    async def chat_stream(
        self,
        messages: list[OllamaMessage],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream a chat response from Ollama."""
        client = await self._get_client()

        # Build request payload
        ollama_messages = []
        if system_prompt:
            ollama_messages.append({"role": "system", "content": system_prompt})
        for msg in messages:
            ollama_messages.append({"role": msg.role, "content": msg.content})

        payload = {
            "model": self.model,
            "messages": ollama_messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
            },
        }

        # Use stream method for SSE-like streaming
        async with client.stream("POST", "/api/chat", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                try:
                    import json

                    data = json.loads(line)
                    message_data = data.get("message", {})
                    content = message_data.get("content", "")
                    done = data.get("done", False)

                    if content:
                        yield StreamChunk(content=content, done=done)
                    elif done:
                        yield StreamChunk(content="", done=True)
                        break
                except json.JSONDecodeError:
                    continue

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stream: bool = False,
    ) -> OllamaResponse:
        """Generate a completion for a single prompt."""
        messages = [OllamaMessage(role="user", content=prompt)]
        return await self.chat(
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature,
            top_p=top_p,
            stream=stream,
        )

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream a completion for a single prompt."""
        messages = [OllamaMessage(role="user", content=prompt)]
        async for chunk in self.chat_stream(
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature,
            top_p=top_p,
        ):
            yield chunk

    async def check_health(self) -> bool:
        """Check if Ollama server is running."""
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            return response.status_code == 200
        except Exception:
            return False

    def set_model(self, model: str) -> None:
        """Set the model to use."""
        self.model = model

    def get_model(self) -> str:
        """Get the current model."""
        return self.model
