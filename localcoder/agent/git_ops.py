"""Git operations agent for LocalCoder."""

from pathlib import Path

from localcoder.agent.base import BaseAgent
from localcoder.config.settings import Settings


class GitAgent(BaseAgent):
    """Agent for git operations."""

    def _get_system_prompt(self) -> str:
        return """You are LocalCoder, an expert AI coding assistant.
You help users with git operations including commits, diffs, and history.

When working with git:
1. Check the current status first
2. Review changes with git diff
3. Generate meaningful commit messages
4. Explain what is being committed

Available tools:
- git_status: Show repository status
- git_diff: Show changes
- git_commit: Create commits

Always show the user what changes will be committed before proceeding."""

    def _register_tools(self) -> None:
        from localcoder.tools.git import GitStatusTool, GitDiffTool, GitCommitTool

        self.register_tool(GitStatusTool())
        self.register_tool(GitDiffTool())
        self.register_tool(GitCommitTool())

    async def commit(self, message: str = None) -> None:
        """Create a git commit, optionally generating the message."""
        from localcoder.utils.rich import create_rich_console

        console = create_rich_console()

        # Check git status first
        console.print("[blue]Checking git status...[/blue]")
        success, status_output = await self.execute_tool("git_status")

        if not success:
            console.print(f"[red]{status_output}[/red]")
            await self.close()
            return

        console.print(f"[green]{status_output}[/green]\n")

        # If no message provided, generate one
        if not message:
            console.print("[blue]Generating commit message...[/blue]")

            # Get diff for context
            _, diff_output = await self.execute_tool("git_diff")

            prompt = f"""Based on these changes, generate a concise but descriptive commit message:

{diff_output[:2000]}

Provide only the commit message, nothing else.
Follow conventional commit format if applicable (feat:, fix:, chore:, etc.)."""

            message = await self.chat(prompt)
            message = message.strip().strip('"').strip("'")
            console.print(f"[cyan]Generated message: {message}[/cyan]\n")

        # Confirm and commit
        console.print(f"[blue]Creating commit: {message}[/blue]")
        success, result = await self.execute_tool("git_commit", message=message, all_flag=True)

        if success:
            console.print(f"[green]{result}[/green]")
        else:
            console.print(f"[red]Commit failed: {result}[/red]")

        await self.close()
