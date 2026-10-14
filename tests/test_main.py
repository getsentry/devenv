from __future__ import annotations

import os
from unittest.mock import patch

from devenv import constants
from devenv import main
from devenv.lib.config import read_config


def test(tmp_path: str) -> None:
    with (
        patch("devenv.constants.CI", True),
        # these download and install global tools, which this doesn't test
        patch("devenv.bootstrap.brew.install"),
        patch("devenv.bootstrap.docker.install_global"),
        patch("devenv.bootstrap.colima.install_global"),
        patch("devenv.bootstrap.limactl.install_global"),
        patch("devenv.bootstrap.direnv.install"),
    ):
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


def test_home_is_not_the_developers() -> None:
    # tests that run real devenv commands rely on this
    assert constants.home == os.environ["HOME"]
    assert not os.path.exists(f"{constants.root}/bin/colima")
