from __future__ import annotations

import os
import pathlib
import shutil
import tarfile
from unittest.mock import patch

from devenv.lib import limactl

# the layout of upstream's lima-2.x-Darwin-*.tar.gz, abridged
RELEASE_FILES = (
    "./bin/lima",
    "./bin/limactl",
    "./bin/docker.lima",
    "./libexec/lima/lima-driver-krunkit",
    "./share/lima/lima-guestagent.Linux-aarch64.gz",
    "./share/lima/templates/default.yaml",
    "./share/doc/lima/README.md",
)


def _release(tmp_path: pathlib.Path) -> str:
    src = tmp_path / "release"
    for name in RELEASE_FILES:
        (src / name).parent.mkdir(parents=True, exist_ok=True)
        (src / name).write_text(name)
    path = f"{tmp_path}/lima.tar.gz"
    with tarfile.open(path, "w:gz") as tarf:
        tarf.add(src, arcname=".")
    return path


def _install(tmp_path: pathlib.Path, binroot: str) -> None:
    release = _release(tmp_path)

    def download(url: str, sha256: str, dest: str) -> str:
        shutil.copy(release, dest)
        return dest

    with patch("devenv.lib.archive.download", side_effect=download):
        limactl._install("url", "sha256", binroot)


def test_install_keeps_data_dirs_next_to_bin(tmp_path: pathlib.Path) -> None:
    prefix = f"{tmp_path}/sentry-devenv"
    binroot = f"{prefix}/bin"

    _install(tmp_path, binroot)

    # lima >= 2 finds these relative to limactl
    assert os.path.exists(f"{binroot}/lima")
    assert os.path.exists(f"{binroot}/limactl")
    assert os.path.exists(
        f"{prefix}/share/lima/lima-guestagent.Linux-aarch64.gz"
    )
    assert os.path.exists(f"{prefix}/libexec/lima/lima-driver-krunkit")
    # only lima and limactl go on PATH
    assert sorted(os.listdir(binroot)) == ["lima", "limactl"]


def test_install_replaces_a_previous_install(tmp_path: pathlib.Path) -> None:
    prefix = f"{tmp_path}/sentry-devenv"
    binroot = f"{prefix}/bin"
    _install(tmp_path, binroot)
    stale = f"{prefix}/share/lima/stale"
    open(stale, "w").close()

    limactl.uninstall(binroot)
    _install(tmp_path, binroot)

    assert not os.path.exists(stale)
    assert os.path.exists(f"{binroot}/limactl")


def test_uninstall_removes_the_lima_1_layout(tmp_path: pathlib.Path) -> None:
    binroot = f"{tmp_path}/sentry-devenv/bin"
    os.makedirs(f"{binroot}/templates")
    for name in (
        "lima",
        "limactl",
        "lima-guestagent.Linux-aarch64",
        "lima-guestagent.Linux-x86_64",
        "templates/default.yaml",
        "colima",
    ):
        open(f"{binroot}/{name}", "w").close()

    limactl.uninstall(binroot)

    assert os.listdir(binroot) == ["colima"]


def test_install_global_reinstalls_without_guest_agents(
    tmp_path: pathlib.Path,
) -> None:
    root = f"{tmp_path}/sentry-devenv"
    binroot = f"{root}/bin"
    _install(tmp_path, binroot)
    # e.g. an interrupted install
    shutil.rmtree(f"{root}/share/lima")

    with (
        patch.object(limactl, "root", root),
        patch.object(limactl, "SYSTEM_MACHINE", "darwin_arm64"),
        patch(
            "devenv.lib.limactl.proc.run", return_value="limactl version 2.2.1"
        ),
        patch.object(limactl, "_install") as install,
    ):
        limactl.install_global()

    install.assert_called_once()
