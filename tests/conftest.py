from __future__ import annotations

import os
import shutil
import tempfile

import pytest

_home = tempfile.mkdtemp(prefix="devenv-tests-home-")


def pytest_configure(config: pytest.Config) -> None:
    os.environ["CI"] = "1"
    os.environ["SHELL"] = "/bin/bash"
    os.environ["SENTRY_FORCE_PY"] = "1"
    # With CI set, devenv takes its home from $HOME, and some tests run
    # real devenv commands. Without this they'd install tools into the
    # developer's own ~/.local/share/sentry-devenv and edit their dotfiles.
    os.environ["HOME"] = _home


def pytest_unconfigure(config: pytest.Config) -> None:
    shutil.rmtree(_home, ignore_errors=True)
