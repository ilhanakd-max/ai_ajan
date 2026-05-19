"""Autonomous agent with Needle-based tool execution for LocalCoder.

This module implements the core autonomous agent that:
1. Uses Needle to route requests to skills and tools
2. Executes tools automatically without user intervention
3. Follows a ReAct-style loop for multi-step tasks
4. Verifies results and reports completion
"""

import asyncio
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel

from localcoder.agent.base import BaseAgent
from localcoder.agent.router import ExecutionPlan, NeedleRouter, SkillRegistry, ToolCall
from localcoder.config.settings import Settings
from localcoder.models.message import Message, MessageRole
from localcoder.providers.ollama import OllamaMessage, OllamaProvider
from localcoder.tools.base import Tool
from localcoder.utils.rich import create_rich_console


class AutonomousAgent(BaseAgent):
    """
    Autonomous coding agent that executes tasks using Needle-based routing.

    This agent differs from base agents by:
    - Automatically executing tools when available
    - Never instructing users to perform actions it can do itself
    - Using a ReAct-style loop for complex tasks
    - Verifying results after each action
    """

    def __init__(
        self,
        settings: Settings,
        project_root: Path,
        console: Optional[Console] = None,
        auto_execute: bool = True,
        explain_only: bool = False,
    ):
        super().__init__(settings, project_root)
        self.console = console or create_rich_console()
        self.auto_execute = auto_execute
        self.explain_only = explain_only
        self._router: Optional[NeedleRouter] = None
        self._skill_registry: Optional[SkillRegistry] = None

    def _get_system_prompt(self) -> str:
        """Get the system prompt emphasizing autonomous execution."""
        return """You are LocalCoder, an AUTONOMOUS coding agent.

CRITICAL RULES:
1. You MUST execute tools directly when they are available for the task.
2. NEVER tell the user how to use terminal commands, editors, or shell utilities.
3. NEVER provide step-by-step instructions for actions you can perform yourself.
4. Your default behavior is ACTION, not INSTRUCTION.

When given a task:
1. Analyze what needs to be done
2. Use available tools to complete the task
3. Verify your work succeeded
4. Report what was accomplished

Only provide explanations when:
- The user explicitly asks for an explanation
- No tool exists to perform the task
- Permission is denied

Complete tasks autonomously whenever possible."""

    def _register_tools(self) -> None:
        """Register all available tools."""
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

    def _init_router(self) -> None:
        """Initialize the Needle router."""
        if self._router is not None:
            return

        # Get skills directory
        skills_dir = self.settings.get_skills_dir(self.project_root)
        self._skill_registry = SkillRegistry(skills_dir)

        # Build tool definitions for router
        tool_defs = [tool.get_tool_definition() for tool in self.get_available_tools()]
        skill_defs = self._skill_registry.get_skills()

        self._router = NeedleRouter(
            settings=self.settings,
            available_tools=tool_defs,
            available_skills=skill_defs,
        )

    async def execute(self, user_request: str) -> str:
        """
        Execute a user request autonomously.

        Args:
            user_request: The user's task/request

        Returns:
            Summary of what was accomplished
        """
        self._init_router()

        # Add user message to conversation
        self.conversation.add_message(Message.user(user_request))

        # Step 1: Use Needle to generate execution plan
        self.console.print("\n[bold blue]Analyzing task...[/bold blue]")
        
        context = await self._gather_context()
        plan = await self._router.plan(user_request, context)

        # Display plan
        self._display_plan(plan)

        # Check if we should only explain
        if self.explain_only:
            return self._generate_explanation(plan)

        # Step 2: Execute the plan
        if plan.tools:
            results = await self._execute_plan(plan)
            
            # Step 3: Verify and summarize
            summary = await self._summarize_results(plan, results, user_request)
            
            # Add to conversation
            self.conversation.add_message(Message.assistant(summary))
            
            return summary
        else:
            # No tools needed - get reasoning model response
            response = await self._get_reasoning_response(user_request, context)
            self.conversation.add_message(Message.assistant(response))
            return response

    def _display_plan(self, plan: ExecutionPlan) -> None:
        """Display the execution plan to the user."""
        if plan.skills:
            skill_names = ", ".join(s.name for s in plan.skills)
            self.console.print(f"[cyan]Selected skills:[/cyan] {skill_names}")
        
        if plan.tools:
            tool_names = ", ".join(t.name for t in plan.tools)
            self.console.print(f"[green]Tools to execute:[/green] {tool_names}")
        
        if plan.summary:
            self.console.print(f"[dim]{plan.summary}[/dim]")

    async def _execute_plan(self, plan: ExecutionPlan) -> list[tuple[str, bool, str]]:
        """
        Execute all tools in the plan.

        Returns:
            List of (tool_name, success, output/error) tuples
        """
        results = []

        for tool_call in plan.tools:
            # Check for dangerous operations
            if tool_call.name == "delete_file" and tool_call.arguments.get("recursive"):
                if not self.settings.auto_confirm:
                    self.console.print(
                        f"\n[yellow]Warning: Recursive delete requested for {tool_call.arguments.get('path')}[/yellow]"
                    )
                    # In auto-execute mode, proceed anyway
                    if not self.auto_execute:
                        results.append((tool_call.name, False, "Cancelled by user"))
                        continue

            # Execute the tool
            self.console.print(f"\n[bold]Executing:[/bold] {tool_call.name}...")
            
            try:
                success, output = await self.execute_tool(
                    tool_call.name, **tool_call.arguments
                )
                
                if success:
                    self.console.print(f"[green]✓ {tool_call.name} completed[/green]")
                else:
                    self.console.print(f"[red]✗ {tool_call.name} failed: {output}[/red]")
                
                results.append((tool_call.name, success, output))
                
            except Exception as e:
                error_msg = str(e)
                self.console.print(f"[red]✗ {tool_call.name} error: {error_msg}[/red]")
                results.append((tool_call.name, False, error_msg))

        return results

    async def _summarize_results(
        self,
        plan: ExecutionPlan,
        results: list[tuple[str, bool, str]],
        original_request: str,
    ) -> str:
        """Generate a summary of what was accomplished."""
        successful = sum(1 for _, success, _ in results if success)
        failed = len(results) - successful

        # Build summary parts
        parts = []
        
        if plan.summary:
            parts.append(plan.summary)
        
        if successful > 0:
            parts.append(f"\nSuccessfully executed {successful} tool(s):")
            for name, success, output in results:
                if success:
                    parts.append(f"  • {name}: {output[:100]}")
        
        if failed > 0:
            parts.append(f"\nFailed: {failed} tool(s)")
            for name, success, output in results:
                if not success:
                    parts.append(f"  ✗ {name}: {output[:100]}")

        # Use reasoning model to generate natural summary if needed
        if len(parts) <= 1:
            summary_text = "\n".join(parts) if parts else "Task completed."
            return summary_text

        return "\n".join(parts)

    async def _get_reasoning_response(
        self, user_request: str, context: Optional[str]
    ) -> str:
        """Get a response from the reasoning model when no tools are needed."""
        prompt = user_request
        if context:
            prompt = f"{context}\n\n{user_request}"

        response = await self.provider.chat(
            messages=[OllamaMessage(role="user", content=prompt)],
            system_prompt=self.conversation.system_prompt,
            temperature=self.settings.temperature,
            top_p=self.settings.top_p,
        )

        return response.message.content

    async def _gather_context(self) -> str:
        """Gather context about the project."""
        context_parts = []

        # Check for common project files
        common_files = [
            "README.md",
            "AGENTS.md",
            "LOCALCODER.md",
            ".localcoder/config.toml",
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

        return "\n\n".join(context_parts) if context_parts else ""

    def _generate_explanation(self, plan: ExecutionPlan) -> str:
        """Generate an explanation of what would be done (for explain-only mode)."""
        lines = ["Here's what I would do:"]
        
        if plan.skills:
            lines.append(f"\nSkills: {', '.join(s.name for s in plan.skills)}")
        
        if plan.tools:
            lines.append("\nTools:")
            for tool in plan.tools:
                lines.append(f"  - {tool.name}({tool.arguments})")
        
        if plan.requires_confirmation:
            lines.append("\n⚠️  This operation requires confirmation.")
        
        return "\n".join(lines)

    async def run_loop(
        self,
        user_request: str,
        max_steps: int = 10,
        timeout: float = 300.0,
    ) -> str:
        """
        Run a full ReAct-style agent loop.

        Args:
            user_request: Initial user request
            max_steps: Maximum iterations
            timeout: Timeout in seconds

        Returns:
            Final response
        """
        self._init_router()
        
        current_request = user_request
        step = 0
        all_results = []

        while step < max_steps:
            step += 1
            self.console.print(f"\n[bold cyan]Step {step}/{max_steps}[/bold cyan]")

            # Generate plan
            context = await self._gather_context()
            plan = await self._router.plan(current_request, context)

            # Check if any tools are planned
            if not plan.tools:
                # No more tools needed - generate final response
                final_response = await self._get_reasoning_response(
                    f"Based on these results: {all_results}, provide a final summary for: {user_request}",
                    context,
                )
                return final_response

            # Execute tools
            results = await self._execute_plan(plan)
            all_results.extend(results)

            # Check if all tools succeeded
            all_success = all(success for _, success, _ in results)
            
            if all_success:
                # Task likely complete, generate summary
                summary = await self._summarize_results(plan, results, user_request)
                
                # Ask model if task is complete
                completion_check = await self._check_completion(
                    user_request, all_results, summary
                )
                
                if completion_check.get("complete", False):
                    return completion_check.get("summary", summary)
                
                # Not complete - continue with follow-up
                current_request = completion_check.get("next_step", "Continue the task")
            else:
                # Some tools failed - ask for recovery strategy
                current_request = await self._handle_failures(results, user_request)

        # Max steps reached
        return f"Reached maximum steps ({max_steps}). Current status: {all_results}"

    async def _check_completion(
        self,
        original_request: str,
        results: list,
        summary: str,
    ) -> dict:
        """Check if the task is complete."""
        prompt = f"""Original request: {original_request}

Results so far: {results}

Summary: {summary}

Is the task complete? Respond with JSON:
{{
    "complete": true/false,
    "summary": "Final summary if complete",
    "next_step": "What to do next if not complete"
}}
"""
        response = await self.provider.chat(
            messages=[OllamaMessage(role="user", content=prompt)],
            system_prompt="You are a task completion checker. Respond with valid JSON only.",
            temperature=0.1,
        )

        try:
            import json
            return json.loads(response.message.content)
        except (json.JSONDecodeError, Exception):
            return {"complete": True, "summary": summary}

    async def _handle_failures(
        self,
        results: list,
        original_request: str,
    ) -> str:
        """Handle tool failures and determine recovery strategy."""
        failed_tools = [(name, output) for name, success, output in results if not success]
        
        prompt = f"""Some tools failed during execution:

Failed tools: {failed_tools}

Original request: {original_request}

What should be done next to recover or continue? Provide a brief instruction."""

        response = await self.provider.chat(
            messages=[OllamaMessage(role="user", content=prompt)],
            system_prompt=self.conversation.system_prompt,
            temperature=0.3,
        )

        return response.message.content

    async def close(self) -> None:
        """Clean up resources."""
        await super().close()
        if self._router:
            await self._router.close()
