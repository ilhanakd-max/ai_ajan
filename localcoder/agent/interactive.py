"""Interactive chat agent for LocalCoder."""

import asyncio
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from localcoder.agent.base import BaseAgent
from localcoder.config.settings import Settings
from localcoder.models.message import Message
from localcoder.providers.ollama import StreamChunk
from localcoder.utils.rich import create_rich_console


class InteractiveAgent(BaseAgent):
    """Interactive agent for chat sessions."""

    def __init__(
        self,
        settings: Settings,
        project_root: Path,
        console: Optional[Console] = None,
    ):
        super().__init__(settings, project_root)
        self.console = console or create_rich_console()
        self._running = True

    def _get_system_prompt(self) -> str:
        return """You are LocalCoder, an expert AI coding assistant running in a terminal.
You help users with coding tasks including:
- Writing new code
- Editing existing files
- Debugging issues
- Explaining code
- Running commands and tests
- Git operations

You have access to tools for file operations, shell commands, search, and git.
When you need to make changes, use the appropriate tools.
Always explain what you're doing before making changes.
Be concise but thorough in your responses."""

    def _register_tools(self) -> None:
        from localcoder.tools.filesystem import (
            ReadFileTool,
            WriteFileTool,
            EditFileTool,
            ListFilesTool,
            DeleteFileTool,
            RenameFileTool,
            CreateDirectoryTool,
        )
        from localcoder.tools.shell import RunShellTool
        from localcoder.tools.search import SearchTextTool, GrepCodeTool
        from localcoder.tools.git import GitStatusTool, GitDiffTool, GitCommitTool

        self.register_tool(ReadFileTool())
        self.register_tool(WriteFileTool())
        self.register_tool(EditFileTool())
        self.register_tool(ListFilesTool())
        self.register_tool(DeleteFileTool())
        self.register_tool(RenameFileTool())
        self.register_tool(CreateDirectoryTool())
        self.register_tool(RunShellTool(workspace_root=self.project_root))
        self.register_tool(SearchTextTool())
        self.register_tool(GrepCodeTool())
        self.register_tool(GitStatusTool())
        self.register_tool(GitDiffTool())
        self.register_tool(GitCommitTool())

    async def run(self) -> None:
        """Run the interactive chat session."""
        self.console.print(
            Panel(
                "[bold]Welcome to LocalCoder Chat![/bold]\n\n"
                "Type your message and press Enter.\n"
                "Use /help for available commands.\n"
                "Press Ctrl+C to exit.",
                title="LocalCoder",
                border_style="blue",
            )
        )

        while self._running:
            try:
                # Get user input
                user_input = Prompt.ask("\n[bold green]You[/bold green]")

                if not user_input.strip():
                    continue

                # Handle slash commands
                if user_input.startswith("/"):
                    await self._handle_command(user_input)
                    continue

                # Process message
                await self._process_message(user_input)

            except KeyboardInterrupt:
                self.console.print("\n[yellow]Interrupted. Type /exit to quit.[/yellow]")
            except EOFError:
                break

        await self.close()

    async def _handle_command(self, command: str) -> None:
        """Handle slash commands."""
        cmd = command.lower().strip()

        if cmd == "/help":
            self._show_help()
        elif cmd == "/clear":
            self.clear_history()
            self.console.print("[green]History cleared[/green]")
        elif cmd == "/exit" or cmd == "/quit":
            self._running = False
            self.console.print("[blue]Goodbye![/blue]")
        elif cmd == "/tools":
            self._show_tools()
        elif cmd == "/model":
            self.console.print(f"Current model: [cyan]{self.settings.default_model}[/cyan]")
        elif cmd.startswith("/model "):
            new_model = cmd[7:].strip()
            self.set_model(new_model)
            self.console.print(f"[green]Model changed to: {new_model}[/green]")
        else:
            self.console.print(f"[yellow]Unknown command: {cmd}[/yellow]")
            self._show_help()

    def _show_help(self) -> None:
        """Show help information."""
        help_text = """[bold]Available Commands:[/bold]
  /help     Show this help message
  /clear    Clear conversation history
  /tools    Show available tools
  /model    Show or change current model
  /exit     Exit the chat session

Just type your message to chat with the AI."""
        self.console.print(Panel(help_text, title="Help", border_style="cyan"))

    def _show_tools(self) -> None:
        """Show available tools."""
        tools = self.get_available_tools()
        tool_list = "\n".join([f"  - [cyan]{t.name}[/cyan]: {t.description}" for t in tools])
        self.console.print(Panel(tool_list, title="Available Tools", border_style="green"))

    async def _process_message(self, message: str) -> None:
        """Process a user message."""
        # Add user message to conversation
        self.conversation.add_message(Message.user(message))

        # Stream response
        self.console.print("\n[bold blue]LocalCoder[/bold blue]:")

        full_response = ""
        async for chunk in self.provider.chat_stream(
            messages=[
                {"role": m.role.value, "content": m.content}
                for m in self.conversation.messages
            ],
            system_prompt=self.conversation.system_prompt,
            temperature=self.settings.temperature,
            top_p=self.settings.top_p,
        ):
            self.console.print(chunk.content, end="", markup=False)
            full_response += chunk.content
            await asyncio.sleep(0.01)  # Small delay for smoother streaming

        self.console.print()  # New line

        # Add assistant response to conversation
        self.conversation.add_message(Message.assistant(full_response))
