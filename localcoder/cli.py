"""Main CLI application for LocalCoder."""

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from localcoder import __version__
from localcoder.config.manager import get_settings
from localcoder.providers.ollama import OllamaProvider
from localcoder.utils.rich import create_rich_console

app = typer.Typer(
    name="localcoder",
    help="A terminal-based AI coding assistant powered by local Ollama models.",
    add_completion=False,
)

console = create_rich_console()


@app.command()
def version() -> None:
    """Show version information."""
    console.print(f"[bold blue]LocalCoder[/bold blue] v{__version__}")


@app.command()
def chat(
    project_root: Optional[Path] = typer.Option(
        None, "-p", "--project", help="Project root directory"
    ),
    model: Optional[str] = typer.Option(None, "-m", "--model", help="Model to use"),
) -> None:
    """Start an interactive chat session."""
    from localcoder.agent.interactive import InteractiveAgent

    root = project_root or Path.cwd()
    settings = get_settings(root)

    if model:
        settings.default_model = model

    console.print(Panel("[bold blue]Starting LocalCoder Chat[/bold blue]"))
    console.print(f"Project: [green]{root}[/green]")
    console.print(f"Model: [cyan]{settings.default_model}[/cyan]")

    agent = InteractiveAgent(settings=settings, project_root=root)
    asyncio.run(agent.run())


@app.command()
def ask(
    question: str,
    project_root: Optional[Path] = typer.Option(
        None, "-p", "--project", help="Project root directory"
    ),
    model: Optional[str] = typer.Option(None, "-m", "--model", help="Model to use"),
) -> None:
    """Ask a question about the codebase."""
    from localcoder.agent.simple import SimpleAgent

    root = project_root or Path.cwd()
    settings = get_settings(root)

    if model:
        settings.default_model = model

    console.print(f"[bold blue]Question:[/bold blue] {question}")

    agent = SimpleAgent(settings=settings, project_root=root)
    response = asyncio.run(agent.ask(question))
    console.print(f"\n[bold green]Answer:[/bold green]\n{response}")


@app.command()
def code(
    instruction: str,
    project_root: Optional[Path] = typer.Option(
        None, "-p", "--project", help="Project root directory"
    ),
    model: Optional[str] = typer.Option(None, "-m", "--model", help="Model to use"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be done"),
) -> None:
    """Generate code based on instructions."""
    from localcoder.agent.coding import CodingAgent

    root = project_root or Path.cwd()
    settings = get_settings(root)

    if model:
        settings.default_model = model

    console.print(f"[bold blue]Instruction:[/bold blue] {instruction}")
    if dry_run:
        console.print("[yellow]Dry run mode - no changes will be made[/yellow]")

    agent = CodingAgent(settings=settings, project_root=root, dry_run=dry_run)
    asyncio.run(agent.execute(instruction))


@app.command()
def edit(
    file_path: str,
    instruction: str,
    project_root: Optional[Path] = typer.Option(
        None, "-p", "--project", help="Project root directory"
    ),
    model: Optional[str] = typer.Option(None, "-m", "--model", help="Model to use"),
) -> None:
    """Edit a file based on instructions."""
    from localcoder.agent.editing import EditingAgent

    root = project_root or Path.cwd()
    settings = get_settings(root)

    if model:
        settings.default_model = model

    console.print(f"[bold blue]Editing:[/bold blue] {file_path}")
    console.print(f"[bold blue]Instruction:[/bold blue] {instruction}")

    agent = EditingAgent(settings=settings, project_root=root)
    asyncio.run(agent.edit(file_path, instruction))


@app.command()
def run(
    command: str,
    project_root: Optional[Path] = typer.Option(
        None, "-p", "--project", help="Project root directory"
    ),
) -> None:
    """Run a shell command in the project context."""
    from localcoder.tools.shell import RunShellTool

    root = project_root or Path.cwd()
    tool = RunShellTool(workspace_root=root)

    console.print(f"[bold blue]Running:[/bold blue] {command}")

    result = asyncio.run(tool.execute(command))
    if result.success:
        console.print(f"[green]{result.output}[/green]")
    else:
        console.print(f"[red]{result.error}[/red]")


@app.command()
def test(
    project_root: Optional[Path] = typer.Option(
        None, "-p", "--project", help="Project root directory"
    ),
) -> None:
    """Run tests in the project."""
    from localcoder.tools.shell import RunShellTool

    root = project_root or Path.cwd()

    # Detect test framework and run appropriate command
    test_commands = [
        "pytest -v",
        "python -m pytest -v",
        "npm test",
        "cargo test",
        "go test ./...",
    ]

    console.print("[bold blue]Running tests...[/bold blue]")

    for cmd in test_commands:
        tool = RunShellTool(workspace_root=root)
        result = asyncio.run(tool.execute(cmd))
        if result.success or "no tests ran" not in result.output.lower():
            if result.success:
                console.print(f"[green]{result.output}[/green]")
            else:
                console.print(f"[yellow]{result.output}[/yellow]")
                if result.error:
                    console.print(f"[red]{result.error}[/red]")
            break
    else:
        console.print("[yellow]No test framework detected[/yellow]")


@app.command()
def fix(
    project_root: Optional[Path] = typer.Option(
        None, "-p", "--project", help="Project root directory"
    ),
    model: Optional[str] = typer.Option(None, "-m", "--model", help="Model to use"),
) -> None:
    """Automatically fix issues in the codebase."""
    from localcoder.agent.fixing import FixingAgent

    root = project_root or Path.cwd()
    settings = get_settings(root)

    if model:
        settings.default_model = model

    console.print("[bold blue]Analyzing and fixing issues...[/bold blue]")

    agent = FixingAgent(settings=settings, project_root=root)
    asyncio.run(agent.fix())


@app.command()
def commit(
    message: Optional[str] = typer.Option(
        None, "-m", "--message", help="Commit message"
    ),
    project_root: Optional[Path] = typer.Option(
        None, "-p", "--project", help="Project root directory"
    ),
    model: Optional[str] = typer.Option(None, "-m", "--model", help="Model to use"),
) -> None:
    """Create a git commit, optionally with AI-generated message."""
    from localcoder.agent.git_ops import GitAgent

    root = project_root or Path.cwd()
    settings = get_settings(root)

    if model:
        settings.default_model = model

    agent = GitAgent(settings=settings, project_root=root)
    asyncio.run(agent.commit(message))


@app.command()
def memory_add(
    note: str,
    category: str = typer.Option("general", "-c", "--category", help="Memory category"),
    project_root: Optional[Path] = typer.Option(
        None, "-p", "--project", help="Project root directory"
    ),
) -> None:
    """Add a note to project memory."""
    from localcoder.memory.store import MemoryStore

    root = project_root or Path.cwd()
    settings = get_settings(root)

    db_path = settings.get_memory_db_path(root)
    store = MemoryStore(db_path)

    from localcoder.memory.store import MemoryEntry

    entry = MemoryEntry.new(content=note, category=category, project_root=str(root))
    entry = store.add(entry)

    console.print(f"[green]Memory added (ID: {entry.id})[/green]")
    store.close()


@app.command()
def memory_search(
    query: str,
    project_root: Optional[Path] = typer.Option(
        None, "-p", "--project", help="Project root directory"
    ),
) -> None:
    """Search project memory."""
    from localcoder.memory.store import MemoryStore

    root = project_root or Path.cwd()
    settings = get_settings(root)

    db_path = settings.get_memory_db_path(root)
    store = MemoryStore(db_path)

    results = store.search(query, project_root=str(root))

    if results:
        console.print(f"[bold blue]Found {len(results)} memories:[/bold blue]\n")
        for entry in results:
            console.print(f"[green]([{entry.category}])[/green] {entry.content}")
            console.print(f"  [dim]Created: {entry.created_at}[/dim]\n")
    else:
        console.print("[yellow]No memories found[/yellow]")

    store.close()


@app.command()
def config(
    show: bool = typer.Option(False, "--show", help="Show current configuration"),
    edit: bool = typer.Option(False, "--edit", help="Edit configuration"),
    project_root: Optional[Path] = typer.Option(
        None, "-p", "--project", help="Project root directory"
    ),
) -> None:
    """Manage LocalCoder configuration."""
    root = project_root or Path.cwd()
    settings = get_settings(root)

    if show:
        console.print("[bold blue]Current Configuration:[/bold blue]\n")
        config_dict = settings.model_dump()
        for key, value in config_dict.items():
            console.print(f"  [cyan]{key}[/cyan]: {value}")
    elif edit:
        console.print("[yellow]Opening config file for editing...[/yellow]")
        import subprocess

        config_file = root / ".localcoder" / "config.toml"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        if not config_file.exists():
            config_file.write_text("# LocalCoder configuration\n")
        subprocess.run(["nano", str(config_file)])
    else:
        console.print("Use --show to view config or --edit to modify it.")


@app.command()
def models(
    ollama_url: Optional[str] = typer.Option(
        None, "--url", help="Ollama API URL"
    ),
) -> None:
    """List available Ollama models."""
    settings = get_settings()
    url = ollama_url or settings.ollama_url

    provider = OllamaProvider(base_url=url)

    async def list_models():
        if not await provider.check_health():
            console.print("[red]Cannot connect to Ollama server[/red]")
            console.print(f"URL: {url}")
            return

        models = await provider.list_models()
        if models:
            console.print("[bold blue]Available models:[/bold blue]\n")
            for model in models:
                name = model.get("name", "unknown")
                size = model.get("size", 0) / (1024**3)  # Convert to GB
                console.print(f"  [cyan]{name}[/cyan] ({size:.2f} GB)")
        else:
            console.print("[yellow]No models found[/yellow]")

        await provider.close()

    asyncio.run(list_models())


@app.command()
def doctor() -> None:
    """Check system health and configuration."""
    console.print("[bold blue]LocalCoder Health Check[/bold blue]\n")

    checks_passed = 0
    total_checks = 0

    # Check Python version
    total_checks += 1
    import sys

    if sys.version_info >= (3, 12):
        console.print("[green]✓[/green] Python version: OK")
        checks_passed += 1
    else:
        console.print("[red]✗[/red] Python version: Requires 3.12+")

    # Check Ollama
    total_checks += 1
    provider = OllamaProvider()

    async def check_ollama():
        if await provider.check_health():
            console.print("[green]✓[/green] Ollama server: Running")
            await provider.close()
            return True
        else:
            console.print("[red]✗[/red] Ollama server: Not running")
            console.print("  Start with: ollama serve")
            await provider.close()
            return False

    if asyncio.run(check_ollama()):
        checks_passed += 1

    # Check workspace
    total_checks += 1
    workspace = Path.cwd()
    if workspace.exists():
        console.print(f"[green]✓[/green] Workspace: {workspace}")
        checks_passed += 1
    else:
        console.print(f"[red]✗[/red] Workspace: {workspace} not found")

    # Summary
    console.print(f"\n[bold]Result: {checks_passed}/{total_checks} checks passed[/bold]")

    if checks_passed == total_checks:
        console.print("[green]All systems operational![/green]")
    else:
        console.print("[yellow]Some issues detected. Please review above.[/yellow]")


@app.command()
def init(
    project_root: Optional[Path] = typer.Option(
        None, "-p", "--project", help="Project root directory"
    ),
) -> None:
    """Initialize LocalCoder for a project."""
    root = project_root or Path.cwd()

    console.print(f"[bold blue]Initializing LocalCoder for:[/bold blue] {root}\n")

    # Create .localcoder directory
    localcoder_dir = root / ".localcoder"
    localcoder_dir.mkdir(exist_ok=True)

    # Create config file
    config_file = localcoder_dir / "config.toml"
    if not config_file.exists():
        from localcoder.config.settings import Settings
        from localcoder.config.manager import ConfigManager

        settings = Settings.default()
        settings.workspace_root = root
        manager = ConfigManager()
        manager.save_project_config(settings, root)
        console.print(f"[green]✓[/green] Created config file: {config_file}")
    else:
        console.print(f"[yellow]![/yellow] Config already exists: {config_file}")

    # Create skills directory
    skills_dir = localcoder_dir / "skills"
    skills_dir.mkdir(exist_ok=True)
    console.print(f"[green]✓[/green] Created skills directory: {skills_dir}")

    # Create AGENTS.md template
    agents_file = root / "AGENTS.md"
    if not agents_file.exists():
        agents_file.write_text("""# Agent Instructions

This file contains instructions for AI coding assistants.

## Project Overview

TODO: Describe your project

## Coding Standards

TODO: Define your coding standards

## Common Commands

TODO: List common development commands

## Architecture Notes

TODO: Document architecture decisions
""")
        console.print(f"[green]✓[/green] Created AGENTS.md template")

    console.print("\n[green]LocalCoder initialized successfully![/green]")
    console.print("\nNext steps:")
    console.print("  1. Edit AGENTS.md with project-specific instructions")
    console.print("  2. Run 'localcoder chat' to start coding")


@app.command()
def undo(
    project_root: Optional[Path] = typer.Option(
        None, "-p", "--project", help="Project root directory"
    ),
) -> None:
    """Undo the last change."""
    console.print("[yellow]Undo functionality coming soon[/yellow]")
    console.print("For now, use git to revert changes:")
    console.print("  git checkout HEAD -- <file>")
    console.print("  git reset --hard HEAD~1")


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
