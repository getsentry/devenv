from __future__ import annotations

from unittest.mock import patch

import pytest

from devenv.lib.volta import _sha256
from devenv.lib.volta import _version
from devenv.lib.volta import install_volta
from devenv.lib.volta import UnexpectedPlatformError


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
