from __future__ import annotations

import pathlib
from unittest.mock import call
from unittest.mock import patch

from devenv import sync


def test_darwin(tmp_path: str) -> None:
    with patch("devenv.bootstrap.CI", True), patch(
        "devenv.bootstrap.DARWIN", True
    ), patch(
        "devenv.lib.brew.install"
    ) as mock_brew_install, patch(
        "devenv.lib.volta.install"
    ) as mock_volta_install, patch(
        "devenv.lib.direnv.install"
    ) as mock_direnv_install, patch(
        "devenv.lib.colima.install"
    ) as mock_colima_install, patch(
        "devenv.lib.limactl.install"
    ) as mock_limactl_install, patch(
        "shutil.rmtree"
    ), patch(
        "devenv.lib.proc.run",
        side_effect=[
            None,  # git clone sentry
            None,  # brew install docker qemu
            None,  # devenv sync
            None,  # make bootstrap
        ],
    ) as mock_proc_run:
        coderoot = f"{tmp_path}/coderoot"
        sync.main(context={"repo": "sentry", "reporoot": f"{tmp_path}/sentry"})
        mock_brew_install.assert_called_once()
        mock_volta_install.assert_called_once()
        mock_direnv_install.assert_called_once()
        mock_colima_install.assert_called_once()
        mock_limactl_install.assert_called_once()
        mock_proc_run.assert_has_calls(
            ["a"],
        )
