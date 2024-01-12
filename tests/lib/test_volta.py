from __future__ import annotations

import os
from unittest.mock import call
from unittest.mock import patch

import pytest

from devenv.lib.volta import _sha256
from devenv.lib.volta import _version
from devenv.lib.volta import install
from devenv.lib.volta import install_volta
from devenv.lib.volta import populate_volta_home_with_shims
from devenv.lib.volta import UnexpectedPlatformError


def test_install(tmp_path: str) -> None:
    VOLTA_HOME = f"{tmp_path}/volta"
    os.makedirs(f"{tmp_path}/bin")
    os.makedirs(f"{VOLTA_HOME}/bin")
    for executable in ("node", "npm", "npx", "yarn", "pnpm"):
        open(f"{VOLTA_HOME}/bin/{executable}", "a").close()

    with patch.multiple(
        "devenv.lib.volta", root=tmp_path, VOLTA_HOME=VOLTA_HOME
    ):
        with patch("devenv.lib.volta.which", side_effect=[None, None]), patch(
            "devenv.lib.volta.install_volta"
        ) as mock_install_volta, patch(
            "devenv.lib.volta.proc.run",
            side_effect=[None, _version],  # volta-migrate  # volta -v
        ) as mock_proc_run:
            install()

            mock_install_volta.assert_called_once_with(f"{tmp_path}/bin")
            assert mock_proc_run.mock_calls == [
                call((f"{tmp_path}/bin/volta-migrate",)),
                call((f"{tmp_path}/bin/volta", "-v"), stdout=True),
            ]
            assert (
                os.readlink(f"{tmp_path}/bin/node")
                == f"{tmp_path}/volta/bin/node"
            )

    # now test already installed
    with patch.multiple(
        "devenv.lib.volta", root=tmp_path, VOLTA_HOME=VOLTA_HOME
    ), patch("devenv.lib.volta.install_volta") as mock_install_volta, patch(
        "devenv.lib.volta.which",
        side_effect=[f"{tmp_path}/bin/volta", f"{tmp_path}/volta/bin/node"],
    ):
        install()
        assert not mock_install_volta.called


def test_install_volta_linux_x86_64() -> None:
    with patch("platform.system", return_value="Linux") as mock_system, patch(
        "platform.machine", return_value="x86_64"
    ) as mock_machine, patch(
        "devenv.lib.volta.archive.download"
    ) as mock_download, patch(
        "devenv.lib.volta.archive.unpack"
    ) as mock_unpack:
        install_volta("/path/to/unpack")
        mock_system.assert_called_once()
        mock_machine.assert_called_once()
        mock_download.assert_called_once_with(
            (
                "https://github.com/volta-cli/volta/releases/download/"
                f"v{_version}/volta-{_version}-linux.tar.gz"
            ),
            _sha256[f"volta-{_version}-linux.tar.gz"],
        )
        mock_unpack.assert_called_once_with(
            mock_download.return_value, "/path/to/unpack"
        )


def test_install_volta_macos_x86_64() -> None:
    with patch("platform.system", return_value="Darwin") as mock_system, patch(
        "platform.machine", return_value="x86_64"
    ) as mock_machine, patch(
        "devenv.lib.volta.archive.download"
    ) as mock_download, patch(
        "devenv.lib.volta.archive.unpack"
    ) as mock_unpack:
        install_volta("/path/to/unpack")
        mock_system.assert_called_once()
        mock_machine.assert_called_once()
        mock_download.assert_called_once_with(
            (
                "https://github.com/volta-cli/volta/releases/download/"
                f"v{_version}/volta-{_version}-macos.tar.gz"
            ),
            _sha256[f"volta-{_version}-macos.tar.gz"],
        )
        mock_unpack.assert_called_once_with(
            mock_download.return_value, "/path/to/unpack"
        )


def test_install_volta_macos_arm64() -> None:
    with patch("platform.system", return_value="Darwin") as mock_system, patch(
        "platform.machine", return_value="arm64"
    ) as mock_machine, patch(
        "devenv.lib.volta.archive.download"
    ) as mock_download, patch(
        "devenv.lib.volta.archive.unpack"
    ) as mock_unpack:
        install_volta("/path/to/unpack")
        mock_system.assert_called_once()
        mock_machine.assert_called_once()
        mock_download.assert_called_once_with(
            (
                "https://github.com/volta-cli/volta/releases/download/"
                f"v{_version}/volta-{_version}-macos-aarch64.tar.gz"
            ),
            _sha256[f"volta-{_version}-macos-aarch64.tar.gz"],
        )
        mock_unpack.assert_called_once_with(
            mock_download.return_value, "/path/to/unpack"
        )


def test_install_volta_unexpected_platform() -> None:
    with patch("platform.system", return_value="Unexpected"):
        with pytest.raises(UnexpectedPlatformError):
            install_volta("/path/to/unpack")


def test_populate_volta_home_with_shims() -> None:
    with patch("devenv.lib.volta.proc.run") as mock_run:
        unpack_into = "/path/to/unpack"
        mock_run.side_effect = [
            None,  # mock run for volta-migrate
            _version,  # mock run for volta -v
        ]

        populate_volta_home_with_shims(unpack_into)

        assert mock_run.mock_calls == [
            call((f"{unpack_into}/volta-migrate",)),
            call((f"{unpack_into}/volta", "-v"), stdout=True),
        ]
