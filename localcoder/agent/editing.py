"""Editing agent for file modifications."""

from pathlib import Path

from localcoder.agent.base import BaseAgent
from localcoder.config.settings import Settings


class EditingAgent(BaseAgent):
    """Agent for editing existing files."""

    def _get_system_prompt(self) -> str:
        return """You are LocalCoder, an expert AI coding assistant.
You help users modify existing files based on their instructions.

When editing files:
1. First read the file to understand its current state
2. Plan your changes carefully
3. Use edit_file for targeted changes or write_file for larger rewrites
4. Preserve existing code style and conventions
5. Explain what you changed

Available tools:
- read_file: Read file contents before editing
- edit_file: Make targeted search/replace edits
- write_file: Rewrite entire file if needed

Always show the user what changes you're making."""

    def _register_tools(self) -> None:
        from localcoder.tools.filesystem import ReadFileTool, EditFileTool, WriteFileTool

        self.register_tool(ReadFileTool())
        self.register_tool(EditFileTool())
        self.register_tool(WriteFileTool())

    async def edit(self, file_path: str, instruction: str) -> None:
        """Edit a file based on instructions."""
        from localcoder.utils.rich import create_rich_console

        console = create_rich_console()

        # Read the file first
        console.print(f"[blue]Reading {file_path}...[/blue]")
        success, result = await self.execute_tool("read_file", path=file_path)

        if not success:
            console.print(f"[red]Error reading file: {result}[/red]")
            await self.close()
            return

        original_content = result

        # Build prompt with file content
        prompt = f"""I need to edit this file: {file_path}

Current content:
```
{original_content}
```

Instruction: {instruction}

Please provide the exact changes to make. Specify:
1. The text to search for (old_text)
2. The replacement text (new_text)

Or if the changes are extensive, provide the complete new file content."""

        response = await self.chat(prompt)
        console.print(f"\n[green]{response}[/green]")

        await self.close()
