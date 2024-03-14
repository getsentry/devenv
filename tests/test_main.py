from __future__ import annotations

from unittest.mock import patch

from devenv import main


def test_initialize_config(tmp_path: str) -> None:
    with patch("devenv.main.CI", True):
        config_path = f"{tmp_path}/.config/sentry-devenv/config.ini"
        main.initialize_config(config_path, main.DEFAULT_CONFIG)

        with open(config_path, "r") as f:
            assert (
                f.read()
                == """[devenv]
# please enter the root directory you want to work in
coderoot = ~/code

"""
            )
