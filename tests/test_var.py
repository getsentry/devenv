from __future__ import annotations

import os
from typing import Generator
from unittest.mock import patch

import pytest

from devenv import main


@pytest.fixture
def config_path(
    tmp_path: str, capsys: pytest.CaptureFixture[str]
) -> Generator[str, None, None]:
    config_path = f"{tmp_path}/.config/sentry-devenv/config.ini"
    coderoot = f"{tmp_path}/code"
    with patch("devenv.constants.CI", True):
        main.devenv(
            (
                "/path/to/argv0",
                "bootstrap",
                "-d",
                f"coderoot:{coderoot}",
            ),
            config_path,
        )
    capsys.readouterr()
    yield config_path


def test_var_coderoot(
    config_path: str, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main.devenv(("/argv0", "var", "coderoot"), config_path)
    assert rc == 0
    captured = capsys.readouterr()
    # coderoot is non-empty and is a valid absolute path
    assert os.path.isabs(captured.out.strip())


def test_var_no_arg_lists_vars(
    config_path: str, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main.devenv(("/argv0", "var"), config_path)
    assert rc == 0
    captured = capsys.readouterr()
    assert "coderoot" in captured.out


def test_var_unknown(
    config_path: str, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main.devenv(
        ("/argv0", "var", "nonexistent"), config_path
    )
    assert rc == 1
    captured = capsys.readouterr()
    assert "unknown variable: nonexistent" in captured.out
