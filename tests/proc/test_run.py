from __future__ import annotations

from subprocess import CalledProcessError
from unittest.mock import patch

import pytest

from devenv.lib.proc import base_env
from devenv.lib.proc import run


def test_run_with_stdout() -> None:
    cmd = ("echo", "Hello, World!")
    expected_output = "Hello, World!"
    user_environ = {"PATH": "/usr/local/bin:/usr/bin"}
    env = {**user_environ, **base_env}

    with patch("devenv.lib.proc.subprocess_run") as mock_run, patch(
        "devenv.lib.proc.constants.user_environ", user_environ
    ):
        mock_run.return_value.stdout = expected_output.encode()
        result = run(cmd, stdout=True)

    assert result == expected_output
    mock_run.assert_called_once_with(
        cmd, check=True, stdout=-1, cwd=None, env=env
    )


def test_run_without_stdout() -> None:
    cmd = ("echo", "Hello, World!")
    user_environ = {"PATH": "/usr/local/bin:/usr/bin"}
    env = {**user_environ, **base_env}

    with patch("devenv.lib.proc.subprocess_run") as mock_run, patch(
        "devenv.lib.proc.constants.user_environ", user_environ
    ):
        result = run(cmd)

    assert result is None
    mock_run.assert_called_once_with(
        cmd, check=True, stdout=None, cwd=None, env=env
    )


def test_run_with_pathprepend() -> None:
    cmd = ("echo", "Hello, World!")
    pathprepend = "/path/to/bin"
    user_environ = {"PATH": "/usr/local/bin:/usr/bin"}
    env = {**user_environ, **base_env}
    env["PATH"] = f"{pathprepend}:{env['PATH']}"

    with patch("devenv.lib.proc.subprocess_run") as mock_run, patch(
        "devenv.lib.proc.constants.user_environ", user_environ
    ):
        mock_run.return_value.stdout = None
        result = run(cmd, pathprepend=pathprepend)

    assert result is None
    mock_run.assert_called_once_with(
        cmd, check=True, stdout=None, cwd=None, env=env
    )


def test_run_command_not_found() -> None:
    cmd = ("invalid_command",)
    user_environ = {"PATH": "/usr/local/bin:/usr/bin"}
    env = {**user_environ, **base_env}

    with patch("devenv.lib.proc.subprocess_run") as mock_run, patch(
        "devenv.lib.proc.constants.user_environ", user_environ
    ):
        mock_run.side_effect = FileNotFoundError("Command not found")
        with pytest.raises(SystemExit):
            run(cmd, exit=True)

    mock_run.assert_called_once_with(
        cmd, check=True, stdout=None, cwd=None, env=env
    )


def test_run_with_custom_env() -> None:
    cmd = ("sh", "-c", "printenv VAR1 && printenv VAR2")
    custom_env = {"VAR1": "value1", "VAR2": "value2"}

    result = run(cmd, env=custom_env, stdout=True)

    assert result == "value1\nvalue2"


def test_run_with_cwd() -> None:
    cmd = ("echo", "Hello, World!")
    cwd = "/path/to/directory"
    user_environ = {"PATH": "/usr/local/bin:/usr/bin"}
    env = {**user_environ, **base_env}

    with patch("devenv.lib.proc.subprocess_run") as mock_run, patch(
        "devenv.lib.proc.constants.user_environ", user_environ
    ):
        mock_run.return_value.stdout = None
        result = run(cmd, cwd=cwd)

    assert result is None
    mock_run.assert_called_once_with(
        cmd, check=True, stdout=None, cwd=cwd, env=env
    )


def test_run_command_failed() -> None:
    cmd = ("ls", "nonexistent_directory")
    user_environ = {"PATH": "/usr/local/bin:/usr/bin"}
    env = {**user_environ, **base_env}

    with patch("devenv.lib.proc.subprocess_run") as mock_run, patch(
        "devenv.lib.proc.constants.user_environ", user_environ
    ):
        mock_run.side_effect = CalledProcessError(1, cmd)
        with pytest.raises(SystemExit):
            run(cmd, exit=True)

    mock_run.assert_called_once_with(
        cmd, check=True, stdout=None, cwd=None, env=env
    )
