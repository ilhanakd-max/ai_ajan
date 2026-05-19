"""Git tools for LocalCoder."""

import asyncio
from pathlib import Path
from typing import Optional

from localcoder.tools.base import SafetyLevel, Tool, ToolResult


class GitStatusTool(Tool):
    """Get git repository status."""

    name = "git_status"
    description = "Show the current git status of the repository."
    safety_level = SafetyLevel.SAFE

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the git repository (default: current directory)",
                },
            },
            "required": [],
        }

    async def execute(self, path: Optional[str] = None) -> ToolResult:
        try:
            repo_path = Path(path) if path else Path.cwd()

            # Check if it's a git repo
            git_dir = repo_path / ".git"
            if not git_dir.exists():
                return ToolResult(
                    success=False, output="", error="Not a git repository"
                )

            process = await asyncio.create_subprocess_exec(
                "git",
                "status",
                "--short",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=repo_path,
            )

            stdout, stderr = await process.communicate()
            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            if process.returncode != 0:
                return ToolResult(
                    success=False,
                    output="",
                    error=stderr_str or f"Exit code: {process.returncode}",
                )

            if not stdout_str.strip():
                output = "Working tree clean"
            else:
                output = f"Git status:\n{stdout_str}"

            return ToolResult(success=True, output=output)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class GitDiffTool(Tool):
    """Show git diff."""

    name = "git_diff"
    description = "Show git diff for changed files."
    safety_level = SafetyLevel.SAFE

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the git repository (default: current directory)",
                },
                "staged": {
                    "type": "boolean",
                    "description": "Show staged changes only",
                },
                "file": {
                    "type": "string",
                    "description": "Show diff for specific file only",
                },
            },
            "required": [],
        }

    async def execute(
        self,
        path: Optional[str] = None,
        staged: bool = False,
        file: Optional[str] = None,
    ) -> ToolResult:
        try:
            repo_path = Path(path) if path else Path.cwd()

            args = ["git", "diff"]
            if staged:
                args.append("--cached")
            if file:
                args.append("--")
                args.append(file)

            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=repo_path,
            )

            stdout, stderr = await process.communicate()
            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            if process.returncode != 0:
                return ToolResult(
                    success=False,
                    output="",
                    error=stderr_str or f"Exit code: {process.returncode}",
                )

            if not stdout_str.strip():
                output = "No changes"
            else:
                output = stdout_str

            return ToolResult(success=True, output=output)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class GitCommitTool(Tool):
    """Create a git commit."""

    name = "git_commit"
    description = "Create a git commit with the specified message."
    safety_level = SafetyLevel.WORKSPACE

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Commit message",
                },
                "path": {
                    "type": "string",
                    "description": "Path to the git repository (default: current directory)",
                },
                "all": {
                    "type": "boolean",
                    "description": "Stage all changes before committing",
                },
            },
            "required": ["message"],
        }

    async def execute(
        self, message: str, path: Optional[str] = None, all_flag: bool = False
    ) -> ToolResult:
        try:
            repo_path = Path(path) if path else Path.cwd()

            # Check if it's a git repo
            git_dir = repo_path / ".git"
            if not git_dir.exists():
                return ToolResult(
                    success=False, output="", error="Not a git repository"
                )

            # Stage all changes if requested
            if all_flag:
                stage_process = await asyncio.create_subprocess_exec(
                    "git",
                    "add",
                    "-A",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=repo_path,
                )
                _, stderr = await stage_process.communicate()
                if stage_process.returncode != 0:
                    return ToolResult(
                        success=False,
                        output="",
                        error=stderr.decode("utf-8", errors="replace"),
                    )

            # Create commit
            process = await asyncio.create_subprocess_exec(
                "git",
                "commit",
                "-m",
                message,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=repo_path,
            )

            stdout, stderr = await process.communicate()
            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            if process.returncode != 0:
                return ToolResult(
                    success=False,
                    output="",
                    error=stderr_str or f"Exit code: {process.returncode}",
                )

            output = f"Commit created:\n{stdout_str}" if stdout_str else "Commit created successfully"
            return ToolResult(success=True, output=output)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
