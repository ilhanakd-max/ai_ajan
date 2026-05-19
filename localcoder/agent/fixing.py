"""Fixing agent for automatic bug fixes."""

from pathlib import Path

from localcoder.agent.base import BaseAgent
from localcoder.config.settings import Settings


class FixingAgent(BaseAgent):
    """Agent for automatically fixing code issues."""

    def _get_system_prompt(self) -> str:
        return """You are LocalCoder, an expert AI coding assistant.
You help users identify and fix issues in their codebase.

When fixing issues:
1. Analyze error messages or problem descriptions
2. Locate the problematic code
3. Understand the root cause
4. Apply targeted fixes
5. Verify the fix works

Available tools:
- read_file: Read file contents
- edit_file: Make targeted fixes
- run_shell: Run tests to verify fixes
- grep_code: Search for patterns
- git_diff: Review changes

Always explain what issue you found and how you fixed it."""

    def _register_tools(self) -> None:
        from localcoder.tools.filesystem import ReadFileTool, EditFileTool, ListFilesTool
        from localcoder.tools.shell import RunShellTool
        from localcoder.tools.search import GrepCodeTool
        from localcoder.tools.git import GitDiffTool

        self.register_tool(ReadFileTool())
        self.register_tool(EditFileTool())
        self.register_tool(ListFilesTool())
        self.register_tool(RunShellTool(workspace_root=self.project_root))
        self.register_tool(GrepCodeTool())
        self.register_tool(GitDiffTool())

    async def fix(self) -> None:
        """Automatically find and fix issues."""
        from localcoder.utils.rich import create_rich_console

        console = create_rich_console()

        console.print("[blue]Analyzing codebase for issues...[/blue]")

        # First, try to run tests to see if there are failures
        test_result = await self.execute_tool("run_shell", command="python -m pytest -v --tb=short")

        issues_found = []

        if not test_result[0]:
            # Tests failed, extract error info
            output = test_result[1]
            console.print(f"[yellow]Test failures detected:[/yellow]\n{output[:500]}...")
            issues_found.append(("test_failures", output))

        # Check for common issues
        console.print("[blue]Checking for common issues...[/blue]")

        # Build prompt for the model
        prompt = "Please analyze this codebase for issues and fix them.\n\n"

        if issues_found:
            prompt += f"Test failures:\n{issues_found[0][1][:1000]}\n\n"

        prompt += """Please:
1. Identify the issues
2. Explain what's wrong
3. Apply fixes using the available tools
4. Verify the fixes work

Start by describing what issues you found."""

        response = await self.chat(prompt)
        console.print(f"\n[green]{response}[/green]")

        await self.close()
