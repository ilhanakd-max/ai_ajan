"""Tests for tools module."""

import pytest
from pathlib import Path
import tempfile
import os

from localcoder.tools.filesystem import (
    ReadFileTool,
    WriteFileTool,
    EditFileTool,
    ListFilesTool,
    DeleteFileTool,
)
from localcoder.tools.base import ToolResult, SafetyLevel


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestReadFileTool:
    """Test ReadFileTool."""

    async def test_read_existing_file(self, temp_dir):
        """Test reading an existing file."""
        # Create test file
        test_file = temp_dir / "test.txt"
        test_file.write_text("Hello, World!")

        tool = ReadFileTool()
        result = await tool.execute(path=str(test_file))

        assert result.success is True
        assert result.output == "Hello, World!"

    async def test_read_nonexistent_file(self):
        """Test reading a nonexistent file."""
        tool = ReadFileTool()
        result = await tool.execute(path="/nonexistent/file.txt")

        assert result.success is False
        assert "not found" in result.error.lower()

    async def test_read_with_limit(self, temp_dir):
        """Test reading file with line limit."""
        test_file = temp_dir / "multiline.txt"
        test_file.write_text("\n".join([f"Line {i}" for i in range(10)]))

        tool = ReadFileTool()
        result = await tool.execute(path=str(test_file), limit=3)

        assert result.success is True
        assert "Line 0" in result.output
        assert "more lines" in result.output


class TestWriteFileTool:
    """Test WriteFileTool."""

    async def test_write_new_file(self, temp_dir):
        """Test writing a new file."""
        test_file = temp_dir / "new_file.txt"

        tool = WriteFileTool()
        result = await tool.execute(path=str(test_file), content="New content")

        assert result.success is True
        assert test_file.exists()
        assert test_file.read_text() == "New content"

    async def test_write_creates_directories(self, temp_dir):
        """Test that write creates parent directories."""
        test_file = temp_dir / "subdir" / "nested" / "file.txt"

        tool = WriteFileTool()
        result = await tool.execute(path=str(test_file), content="Nested content")

        assert result.success is True
        assert test_file.exists()


class TestEditFileTool:
    """Test EditFileTool."""

    async def test_edit_file(self, temp_dir):
        """Test editing a file."""
        test_file = temp_dir / "edit_me.txt"
        test_file.write_text("Hello, World!")

        tool = EditFileTool()
        result = await tool.execute(
            path=str(test_file),
            old_text="World",
            new_text="Universe",
        )

        assert result.success is True
        assert test_file.read_text() == "Hello, Universe!"

    async def test_edit_not_found(self, temp_dir):
        """Test editing when search text not found."""
        test_file = temp_dir / "edit_me.txt"
        test_file.write_text("Hello, World!")

        tool = EditFileTool()
        result = await tool.execute(
            path=str(test_file),
            old_text="Nonexistent",
            new_text="Something",
        )

        assert result.success is False
        assert "not found" in result.error.lower()


class TestListFilesTool:
    """Test ListFilesTool."""

    async def test_list_empty_directory(self, temp_dir):
        """Test listing an empty directory."""
        tool = ListFilesTool()
        result = await tool.execute(path=str(temp_dir))

        assert result.success is True
        assert "empty" in result.output.lower() or result.output.strip() == ""

    async def test_list_directory_with_files(self, temp_dir):
        """Test listing a directory with files."""
        (temp_dir / "file1.txt").write_text("content1")
        (temp_dir / "file2.txt").write_text("content2")

        tool = ListFilesTool()
        result = await tool.execute(path=str(temp_dir))

        assert result.success is True
        assert "file1.txt" in result.output
        assert "file2.txt" in result.output


class TestDeleteFileTool:
    """Test DeleteFileTool."""

    async def test_delete_file(self, temp_dir):
        """Test deleting a file."""
        test_file = temp_dir / "delete_me.txt"
        test_file.write_text("To be deleted")

        tool = DeleteFileTool()
        result = await tool.execute(path=str(test_file))

        assert result.success is True
        assert not test_file.exists()

    async def test_delete_nonexistent_file(self, temp_dir):
        """Test deleting a nonexistent file."""
        tool = DeleteFileTool()
        result = await tool.execute(path=str(temp_dir / "nonexistent.txt"))

        assert result.success is False
        assert "not found" in result.error.lower()
