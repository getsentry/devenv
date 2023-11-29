from __future__ import annotations

from devenv.lib.volta import build_url


def test_build_url_linux_x86_64() -> None:
    assert (
        build_url("volta-1.1.1-linux.tar.gz")
        == "https://github.com/volta-cli/volta/releases/download/v1.1.1/volta-1.1.1-linux.tar.gz"
    )


def test_build_url_macos_x86_64() -> None:
    assert (
        build_url("volta-1.1.1-macos.tar.gz")
        == "https://github.com/volta-cli/volta/releases/download/v1.1.1/volta-1.1.1-macos.tar.gz"
    )


def test_build_url_macos_arm64() -> None:
    assert (
        build_url("volta-1.1.1-macos-aarch64.tar.gz")
        == "https://github.com/volta-cli/volta/releases/download/v1.1.1/volta-1.1.1-macos-aarch64.tar.gz"
    )
