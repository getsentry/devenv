from __future__ import annotations

from unittest.mock import patch

import pytest

from devenv.lib.volta import determine_platform
from devenv.lib.volta import UnexpectedPlatformError


def test_determine_platform_linux_x86_64() -> None:
    with patch("platform.system", return_value="Linux"), patch(
        "platform.machine", return_value="x86_64"
    ):
        assert (
            determine_platform("/path/to/unpack") == "volta-1.1.1-linux.tar.gz"
        )


def test_determine_platform_macos_x86_64() -> None:
    with patch("platform.system", return_value="Darwin"), patch(
        "platform.machine", return_value="x86_64"
    ):
        assert (
            determine_platform("/path/to/unpack") == "volta-1.1.1-macos.tar.gz"
        )


def test_determine_platform_macos_arm64() -> None:
    with patch("platform.system", return_value="Darwin"), patch(
        "platform.machine", return_value="arm64"
    ):
        assert (
            determine_platform("/path/to/unpack")
            == "volta-1.1.1-macos-aarch64.tar.gz"
        )


def test_determine_platform_unexpected_platform() -> None:
    with patch("platform.system", return_value="Unexpected"):
        with pytest.raises(UnexpectedPlatformError):
            determine_platform("/path/to/unpack")
