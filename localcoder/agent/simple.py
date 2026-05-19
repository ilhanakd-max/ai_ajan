"""Simple agent for Q&A interactions."""

from pathlib import Path

from localcoder.agent.base import BaseAgent
from localcoder.config.settings import Settings


class SimpleAgent(BaseAgent):
    """Simple agent for question and answer interactions."""

    def _get_system_prompt(self) -> str:
        return """You are LocalCoder, a helpful AI coding assistant.
You help users understand codebases, answer questions about code, and provide programming guidance.
You have access to read files and search the codebase to provide accurate answers.
Always be concise and direct in your responses."""

    def _register_tools(self) -> None:
        from localcoder.tools.filesystem import ReadFileTool, ListFilesTool
        from localcoder.tools.search import SearchTextTool, GrepCodeTool

        self.register_tool(ReadFileTool())
        self.register_tool(ListFilesTool())
        self.register_tool(SearchTextTool())
        self.register_tool(GrepCodeTool())

    async def ask(self, question: str) -> str:
        """Ask a question and get an answer."""
        try:
            response = await self.chat(question)
            return response
        finally:
            await self.close()
