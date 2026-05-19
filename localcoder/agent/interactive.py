"""Interactive chat agent for LocalCoder with autonomous tool execution."""

import asyncio
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from localcoder.agent.autonomous import AutonomousAgent
from localcoder.config.settings import Settings
from localcoder.models.message import Message
from localcoder.providers.ollama import StreamChunk
from localcoder.utils.rich import create_rich_console


class InteractiveAgent(AutonomousAgent):
    """Interactive agent for chat sessions with autonomous execution."""

    def __init__(
        self,
        settings: Settings,
        project_root: Path,
        console: Optional[Console] = None,
        auto_execute: bool = True,
    ):
        super().__init__(settings, project_root, console, auto_execute=auto_execute)
        self._running = True

    def _get_system_prompt(self) -> str:
        return """You are LocalCoder, an AUTONOMOUS coding agent running in a terminal.

CRITICAL RULES:
1. You MUST execute tools directly when they are available for the task.
2. NEVER tell the user how to use terminal commands, editors, or shell utilities.
3. NEVER provide step-by-step instructions for actions you can perform yourself.
4. Your default behavior is ACTION, not INSTRUCTION.

You help users with coding tasks including:
- Writing new code (CREATE files directly)
- Editing existing files (USE edit_file tool)
- Debugging issues (READ files, RUN commands)
- Explaining code (only explain when asked)
- Running commands and tests (EXECUTE directly)
- Git operations (COMMIT changes)

When you need to make changes, use the appropriate tools IMMEDIATELY.
Do NOT explain what commands to run - RUN them yourself.
Do NOT tell users to open editors - EDIT files yourself.

Only provide explanations when:
- The user explicitly asks for an explanation
- No tool exists to perform the task
- Permission is denied

Complete tasks autonomously whenever possible."""

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
        """Process a user message with autonomous tool execution."""
        # Use the autonomous agent's execute method
        self._init_router()
        
        # Display analyzing status
        self.console.print("\n[bold blue]Processing request...[/bold blue]")
        
        try:
            # Execute the request autonomously
            response = await self.execute(message)
            
            # Display the response
            self.console.print(f"\n[bold green]Result:[/bold green]\n{response}")
            
        except Exception as e:
            self.console.print(f"\n[red]Error: {str(e)}[/red]")
