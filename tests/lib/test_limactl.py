from __future__ import annotations

import os
import pathlib
import shutil
import tarfile
from unittest.mock import patch

import pytest

from devenv.lib import limactl

_RELEASE_FILES = (
    "bin/lima",
    "bin/limactl",
    "libexec/lima/limactl-mcp",
    "libexec/lima/lima-driver-krunkit",
    "share/lima/lima-guestagent.Linux-aarch64.gz",
    "share/lima/lima-guestagent.Linux-x86_64.gz",
    "share/lima/templates/default.yaml",
)


def _release(tmp_path: pathlib.Path) -> pathlib.Path:
    source = tmp_path / "release"
    for name in _RELEASE_FILES:
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "#!/bin/sh\nexit 0\n" if name.startswith("bin/") else name
        )
        if name.startswith(("bin/", "libexec/")):
            path.chmod(0o755)
    archive_path = tmp_path / "lima.tar.gz"
    with tarfile.open(archive_path, "w:gz") as tarf:
        tarf.add(source, arcname=".")
    return archive_path


def _install_from_release(
    tmp_path: pathlib.Path, binroot: str, machine: str = "darwin_arm64"
) -> None:
    release = _release(tmp_path)

    def download(url: str, sha256: str, dest: str) -> str:
        shutil.copy(release, dest)
        return dest

    with (
        patch("devenv.lib.archive.download", side_effect=download),
        patch.object(limactl, "SYSTEM_MACHINE", machine),
    ):
        limactl._install("url", "sha256", binroot)


def _installed_version(command: tuple[str, ...], **kwargs: object) -> str:
    return f"{pathlib.Path(command[0]).name} version 2.2.1"


def test_install_keeps_native_lima_layout(tmp_path: pathlib.Path) -> None:
    prefix = tmp_path / "sentry-devenv"
    binroot = str(prefix / "bin")

    _install_from_release(tmp_path, binroot)

    assert (prefix / "bin/lima").is_file()
    assert (prefix / "bin/limactl").is_file()
    assert (prefix / "share/lima/lima-guestagent.Linux-aarch64.gz").is_file()
    assert (prefix / "libexec/lima/lima-driver-krunkit").is_file()
    assert sorted(path.name for path in (prefix / "bin").iterdir()) == [
        "lima",
        "limactl",
    ]


def test_install_removes_old_lima_layout_from_devenv_prefix(
    tmp_path: pathlib.Path,
) -> None:
    prefix = tmp_path / "sentry-devenv"
    binroot = prefix / "bin"
    old_paths = (
        binroot / "templates/default.yaml",
        binroot / "lima-guestagent.Linux-aarch64",
        binroot / "lima-guestagent.Linux-x86_64",
        prefix / "share/lima/old-guestagent",
        prefix / "libexec/lima/old-driver",
    )
    for path in old_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"old layout")

    _install_from_release(tmp_path, str(binroot))

    assert not (binroot / "templates").exists()
    assert not (binroot / "lima-guestagent.Linux-aarch64").exists()
    assert not (binroot / "lima-guestagent.Linux-x86_64").exists()
    assert not (prefix / "share/lima/old-guestagent").exists()
    assert not (prefix / "libexec/lima/old-driver").exists()
    assert (prefix / "share/lima/templates/default.yaml").is_file()


@pytest.mark.parametrize(
    ("machine", "agent", "driver"),
    (
        (
            "darwin_arm64",
            "lima-guestagent.Linux-aarch64.gz",
            "lima-driver-krunkit",
        ),
        ("darwin_x86_64", "lima-guestagent.Linux-x86_64.gz", "limactl-mcp"),
    ),
)
def test_install_global_installs_native_payload(
    tmp_path: pathlib.Path, machine: str, agent: str, driver: str | None
) -> None:
    root = str(tmp_path / "sentry-devenv")
    binroot = f"{root}/bin"
    release = _release(tmp_path)

    def download(url: str, sha256: str, dest: str) -> str:
        shutil.copy(release, dest)
        return dest

    with (
        patch.object(limactl, "root", root),
        patch.object(limactl, "SYSTEM_MACHINE", machine),
        patch("devenv.lib.archive.download", side_effect=download),
        patch("devenv.lib.limactl.proc.run", side_effect=_installed_version),
    ):
        limactl.install_global()

    assert os.path.isfile(f"{root}/share/lima/{agent}")
    assert os.path.isfile(f"{binroot}/limactl")
    if driver:
        assert os.path.isfile(f"{root}/libexec/lima/{driver}")


def test_uninstall_removes_lima_one_files_and_preserves_user_data(
    tmp_path: pathlib.Path,
) -> None:
    prefix = tmp_path / "sentry-devenv"
    binroot = prefix / "bin"
    home = tmp_path / "home"
    user_data = home / ".lima/sentinel"
    user_data.parent.mkdir(parents=True)
    user_data.write_bytes(b"standalone lima vm\x00data")
    original = user_data.read_bytes()
    binroot.mkdir(parents=True)
    for name in (
        "lima",
        "limactl",
        "lima-guestagent.Linux-aarch64",
        "lima-guestagent.Linux-x86_64",
        "templates/default.yaml",
        "colima",
    ):
        path = binroot / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()

    with patch.object(limactl, "home", str(home), create=True):
        limactl.uninstall(str(binroot))

    assert sorted(path.name for path in binroot.iterdir()) == ["colima"]
    assert user_data.read_bytes() == original


@pytest.mark.parametrize(
    "missing",
    (
        "bin/lima",
        "bin/limactl",
        "share/lima/lima-guestagent.Linux-aarch64.gz",
        "share/lima/templates/default.yaml",
        "libexec/lima/lima-driver-krunkit",
    ),
)
def test_install_global_repairs_missing_payload(
    tmp_path: pathlib.Path, missing: str, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "sentry-devenv"
    home = tmp_path / "home"
    sentinel = home / ".lima/sentinel"
    sentinel.parent.mkdir(parents=True)
    sentinel.write_bytes(b"standalone lima vm\x00data")
    original = sentinel.read_bytes()
    colima_disk = home / ".colima/_lima/colima/diffdisk"
    colima_disk.parent.mkdir(parents=True)
    colima_disk.write_bytes(b"Colima VM data")
    original_colima_disk = colima_disk.read_bytes()
    _install_from_release(tmp_path, str(root / "bin"))
    (root / missing).unlink()
    release = _release(tmp_path)

    def download(url: str, sha256: str, dest: str) -> str:
        shutil.copy(release, dest)
        return dest

    with (
        patch.object(limactl, "root", str(root)),
        patch.object(limactl, "SYSTEM_MACHINE", "darwin_arm64"),
        patch.object(limactl, "home", str(home), create=True),
        patch("devenv.lib.archive.download", side_effect=download),
        patch("devenv.lib.limactl.proc.run", side_effect=_installed_version),
    ):
        limactl.install_global()

    assert (root / missing).is_file()
    assert sentinel.read_bytes() == original
    assert colima_disk.read_bytes() == original_colima_disk
    assert missing in capsys.readouterr().out


def test_install_global_repairs_corrupt_guest_agent(
    tmp_path: pathlib.Path,
) -> None:
    root = tmp_path / "sentry-devenv"
    _install_from_release(tmp_path, str(root / "bin"))
    guest_agent = root / "share/lima/lima-guestagent.Linux-aarch64.gz"
    guest_agent.write_bytes(b"")
    release = _release(tmp_path)

    def download(url: str, sha256: str, dest: str) -> str:
        shutil.copy(release, dest)
        return dest

    with (
        patch.object(limactl, "root", str(root)),
        patch.object(limactl, "SYSTEM_MACHINE", "darwin_arm64"),
        patch("devenv.lib.archive.download", side_effect=download),
        patch("devenv.lib.limactl.proc.run", side_effect=_installed_version),
    ):
        limactl.install_global()

    assert guest_agent.stat().st_size > 0


def test_install_global_repairs_non_executable_driver(
    tmp_path: pathlib.Path,
) -> None:
    root = tmp_path / "sentry-devenv"
    _install_from_release(tmp_path, str(root / "bin"))
    driver = root / "libexec/lima/lima-driver-krunkit"
    driver.chmod(0o644)
    release = _release(tmp_path)

    def download(url: str, sha256: str, dest: str) -> str:
        shutil.copy(release, dest)
        return dest

    with (
        patch.object(limactl, "root", str(root)),
        patch.object(limactl, "SYSTEM_MACHINE", "darwin_arm64"),
        patch("devenv.lib.archive.download", side_effect=download),
        patch("devenv.lib.limactl.proc.run", side_effect=_installed_version),
    ):
        limactl.install_global()

    assert os.access(driver, os.X_OK)


def test_install_global_reinstalls_wrong_version(
    tmp_path: pathlib.Path,
) -> None:
    root = tmp_path / "sentry-devenv"
    home = tmp_path / "home"
    sentinel = home / ".lima/sentinel"
    sentinel.parent.mkdir(parents=True)
    sentinel.write_bytes(b"standalone lima vm\x00data")
    original = sentinel.read_bytes()
    _install_from_release(tmp_path, str(root / "bin"))
    release = _release(tmp_path)

    def installed_version(command: tuple[str, ...], **kwargs: object) -> str:
        version = "2.1.0" if downloads == 0 else "2.2.1"
        return f"{pathlib.Path(command[0]).name} version {version}"

    downloads = 0

    def download(url: str, sha256: str, dest: str) -> str:
        nonlocal downloads
        downloads += 1
        shutil.copy(release, dest)
        return dest

    with (
        patch.object(limactl, "root", str(root)),
        patch.object(limactl, "SYSTEM_MACHINE", "darwin_arm64"),
        patch.object(limactl, "home", str(home), create=True),
        patch("devenv.lib.archive.download", side_effect=download),
        patch("devenv.lib.limactl.proc.run", side_effect=installed_version),
    ):
        limactl.install_global()

    assert (root / "bin/limactl").is_file()
    assert sentinel.read_bytes() == original


def test_install_global_reinstalls_mismatched_lima_commands(
    tmp_path: pathlib.Path,
) -> None:
    root = tmp_path / "sentry-devenv"
    _install_from_release(tmp_path, str(root / "bin"))
    release = _release(tmp_path)
    downloads = 0

    def download(url: str, sha256: str, dest: str) -> str:
        nonlocal downloads
        downloads += 1
        shutil.copy(release, dest)
        return dest

    def installed_version(command: tuple[str, ...], **kwargs: object) -> str:
        command_version = "2.2.1"
        if downloads == 0 and pathlib.Path(command[0]).name == "lima":
            command_version = "2.2.0"
        return f"{pathlib.Path(command[0]).name} version {command_version}"

    with (
        patch.object(limactl, "root", str(root)),
        patch.object(limactl, "SYSTEM_MACHINE", "darwin_arm64"),
        patch("devenv.lib.archive.download", side_effect=download),
        patch("devenv.lib.limactl.proc.run", side_effect=installed_version),
    ):
        limactl.install_global()

    assert downloads == 1
    assert (root / "bin/lima").is_file()
    assert (root / "bin/limactl").is_file()


def test_install_global_is_idempotent(tmp_path: pathlib.Path) -> None:
    root = tmp_path / "sentry-devenv"
    _install_from_release(tmp_path, str(root / "bin"))

    with (
        patch.object(limactl, "root", str(root)),
        patch.object(limactl, "SYSTEM_MACHINE", "darwin_arm64"),
        patch("devenv.lib.limactl.proc.run", side_effect=_installed_version),
        patch.object(limactl, "_install") as install,
    ):
        limactl.install_global()

    install.assert_not_called()


def test_reinstall_and_uninstall_preserve_lima_user_data(
    tmp_path: pathlib.Path,
) -> None:
    root = tmp_path / "sentry-devenv"
    home = tmp_path / "home"
    sentinel = home / ".lima/sentinel"
    sentinel.parent.mkdir(parents=True)
    sentinel.write_bytes(b"standalone lima vm\x00data")
    original = sentinel.read_bytes()
    _install_from_release(tmp_path, str(root / "bin"))
    release = _release(tmp_path)

    downloads = 0

    def download(url: str, sha256: str, dest: str) -> str:
        nonlocal downloads
        downloads += 1
        shutil.copy(release, dest)
        return dest

    def installed_version(command: tuple[str, ...], **kwargs: object) -> str:
        version = "2.1.0" if downloads == 0 else "2.2.1"
        return f"{pathlib.Path(command[0]).name} version {version}"

    with (
        patch.object(limactl, "root", str(root)),
        patch.object(limactl, "SYSTEM_MACHINE", "darwin_arm64"),
        patch.object(limactl, "home", str(home), create=True),
        patch("devenv.lib.archive.download", side_effect=download),
        patch("devenv.lib.limactl.proc.run", side_effect=installed_version),
    ):
        limactl.install_global()
        limactl.uninstall(f"{root}/bin")

    assert sentinel.read_bytes() == original


def test_interrupted_download_preserves_lima_install_and_user_data(
    tmp_path: pathlib.Path,
) -> None:
    root = tmp_path / "sentry-devenv"
    home = tmp_path / "home"
    sentinel = home / ".lima/sentinel"
    sentinel.parent.mkdir(parents=True)
    sentinel.write_bytes(b"standalone lima vm\x00data")
    original = sentinel.read_bytes()
    binroot = root / "bin"
    _install_from_release(tmp_path, str(binroot))
    lima_binary = (binroot / "limactl").read_bytes()

    with (
        patch.object(limactl, "home", str(home), create=True),
        patch(
            "devenv.lib.archive.download",
            side_effect=RuntimeError("download interrupted"),
        ),
        pytest.raises(RuntimeError, match="download interrupted"),
    ):
        limactl._install("url", "sha256", str(binroot))

    assert sentinel.read_bytes() == original
    assert (binroot / "limactl").read_bytes() == lima_binary
