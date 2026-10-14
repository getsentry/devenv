from __future__ import annotations

import os
import pathlib
import shutil
from unittest.mock import patch

from devenv.lib import tenv


def _unpack(_archive_file: str, tmpd: str) -> None:
    for binary in tenv.BINARIES:
        open(f"{tmpd}/{binary}", "w").close()


def _install(reporoot: str, version: str = "v0.0.0") -> None:
    with (
        patch("devenv.lib.archive.download"),
        patch("devenv.lib.archive.unpack", side_effect=_unpack),
        patch(
            "devenv.lib.tenv.proc.run",
            # once to check what's installed, once to verify
            side_effect=[f"tenv version {version}"] * 2,
        ),
    ):
        tenv.install(version, "url", "sha256", reporoot)


def test_install(tmp_path: pathlib.Path) -> None:
    reporoot = f"{tmp_path}/test"
    binroot = f"{reporoot}/.devenv/bin"

    _install(reporoot)

    # terragrunt shells out to `tofu`, so it has to be on PATH too
    for binary in tenv.SHIMS:
        assert os.path.exists(f"{binroot}/tenv-root/bin/{binary}"), binary
        with open(f"{binroot}/{binary}", "r") as f:
            assert (
                f.read()
                == f"""#!/bin/sh
export TENV_ROOT={binroot}/tenv-root
exec {binroot}/tenv-root/bin/{binary} "$@"
"""
            )

    # tf is extracted but deliberately not shimmed onto PATH
    assert os.path.exists(f"{binroot}/tenv-root/bin/tf")
    assert not os.path.exists(f"{binroot}/tf")


def test_install_is_a_noop_when_complete(tmp_path: pathlib.Path) -> None:
    reporoot = f"{tmp_path}/test"

    _install(reporoot)

    with (
        patch("devenv.lib.archive.download") as mock_download,
        patch(
            "devenv.lib.tenv.proc.run",
            side_effect=["tenv version v0.0.0"],  # tenv version
        ),
    ):
        tenv.install("v0.0.0", "url", "sha256", reporoot)

    assert mock_download.mock_calls == []


def test_install_replaces_a_missing_shim(tmp_path: pathlib.Path) -> None:
    reporoot = f"{tmp_path}/test"
    binroot = f"{reporoot}/.devenv/bin"

    _install(reporoot)

    # a checkout installed by a devenv that predates the tofu shim: the
    # version matches, so this has to reinstall anyway or it stays broken
    os.remove(f"{binroot}/tofu")
    os.remove(f"{binroot}/tenv-root/bin/tofu")

    _install(reporoot)

    assert os.path.exists(f"{binroot}/tofu")
    assert os.path.exists(f"{binroot}/tenv-root/bin/tofu")


def test_install_recovers_from_a_missing_tenv_root(
    tmp_path: pathlib.Path,
) -> None:
    reporoot = f"{tmp_path}/test"
    binroot = f"{reporoot}/.devenv/bin"

    _install(reporoot)

    # an interrupted sync or a moved checkout leaves the shims on PATH
    # pointing at a tenv-root that isn't there, so probing the version
    # exits 126 - that has to reinstall, not take the whole sync down
    shutil.rmtree(f"{binroot}/tenv-root")

    def run(cmd: tuple[str, ...], stdout: bool = False) -> str:
        # the shim only runs if its TENV_ROOT survived
        if not os.path.exists(f"{binroot}/tenv-root/bin/tenv"):
            raise RuntimeError(f"Command `{cmd[0]} version` failed! (code 126)")
        return "tenv version v0.0.0"

    with (
        patch("devenv.lib.archive.download"),
        patch("devenv.lib.archive.unpack", side_effect=_unpack),
        patch("devenv.lib.tenv.proc.run", side_effect=run),
    ):
        tenv.install("v0.0.0", "url", "sha256", reporoot)

    assert tenv._missing_shims(binroot) == ()


def test_version_of_an_unrunnable_tenv_is_empty() -> None:
    with patch(
        "devenv.lib.tenv.proc.run",
        side_effect=RuntimeError("failed! (code 126)"),
    ):
        assert tenv._version(f"{os.sep}nonexistent{os.sep}tenv") == ""


def test_uninstall_removes_shims_before_tenv_root(
    tmp_path: pathlib.Path,
) -> None:
    binroot = f"{tmp_path}/bin"
    os.makedirs(f"{binroot}/tenv-root/bin")
    for binary in tenv.SHIMS:
        open(f"{binroot}/{binary}", "w").close()

    surviving_shims: list[list[str]] = []
    real_rmtree = shutil.rmtree

    def spy(path: str, ignore_errors: bool = False) -> None:
        surviving_shims.append(
            [b for b in tenv.SHIMS if os.path.exists(f"{binroot}/{b}")]
        )
        real_rmtree(path, ignore_errors=ignore_errors)

    with patch("devenv.lib.tenv.shutil.rmtree", side_effect=spy):
        tenv.uninstall(binroot)

    # interrupted between the two steps, we'd rather have no tenv on PATH
    # than shims pointing at a tenv-root that's already gone
    assert surviving_shims == [[]]


def test_uninstall_removes_every_shim(tmp_path: pathlib.Path) -> None:
    binroot = f"{tmp_path}/bin"
    os.makedirs(f"{binroot}/tenv-root/bin")
    for binary in tenv.SHIMS:
        open(f"{binroot}/{binary}", "w").close()

    tenv.uninstall(binroot)

    assert not os.path.exists(f"{binroot}/tenv-root")
    assert os.listdir(binroot) == []
