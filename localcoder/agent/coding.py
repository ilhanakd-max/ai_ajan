"""Coding agent for code generation tasks."""

import json
from pathlib import Path
from typing import Optional

from localcoder.agent.base import BaseAgent
from localcoder.config.settings import Settings


class CodingAgent(BaseAgent):
    """Agent for generating and modifying code."""

    def __init__(
        self,
        settings: Settings,
        project_root: Path,
        dry_run: bool = False,
    ):
        super().__init__(settings, project_root, dry_run)
        self.dry_run = dry_run

    def _get_system_prompt(self) -> str:
        return """You are LocalCoder, an expert AI coding assistant.
You help users write new code and modify existing files.

When writing code:
1. First understand the existing codebase structure
2. Plan your approach before making changes
3. Use tools to read existing files when needed
4. Write clean, well-documented code
5. Follow project conventions

Available tools:
- read_file: Read file contents
- write_file: Create or overwrite files
- edit_file: Make targeted edits to files
- list_files: Explore directory structure
- run_shell: Execute commands (tests, linting, etc.)

Always explain what you're doing before making changes.
If the user requests a dry run, show what you would do without actually making changes."""

    def _register_tools(self) -> None:
        from localcoder.tools.filesystem import (
            ReadFileTool,
            WriteFileTool,
            EditFileTool,
            ListFilesTool,
        )
        from localcoder.tools.shell import RunShellTool

        self.register_tool(ReadFileTool())
        self.register_tool(WriteFileTool())
        self.register_tool(EditFileTool())
        self.register_tool(ListFilesTool())
        self.register_tool(RunShellTool(workspace_root=self.project_root))

    async def execute(self, instruction: str) -> None:
        """Execute a coding task."""
        from localcoder.utils.rich import create_rich_console

        console = create_rich_console()

        if self.dry_run:
            console.print("[yellow]Dry run mode - analyzing task without making changes[/yellow]\n")

        # Build context about the project
        context = await self._gather_context()

        # Send request to model with tool instructions
        prompt = f"""{instruction}

Project context:
{context}

Please help implement this. Use the available tools to:
1. Explore the codebase if needed
2. Create or modify files as necessary
3. Test your changes if applicable

{'IMPORTANT: This is a DRY RUN. Do not actually execute any write operations. Just describe what you would do.' if self.dry_run else ''}"""

        response = await self.chat(prompt)
        console.print(response)

        await self.close()

    async def _gather_context(self) -> str:
        """Gather context about the project."""
        context_parts = []

        # List top-level files
        try:
            result = await self.execute_tool("list_files", path=str(self.project_root), recursive=False)
            if result[0]:
                context_parts.append(f"Top-level files:\n{result[1]}")
        except Exception:
            pass

        # Check for common project files
        common_files = [
            "README.md",
            "package.json",
            "pyproject.toml",
            "setup.py",
            "Cargo.toml",
            "go.mod",
            "AGENTS.md",
        ]

        for filename in common_files:
            filepath = self.project_root / filename
            if filepath.exists():
                try:
                    result = await self.execute_tool("read_file", path=str(filepath))
                    if result[0]:
                        content = result[1][:500]  # Limit context
                        context_parts.append(f"{filename}:\n{content}...")
                except Exception:
                    pass

        return "\n\n".join(context_parts) if context_parts else "No additional context available."
