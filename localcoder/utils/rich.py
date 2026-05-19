"""Rich console utilities for LocalCoder."""

from typing import AsyncGenerator, Optional

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax


def create_rich_console() -> Console:
    """Create a configured Rich console."""
    return Console(
        width=None,  # Auto-detect width
        legacy_windows=False,
        force_terminal=True,
        color_system="auto",
    )


def print_streaming(text: str, console: Optional[Console] = None) -> None:
    """Print text with streaming effect."""
    if console is None:
        console = create_rich_console()

    console.print(text, end="")
    console.file.flush()


async def stream_response(
    chunks: AsyncGenerator[str, None],
    console: Optional[Console] = None,
    title: Optional[str] = None,
    markdown: bool = True,
) -> str:
    """Stream and display an async response."""
    if console is None:
        console = create_rich_console()

    full_response = ""
    current_line = ""

    if title:
        console.print(f"\n[bold blue]{title}[/bold blue]")

    async for chunk in chunks:
        full_response += chunk
        current_line += chunk

        if "\n" in current_line:
            lines = current_line.split("\n")
            current_line = lines[-1]
            output = "\n".join(lines[:-1])
            if markdown:
                console.print(Markdown(output), end="")
            else:
                console.print(output, end="")

    if current_line:
        if markdown:
            console.print(Markdown(current_line))
        else:
            console.print(current_line)

    return full_response


def create_code_panel(code: str, language: str = "python", title: Optional[str] = None) -> Panel:
    """Create a panel with syntax-highlighted code."""
    syntax = Syntax(
        code,
        language,
        theme="monokai",
        line_numbers=True,
        word_wrap=False,
    )
    return Panel(syntax, title=title or f"{language} code", border_style="blue")


def create_info_panel(content: str, title: str = "Info") -> Panel:
    """Create an info panel."""
    return Panel(content, title=title, border_style="cyan")


def create_warning_panel(content: str, title: str = "Warning") -> Panel:
    """Create a warning panel."""
    return Panel(content, title=title, border_style="yellow")


def create_error_panel(content: str, title: str = "Error") -> Panel:
    """Create an error panel."""
    return Panel(content, title=title, border_style="red")


def create_success_panel(content: str, title: str = "Success") -> Panel:
    """Create a success panel."""
    return Panel(content, title=title, border_style="green")
