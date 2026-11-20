from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from devenv.lib.repository import Repository


def test_check_minimum_version(tmp_path: str) -> None:
    repo = Repository(f"{tmp_path}/repo")

    mock_config = """
[devenv]
minimum_version = 1.11.0
"""

    os.makedirs(repo.config_path)
    with open(f"{repo.config_path}/config.ini", "w") as f:
        f.write(mock_config)

    with (
        patch("importlib.metadata.version", return_value="1.10.2"),
        patch("platform.python_version", return_value="3.11.4"),
        pytest.raises(SystemExit, match="install-devenv.sh") as raised,
    ):
        repo.check_minimum_version()
    message = str(raised.value)
    assert "running Python 3.11.4" in message
    assert "devenv update 1.11.0" in message

    with patch("importlib.metadata.version", return_value="1.11.0"):
        repo.check_minimum_version()

    with patch("importlib.metadata.version", return_value="1.11.1"):
        repo.check_minimum_version()
