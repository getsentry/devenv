from __future__ import annotations

import os
from unittest.mock import patch

from devenv import main
from devenv.lib.config import read_config


def test(tmp_path: str) -> None:
    with patch("devenv.constants.CI", True):
        config_path = f"{tmp_path}/.config/sentry-devenv/config.ini"
        coderoot = f"{tmp_path}/code"

        assert not os.path.exists(config_path)
        main.devenv(
            ("/path/to/argv0", "bootstrap", "-d", f"coderoot:{coderoot}"),
            config_path,
        )
        assert os.path.exists(config_path)

        config = read_config(config_path)
        assert config.get("devenv", "coderoot") == coderoot
