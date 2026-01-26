# Agent Instructions

## Commit Attribution

AI-generated commits MUST include:
```
Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

## Setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.in -e .
```

## Running Tests

```bash
source .venv/bin/activate
pytest tests/
```

Or with tox: `tox -e py311`

## Code Style

- Python 3.11+
- Black formatter, 80 char line length
- Strict mypy/pyright typing
- Run `black .` and `mypy .` before committing

## Project Structure

- `devenv/` - Main package
- `devenv/lib/` - Library modules (docker, colima, brew, etc.)
- `devenv/checks/` - Health checks for `devenv doctor`
- `tests/` - Test files mirror the main package structure

## Platform Support

- macOS (Darwin): Full support with Colima/Docker
- Linux (Ubuntu 24.04+): Detection only, prints install commands for user
- Use `constants.DARWIN` / `constants.LINUX` for platform checks
