from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from devenv.lib.proc import run


def test_run_with_stdout() -> None:
    cmd = ("echo", "Hello, World!")
    expected_output = "Hello, World!"

    result = run(cmd, stdout=True)

    assert result == expected_output


def test_run_without_stdout() -> None:
    cmd = ("echo", "Hello, World!")

    result = run(cmd)

    assert result is None


def test_run_with_debug() -> None:
    cmd = ("echo", "Hello, World!")

    with patch("devenv.lib.proc.constants.DEBUG", True), patch(
        "devenv.lib.proc.xtrace"
    ) as mock_xtrace:
        run(cmd)

    mock_xtrace.assert_called_once_with(cmd)


def test_run_with_pathprepend(tmp_path: str) -> None:
    dummy_executable = os.path.join(tmp_path, "dummy_executable")
    with open(dummy_executable, "w") as f:
        f.write("#!/bin/sh\necho Hello, World!")
    os.chmod(dummy_executable, 0o755)

    cmd = ("dummy_executable",)
    pathprepend = tmp_path

    result = run(cmd, pathprepend=pathprepend, stdout=True)

    assert result == "Hello, World!"


def test_run_command_not_found() -> None:
    cmd = ("invalid_command",)

    with pytest.raises(RuntimeError):
        run(cmd, exit=False)


def test_run_command_not_found_with_exit() -> None:
    cmd = ("invalid_command",)

    with pytest.raises(SystemExit):
        run(cmd, exit=True)


def test_run_with_custom_env() -> None:
    cmd = ("sh", "-c", "printenv VAR1 && printenv VAR2")
    custom_env = {"VAR1": "value1", "VAR2": "value2"}

    result = run(cmd, env=custom_env, stdout=True)

    assert result == "value1\nvalue2"


def test_run_with_cwd(tmp_path: str) -> None:
    text = "Hello, World!"
    with open(os.path.join(tmp_path, "test.txt"), "w") as f:
        f.write(text)
    cmd = ("cat", "test.txt")
    cwd = tmp_path

    result = run(cmd, cwd=cwd, stdout=True)

    assert result == text


def test_run_command_failed() -> None:
    cmd = ("ls", "nonexistent_directory")

    with pytest.raises(RuntimeError):
        run(cmd, exit=False)


def test_run_command_failed_with_exit() -> None:
    cmd = ("ls", "nonexistent_directory")

    with pytest.raises(SystemExit):
        run(cmd, exit=True)
