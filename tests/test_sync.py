from __future__ import annotations

import os
import pathlib
from unittest.mock import call
from unittest.mock import patch

from devenv import sync


def test_darwin(tmp_path: str) -> None:
    with patch("devenv.bootstrap.CI", True), patch(
        "devenv.bootstrap.DARWIN", True
    ), patch("devenv.lib.volta.install") as mock_volta_install, patch(
        "devenv.lib.colima.install"
    ) as mock_colima_install, patch(
        "devenv.lib.limactl.install"
    ) as mock_limactl_install, patch(
        "shutil.rmtree"
    ), patch(
        "devenv.lib.proc.run", side_effect=[
            None,  # python -m venv .venv
        ],
    ) as mock_proc_run, patch(
        "devenv.sync.run_procs",
        side_effect=[
            None,  # run_procs make setup-git
        ],
    ) as mock_run_procs:
        reporoot = f"{tmp_path}/sentry"
        venv = f"{tmp_path}/sentry/.venv"

        os.makedirs(f"{reporoot}/devenv")
        os.makedirs(venv)

        with open(f"{venv}/pyvenv.cfg", "w") as f:
            f.write(
                f"""
version = 3.8.16
"""
            )

        with open(f"{reporoot}/devenv/config.ini", "w") as f:
            f.write(
                f"""
[python]
version = 3.10.13
darwin_x86_64 = https://github.com/indygreg/python-build-standalone/releases/download/20231002/cpython-3.10.13+20231002-x86_64-apple-darwin-install_only.tar.gz
darwin_x86_64_sha256 = be0b19b6af1f7d8c667e5abef5505ad06cf72e5a11bb5844970c395a7e5b1275
darwin_arm64 = https://github.com/indygreg/python-build-standalone/releases/download/20231002/cpython-3.10.13+20231002-aarch64-apple-darwin-install_only.tar.gz
darwin_arm64_sha256 = fd027b1dedf1ea034cdaa272e91771bdf75ddef4c8653b05d224a0645aa2ca3c
linux_x86_64 = https://github.com/indygreg/python-build-standalone/releases/download/20231002/cpython-3.10.13+20231002-x86_64-unknown-linux-gnu-install_only.tar.gz
linux_x86_64_sha256 = 5d0429c67c992da19ba3eb58b3acd0b35ec5e915b8cae9a4aa8ca565c423847a
linux_arm64 = https://github.com/indygreg/python-build-standalone/releases/download/20231002/cpython-3.10.13+20231002-aarch64-unknown-linux-gnu-install_only.tar.gz
linux_arm64_sha256 = 8675915ff454ed2f1597e27794bc7df44f5933c26b94aa06af510fe91b58bb97
"""
            )

        sync.main(context={"repo": "sentry", "reporoot": reporoot})
        mock_volta_install.assert_called_once()
        mock_colima_install.assert_called_once()
        mock_limactl_install.assert_called_once()
        mock_proc_run.assert_has_calls(["a"])
