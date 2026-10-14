# Agent Instructions

## Commit Attribution

AI-generated commits MUST include a `Co-Authored-By:` trailer crediting
the agent and model that actually wrote them, e.g. the attribution your
tooling provides:
```
Co-Authored-By: <agent and model> <email>
```

Don't replace the placeholder above with a specific agent or model: it's
copied verbatim, so any name written here misattributes commits made by
others.

## Setup

```bash
uv sync
```

## Running Tests

```bash
uv run pytest tests/
```

With coverage: `uv run coverage erase && uv run coverage run -m pytest && uv run coverage report`

## Code Style

- Python 3.11+
- Ruff formatter/linter, 80 char line length
- Strict mypy/pyright typing
- Run `ruff check --fix .`, `ruff format .`, and `mypy .` before committing

## Project Structure

- `devenv/` - Main package
- `devenv/lib/` - Library modules (docker, colima, brew, etc.)
- `devenv/checks/` - Health checks for `devenv doctor`
- `tests/` - Test files mirror the main package structure

## Platform Support

- macOS (Darwin): Full support with Colima/Docker
- Linux (Ubuntu 24.04+): Detection only, prints install commands for user
- Use `constants.DARWIN` / `constants.LINUX` for platform checks
