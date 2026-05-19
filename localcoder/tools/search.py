"""Search tools for LocalCoder."""

import os
from pathlib import Path
from typing import Optional

from localcoder.tools.base import SafetyLevel, Tool, ToolResult


class SearchTextTool(Tool):
    """Search for text in files."""

    name = "search_text"
    description = "Search for a text pattern in files within a directory."
    safety_level = SafetyLevel.SAFE

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Text pattern to search for",
                },
                "path": {
                    "type": "string",
                    "description": "Directory to search in (default: current directory)",
                },
                "include": {
                    "type": "string",
                    "description": "Glob pattern for files to include (e.g., '*.py')",
                },
                "exclude": {
                    "type": "string",
                    "description": "Glob pattern for files to exclude (e.g., '*.log')",
                },
                "case_sensitive": {
                    "type": "boolean",
                    "description": "Whether search is case-sensitive",
                },
            },
            "required": ["pattern"],
        }

    async def execute(
        self,
        pattern: str,
        path: Optional[str] = None,
        include: Optional[str] = None,
        exclude: Optional[str] = None,
        case_sensitive: bool = False,
    ) -> ToolResult:
        try:
            import fnmatch

            search_dir = Path(path) if path else Path.cwd()
            if not search_dir.exists():
                return ToolResult(success=False, output="", error=f"Directory not found: {path}")

            results = []
            count = 0

            for root, dirs, files in os.walk(search_dir):
                # Skip hidden directories
                dirs[:] = [d for d in dirs if not d.startswith(".")]

                for filename in files:
                    # Check include pattern
                    if include and not fnmatch.fnmatch(filename, include):
                        continue
                    # Check exclude pattern
                    if exclude and fnmatch.fnmatch(filename, exclude):
                        continue

                    filepath = Path(root) / filename
                    try:
                        content = filepath.read_text(encoding="utf-8", errors="ignore")
                        lines = content.splitlines()

                        for line_num, line in enumerate(lines, 1):
                            search_line = line if case_sensitive else line.lower()
                            search_pattern = (
                                pattern if case_sensitive else pattern.lower()
                            )

                            if search_pattern in search_line:
                                rel_path = filepath.relative_to(search_dir)
                                results.append(f"{rel_path}:{line_num}: {line.rstrip()}")
                                count += 1

                                # Limit results
                                if count >= 100:
                                    break
                    except Exception:
                        continue

                if count >= 100:
                    break

            if not results:
                return ToolResult(
                    success=True, output=f"No matches found for '{pattern}'", data={"count": 0}
                )

            output = f"Found {count} matches for '{pattern}':\n" + "\n".join(results)
            if count >= 100:
                output += "\n... (results truncated)"

            return ToolResult(success=True, output=output, data={"count": count, "results": results})
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class GrepCodeTool(Tool):
    """Grep-like code search with regex support."""

    name = "grep_code"
    description = "Search for a regex pattern in code files."
    safety_level = SafetyLevel.SAFE

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Regex pattern to search for",
                },
                "path": {
                    "type": "string",
                    "description": "Directory to search in (default: current directory)",
                },
                "file_pattern": {
                    "type": "string",
                    "description": "File pattern to match (e.g., '*.py')",
                },
                "context_lines": {
                    "type": "integer",
                    "description": "Number of context lines to show",
                },
            },
            "required": ["pattern"],
        }

    async def execute(
        self,
        pattern: str,
        path: Optional[str] = None,
        file_pattern: Optional[str] = None,
        context_lines: int = 0,
    ) -> ToolResult:
        try:
            import fnmatch
            import re

            search_dir = Path(path) if path else Path.cwd()
            if not search_dir.exists():
                return ToolResult(success=False, output="", error=f"Directory not found: {path}")

            try:
                regex = re.compile(pattern)
            except re.error as e:
                return ToolResult(success=False, output="", error=f"Invalid regex: {e}")

            results = []
            count = 0

            for root, dirs, files in os.walk(search_dir):
                # Skip hidden directories
                dirs[:] = [d for d in dirs if not d.startswith(".")]

                for filename in files:
                    # Check file pattern
                    if file_pattern and not fnmatch.fnmatch(filename, file_pattern):
                        continue

                    filepath = Path(root) / filename
                    try:
                        content = filepath.read_text(encoding="utf-8", errors="ignore")
                        lines = content.splitlines()

                        for line_num, line in enumerate(lines, 1):
                            if regex.search(line):
                                rel_path = filepath.relative_to(search_dir)

                                # Add context if requested
                                if context_lines > 0:
                                    start = max(0, line_num - 1 - context_lines)
                                    end = min(len(lines), line_num + context_lines)
                                    context = lines[start:end]
                                    context_output = "\n".join(
                                        f"  {start + i + 1}: {l}"
                                        for i, l in enumerate(context)
                                    )
                                    results.append(
                                        f"\n{rel_path}:{line_num}: {line.rstrip()}\n{context_output}"
                                    )
                                else:
                                    results.append(f"{rel_path}:{line_num}: {line.rstrip()}")
                                count += 1

                                # Limit results
                                if count >= 100:
                                    break
                    except Exception:
                        continue

                if count >= 100:
                    break

            if not results:
                return ToolResult(
                    success=True, output=f"No matches found for pattern '{pattern}'", data={"count": 0}
                )

            output = f"Found {count} matches for pattern '{pattern}':" + "\n".join(results)
            if count >= 100:
                output += "\n... (results truncated)"

            return ToolResult(success=True, output=output, data={"count": count, "results": results})
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
