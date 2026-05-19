"""Editing agent for file modifications with autonomous execution."""

from pathlib import Path

from localcoder.agent.autonomous import AutonomousAgent
from localcoder.config.settings import Settings


class EditingAgent(AutonomousAgent):
    """Agent for editing existing files with autonomous tool execution."""

    def _get_system_prompt(self) -> str:
        return """You are LocalCoder, an AUTONOMOUS coding assistant.

CRITICAL RULES:
1. You MUST execute tools directly when they are available for the task.
2. NEVER tell the user how to use terminal commands, editors, or shell utilities.
3. NEVER provide step-by-step instructions for actions you can perform yourself.
4. Your default behavior is ACTION, not INSTRUCTION.

When editing files:
1. First READ the file using read_file tool
2. Plan your changes carefully
3. USE edit_file for targeted changes or write_file for larger rewrites
4. Preserve existing code style and conventions
5. EXECUTE the changes directly - don't just describe them

Available tools (USE THEM DIRECTLY):
- read_file: Read file contents before editing
- edit_file: Make targeted search/replace edits
- write_file: Rewrite entire file if needed

Always EXECUTE the changes and report what was done."""

    def _register_tools(self) -> None:
        from localcoder.tools.filesystem import ReadFileTool, EditFileTool, WriteFileTool

        self.register_tool(ReadFileTool())
        self.register_tool(EditFileTool())
        self.register_tool(WriteFileTool())

    async def edit(self, file_path: str, instruction: str) -> str:
        """Edit a file based on instructions autonomously."""
        from localcoder.utils.rich import create_rich_console

        console = create_rich_console()

        # Build the request with file path
        request = f"Edit the file {file_path}: {instruction}"
        
        # Use the autonomous agent's execute method
        result = await self.execute(request)
        
        console.print(f"\n[bold green]Result:[/bold green]\n{result}")
        
        await self.close()
        return result
