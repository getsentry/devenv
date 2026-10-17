# Agent Instructions

`devenv` (PyPI: `sentry-devenv`) is Sentry's CLI and library for setting up repo dev environments. User docs are in `README.md`, which is also the PyPI long description.

## Commit attribution

AI-generated commits MUST include a `Co-Authored-By:` trailer crediting the agent and model that actually wrote them, such as the attribution your tooling provides:
```
Co-Authored-By: <agent and model> <email>
```

## Commands

- Set up: `uv sync`
- Test: `uv run pytest tests/`
- Test with coverage, as CI runs it: `uv run coverage erase && uv run coverage run -m pytest && uv run coverage report`
- Lint, format, and type-check (ruff, mypy, shellcheck): `uv run pre-commit run --all-files`
- Run your checkout against another repo: `uv run --project ~/code/devenv devenv sync` from that repo's root
- Run the `bootstrap` workflow locally with `gh act`: `make test`

## Invariants

- Python is pinned to 3.11.4 (`requires-python` in `pyproject.toml`, `.python-version`).
- Use `constants.DARWIN` and `constants.LINUX` for platform checks.
- macOS gets the global tools (brew, docker CLI, colima, lima). Linux means apt-based (`dpkg` on PATH). On Linux, devenv installs no global tools, and `devenv bootstrap` exits if docker engine is missing.

## Map

- `devenv/`: one module per subcommand, registered in `devenv/main.py`
- `devenv/lib/`: library modules that repo `sync.py` scripts import
- `devenv/checks/`: builtin `devenv doctor` checks
- `tests/`: mirrors the `devenv/` layout
- `install-devenv.sh`: installer for the global devenv
- `ci/`: scripts for the `bootstrap` and `integration` workflows
- Releases: the `Release` workflow (`.github/workflows/release.yml`) runs craft, which calls `scripts/bump-version.sh`
