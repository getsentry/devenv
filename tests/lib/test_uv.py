from __future__ import annotations

import os
import pathlib
from unittest.mock import patch

import pytest

from devenv.lib import uv


def test_find_on_path() -> None:
    with patch("devenv.lib.uv.shutil.which", return_value="/opt/bin/uv"):
        assert uv.find() == "/opt/bin/uv"


def test_find_falls_back_to_local_bin(tmp_path: pathlib.Path) -> None:
    os.makedirs(f"{tmp_path}/.local/bin")
    binpath = f"{tmp_path}/.local/bin/uv"
    with open(binpath, "w"):
        pass
    os.chmod(binpath, 0o755)

    with (
        patch("devenv.lib.uv.shutil.which", return_value=None),
        patch("devenv.lib.uv.constants.home", str(tmp_path)),
    ):
        assert uv.find() == binpath


def test_find_missing(tmp_path: pathlib.Path) -> None:
    with (
        patch("devenv.lib.uv.shutil.which", return_value=None),
        patch("devenv.lib.uv.constants.home", str(tmp_path)),
        pytest.raises(SystemExit) as excinfo,
    ):
        uv.find()

    assert "brew install uv" in str(excinfo.value)
