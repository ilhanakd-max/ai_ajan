"""Filesystem tools for LocalCoder."""

import os
import shutil
from pathlib import Path
from typing import Optional

from localcoder.tools.base import SafetyLevel, Tool, ToolResult


class ReadFileTool(Tool):
    """Read contents of a file."""

    name = "read_file"
    description = "Read the contents of a file at the specified path."
    safety_level = SafetyLevel.SAFE

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to read",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of lines to read (optional)",
                },
            },
            "required": ["path"],
        }

    async def execute(self, path: str, limit: Optional[int] = None) -> ToolResult:
        try:
            file_path = Path(path)
            if not file_path.exists():
                return ToolResult(success=False, output="", error=f"File not found: {path}")
            if not file_path.is_file():
                return ToolResult(success=False, output="", error=f"Not a file: {path}")

            content = file_path.read_text(encoding="utf-8")
            lines = content.splitlines()

            if limit and len(lines) > limit:
                content = "\n".join(lines[:limit])
                content += f"\n... ({len(lines) - limit} more lines)"

            return ToolResult(success=True, output=content, data={"path": str(file_path)})
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class WriteFileTool(Tool):
    """Write contents to a file."""

    name = "write_file"
    description = "Write content to a file at the specified path. Creates the file if it doesn't exist."
    safety_level = SafetyLevel.WORKSPACE

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to write",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file",
                },
            },
            "required": ["path", "content"],
        }

    async def execute(self, path: str, content: str) -> ToolResult:
        try:
            file_path = Path(path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            return ToolResult(
                success=True,
                output=f"Successfully wrote {len(content)} characters to {path}",
                data={"path": str(file_path), "size": len(content)},
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class EditFileTool(Tool):
    """Edit a file by applying changes."""

    name = "edit_file"
    description = "Edit a file by specifying the search and replace strings."
    safety_level = SafetyLevel.WORKSPACE

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to edit",
                },
                "old_text": {
                    "type": "string",
                    "description": "Text to search for",
                },
                "new_text": {
                    "type": "string",
                    "description": "Text to replace with",
                },
            },
            "required": ["path", "old_text", "new_text"],
        }

    async def execute(self, path: str, old_text: str, new_text: str) -> ToolResult:
        try:
            file_path = Path(path)
            if not file_path.exists():
                return ToolResult(success=False, output="", error=f"File not found: {path}")

            content = file_path.read_text(encoding="utf-8")
            if old_text not in content:
                return ToolResult(
                    success=False, output="", error="Search text not found in file"
                )

            new_content = content.replace(old_text, new_text, 1)
            file_path.write_text(new_content, encoding="utf-8")

            return ToolResult(
                success=True,
                output=f"Successfully edited {path}",
                data={"path": str(file_path)},
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class ListFilesTool(Tool):
    """List files in a directory."""

    name = "list_files"
    description = "List files and directories in the specified path."
    safety_level = SafetyLevel.SAFE

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the directory to list",
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Whether to list recursively",
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum depth for recursive listing",
                },
            },
            "required": ["path"],
        }

    async def execute(
        self, path: str, recursive: bool = False, max_depth: Optional[int] = None
    ) -> ToolResult:
        try:
            dir_path = Path(path)
            if not dir_path.exists():
                return ToolResult(success=False, output="", error=f"Path not found: {path}")
            if not dir_path.is_dir():
                return ToolResult(success=False, output="", error=f"Not a directory: {path}")

            entries = []
            if recursive:
                current_depth = 0
                for item in dir_path.rglob("*"):
                    if max_depth is not None:
                        depth = len(item.relative_to(dir_path).parts)
                        if depth > max_depth:
                            continue
                    rel_path = item.relative_to(dir_path)
                    entry_type = "dir" if item.is_dir() else "file"
                    entries.append(f"{entry_type}: {rel_path}")
            else:
                for item in sorted(dir_path.iterdir()):
                    entry_type = "dir" if item.is_dir() else "file"
                    entries.append(f"{entry_type}: {item.name}")

            output = "\n".join(entries) if entries else "(empty directory)"
            return ToolResult(success=True, output=output, data={"entries": entries})
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class DeleteFileTool(Tool):
    """Delete a file or directory."""

    name = "delete_file"
    description = "Delete a file or empty directory at the specified path."
    safety_level = SafetyLevel.DANGEROUS

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file or directory to delete",
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Whether to delete non-empty directories recursively",
                },
            },
            "required": ["path"],
        }

    async def execute(self, path: str, recursive: bool = False) -> ToolResult:
        try:
            file_path = Path(path)
            if not file_path.exists():
                return ToolResult(success=False, output="", error=f"Path not found: {path}")

            if file_path.is_file():
                file_path.unlink()
                return ToolResult(success=True, output=f"Deleted file: {path}")
            elif file_path.is_dir():
                if recursive:
                    shutil.rmtree(file_path)
                    return ToolResult(success=True, output=f"Deleted directory: {path}")
                else:
                    try:
                        file_path.rmdir()
                        return ToolResult(success=True, output=f"Deleted empty directory: {path}")
                    except OSError:
                        return ToolResult(
                            success=False,
                            output="",
                            error="Directory not empty. Use recursive=true to delete non-empty directories.",
                        )

            return ToolResult(success=False, output="", error=f"Cannot delete: {path}")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class RenameFileTool(Tool):
    """Rename a file or directory."""

    name = "rename_file"
    description = "Rename a file or directory."
    safety_level = SafetyLevel.WORKSPACE

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Current path of the file or directory",
                },
                "destination": {
                    "type": "string",
                    "description": "New path for the file or directory",
                },
            },
            "required": ["source", "destination"],
        }

    async def execute(self, source: str, destination: str) -> ToolResult:
        try:
            source_path = Path(source)
            dest_path = Path(destination)

            if not source_path.exists():
                return ToolResult(success=False, output="", error=f"Source not found: {source}")

            dest_path.parent.mkdir(parents=True, exist_ok=True)
            source_path.rename(dest_path)

            return ToolResult(
                success=True,
                output=f"Renamed {source} to {destination}",
                data={"source": str(source_path), "destination": str(dest_path)},
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class CreateDirectoryTool(Tool):
    """Create a directory."""

    name = "create_directory"
    description = "Create a directory at the specified path."
    safety_level = SafetyLevel.WORKSPACE

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the directory to create",
                },
                "parents": {
                    "type": "boolean",
                    "description": "Create parent directories if needed",
                },
            },
            "required": ["path"],
        }

    async def execute(self, path: str, parents: bool = True) -> ToolResult:
        try:
            dir_path = Path(path)
            dir_path.mkdir(parents=parents, exist_ok=True)
            return ToolResult(
                success=True,
                output=f"Created directory: {path}",
                data={"path": str(dir_path)},
            )
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
