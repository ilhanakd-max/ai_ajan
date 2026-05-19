# LocalCoder

A terminal-based AI coding assistant powered by local Ollama models and Needle skill routing.

## Features

- **Local Execution**: Runs entirely on your computer using Ollama models
- **Skill-Based Architecture**: Modular skills powered by Needle routing engine
- **Autonomous Agent**: Multi-step reasoning and task execution
- **Safe Shell Execution**: Permission-based command execution
- **Git Integration**: Commit, diff, and version control support
- **Persistent Memory**: SQLite-backed project memory
- **Rich CLI**: Interactive chat with streaming responses

## Installation

```bash
pip install -e .
```

## Quick Start

```bash
# Start interactive chat
localcoder chat

# Ask a question
localcoder ask "Explain this codebase"

# Generate code
localcoder code "Create a Flask REST API"

# Edit a file
localcoder edit app.py "Add JWT authentication"

# Run tests
localcoder test

# Fix issues
localcoder fix

# Commit changes
localcoder commit
```

## Requirements

- Python 3.12+
- Ollama installed and running
- Linux (tested on Linux Mint)

## Documentation

See the `docs/` directory for detailed documentation:

- [Installation Guide](docs/INSTALL.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Skills System](docs/SKILLS.md)
- [Configuration](docs/CONFIGURATION.md)
- [Examples](docs/EXAMPLES.md)

## License

MIT License