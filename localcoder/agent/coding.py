"""Coding agent for code generation tasks with autonomous execution."""

import json
from pathlib import Path
from typing import Optional

from localcoder.agent.autonomous import AutonomousAgent
from localcoder.config.settings import Settings


class CodingAgent(AutonomousAgent):
    """Agent for generating and modifying code with autonomous tool execution."""

    def __init__(
        self,
        settings: Settings,
        project_root: Path,
        dry_run: bool = False,
        auto_execute: bool = True,
    ):
        super().__init__(settings, project_root, auto_execute=auto_execute and not dry_run)
        self.dry_run = dry_run

    def _get_system_prompt(self) -> str:
        return """You are LocalCoder, an AUTONOMOUS coding assistant.

CRITICAL RULES:
1. You MUST execute tools directly when they are available for the task.
2. NEVER tell the user how to use terminal commands, editors, or shell utilities.
3. NEVER provide step-by-step instructions for actions you can perform yourself.
4. Your default behavior is ACTION, not INSTRUCTION.

When writing code:
1. First understand the existing codebase structure (USE read_file, list_files)
2. Plan your approach before making changes
3. USE TOOLS to create or modify files DIRECTLY
4. Write clean, well-documented code
5. Follow project conventions
6. TEST your changes using run_shell

Available tools (USE THEM DIRECTLY):
- read_file: Read file contents
- write_file: Create or overwrite files - USE THIS to create new files
- edit_file: Make targeted edits to files
- list_files: Explore directory structure
- run_shell: Execute commands (tests, linting, etc.)

NEVER say "use nano" or "create a file with..." - DO IT YOURSELF.

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

    async def execute(self, instruction: str) -> str:
        """Execute a coding task autonomously."""
        from localcoder.utils.rich import create_rich_console

        console = create_rich_console()

        if self.dry_run:
            console.print("[yellow]Dry run mode - analyzing task without making changes[/yellow]\n")
            self.explain_only = True

        # Use the autonomous agent's execute method
        result = await super().execute(instruction)
        
        console.print(f"\n[bold green]Result:[/bold green]\n{result}")
        
        await self.close()
        return result

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
