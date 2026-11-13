from __future__ import annotations

import os
import pathlib
from collections.abc import Iterator
from unittest.mock import call
from unittest.mock import patch

import pytest

from devenv.lib import mise


def _download(url: str, sha256: str, dest: str) -> str:
    open(dest, "w").close()
    return dest


@pytest.fixture
def mise_path(tmp_path: pathlib.Path) -> Iterator[str]:
    path = f"{tmp_path}/bin/mise"
    with patch("devenv.lib.mise.mise_path", path):
        yield path


@pytest.mark.parametrize(
    ("system", "machine", "asset"),
    (
        ("darwin", "arm64", "macos-arm64"),
        ("darwin", "x86_64", "macos-x64"),
        ("linux", "aarch64", "linux-arm64"),
        ("linux", "x86_64", "linux-x64"),
    ),
)
def test_install(mise_path: str, system: str, machine: str, asset: str) -> None:
    with (
        patch("devenv.lib.mise.SYSTEM", system),
        patch("devenv.lib.mise.MACHINE", machine),
        patch("devenv.lib.archive.download", side_effect=_download) as download,
        patch(
            "devenv.lib.mise.proc.run",
            # not installed yet, then the installed version
            side_effect=[RuntimeError(), f"{mise._version} {asset} (date)"],
        ),
    ):
        mise.install()

    assert download.call_args.args == (
        f"https://github.com/jdx/mise/releases/download/v{mise._version}/mise-v{mise._version}-{asset}",
        mise._sha256[asset],
    )
    assert os.access(mise_path, os.X_OK)


def test_install_skips_when_pinned_version_is_installed(mise_path: str) -> None:
    with (
        patch("devenv.lib.archive.download") as download,
        patch(
            "devenv.lib.mise.proc.run",
            return_value=f"{mise._version} macos-arm64 (date)",
        ),
    ):
        mise.install()

    download.assert_not_called()


def test_configured(tmp_path: pathlib.Path) -> None:
    assert not mise.configured(str(tmp_path))

    os.makedirs(f"{tmp_path}/.config/mise")
    open(f"{tmp_path}/.config/mise/config.toml", "w").close()
    assert mise.configured(str(tmp_path))


def test_sync_runs_sync_task(mise_path: str) -> None:
    with (
        patch("devenv.lib.mise.install"),
        patch("devenv.lib.mise.proc.run") as run,
    ):
        assert mise.sync("/repo") == 0

    assert run.mock_calls == [
        call((mise_path, "install"), cwd="/repo"),
        call((mise_path, "tasks", "info", "sync"), cwd="/repo", stdout=True),
        call((mise_path, "run", "sync"), cwd="/repo"),
    ]


def test_sync_without_sync_task(mise_path: str) -> None:
    with (
        patch("devenv.lib.mise.install"),
        patch(
            "devenv.lib.mise.proc.run", side_effect=[None, RuntimeError()]
        ) as run,
    ):
        assert mise.sync("/repo") == 0

    assert run.call_count == 2


def test_sync_fails_when_install_fails(mise_path: str) -> None:
    with (
        patch("devenv.lib.mise.install"),
        patch(
            "devenv.lib.mise.proc.run", side_effect=RuntimeError("boom")
        ) as run,
    ):
        assert mise.sync("/repo") == 1

    assert run.call_count == 1
