"""Shell execution tools for LocalCoder."""

import asyncio
import os
from pathlib import Path
from typing import Optional

from localcoder.tools.base import SafetyLevel, Tool, ToolResult


class RunShellTool(Tool):
    """Execute shell commands."""

    name = "run_shell"
    description = "Execute a shell command in the workspace directory."
    safety_level = SafetyLevel.DANGEROUS

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute",
                },
                "cwd": {
                    "type": "string",
                    "description": "Working directory for the command (optional)",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default: 60)",
                },
            },
            "required": ["command"],
        }

    def __init__(self, workspace_root: Optional[Path] = None):
        self.workspace_root = workspace_root or Path.cwd()

    def _is_dangerous_command(self, command: str) -> bool:
        """Check if command is potentially dangerous."""
        dangerous_patterns = [
            "rm -rf /",
            "rm -rf ~",
            "sudo rm",
            "mkfs",
            "dd if=",
            "> /dev/",
            "chmod -R 777 /",
            "chown -R root /",
            ":(){ :|:& };:",
            "wget.*\\|.*sh",
            "curl.*\\|.*sh",
        ]
        command_lower = command.lower()
        for pattern in dangerous_patterns:
            if pattern in command_lower:
                return True
        return False

    async def execute(
        self, command: str, cwd: Optional[str] = None, timeout: int = 60
    ) -> ToolResult:
        try:
            # Check for dangerous commands
            if self._is_dangerous_command(command):
                return ToolResult(
                    success=False,
                    output="",
                    error="Command contains dangerous patterns and was blocked for safety.",
                )

            # Determine working directory
            work_dir = Path(cwd) if cwd else self.workspace_root
            if not work_dir.exists():
                return ToolResult(success=False, output="", error=f"Directory not found: {work_dir}")

            # Execute command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=work_dir,
                env={**os.environ, "PWD": str(work_dir)},
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Command timed out after {timeout} seconds",
                )

            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            output = stdout_str
            if stderr_str:
                output += f"\nSTDERR:\n{stderr_str}" if output else stderr_str

            success = process.returncode == 0

            return ToolResult(
                success=success,
                output=output.strip() if output else "(no output)",
                error=None if success else f"Exit code: {process.returncode}",
                data={
                    "returncode": process.returncode,
                    "stdout": stdout_str,
                    "stderr": stderr_str,
                },
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
