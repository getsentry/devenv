from __future__ import annotations

import os
import shutil
import stat
import tempfile

from devenv.constants import SYSTEM_MACHINE
from devenv.constants import root
from devenv.lib import archive
from devenv.lib import proc

_DATA_DIRS = ("share/lima", "libexec/lima")
_GUEST_AGENT = {
    "darwin_arm64": "lima-guestagent.Linux-aarch64.gz",
    "darwin_x86_64": "lima-guestagent.Linux-x86_64.gz",
}
_DRIVER = {
    "darwin_arm64": "lima-driver-krunkit",
    "darwin_x86_64": "limactl-mcp",
}


def _remove_managed_path(path: str) -> None:
    try:
        mode = os.lstat(path).st_mode
    except FileNotFoundError:
        return

    if stat.S_ISDIR(mode):
        shutil.rmtree(path)
    else:
        os.remove(path)


def uninstall(binroot: str) -> None:
    prefix = os.path.dirname(binroot)
    for path in (
        *(f"{prefix}/{directory}" for directory in _DATA_DIRS),
        f"{binroot}/templates",
    ):
        _remove_managed_path(path)

    for path in (
        f"{binroot}/lima",
        f"{binroot}/limactl",
        f"{binroot}/lima-guestagent.Linux-aarch64",
        f"{binroot}/lima-guestagent.Linux-x86_64",
    ):
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


def _install(url: str, sha256: str, into: str) -> None:
    prefix = os.path.dirname(into)
    os.makedirs(into, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=into) as tmpd:
        archive_file = archive.download(url, sha256, dest=f"{tmpd}/download")
        archive.unpack(archive_file, tmpd)
        uninstall(into)

        for directory in _DATA_DIRS:
            destination = f"{prefix}/{directory}"
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            os.replace(f"{tmpd}/{directory}", destination)

        for name in ("lima", "limactl"):
            destination = f"{into}/{name}"
            try:
                os.remove(destination)
            except FileNotFoundError:
                pass
            os.replace(f"{tmpd}/bin/{name}", destination)


def _installed_version(binroot: str) -> str | None:
    if any(
        shutil.which(name, path=binroot) != f"{binroot}/{name}"
        for name in ("lima", "limactl")
    ):
        return None
    versions = []
    for name in ("lima", "limactl"):
        try:
            stdout = proc.run((f"{binroot}/{name}", "--version"), stdout=True)
        except RuntimeError:
            return None
        words = stdout.strip().split()
        if not words:
            return None
        versions.append(words[-1])
    return versions[0] if versions[0] == versions[1] else "/".join(versions)


def _missing_required_payload(prefix: str) -> tuple[str, ...]:
    required_files = [
        f"{prefix}/bin/lima",
        f"{prefix}/bin/limactl",
        f"{prefix}/share/lima/{_GUEST_AGENT[SYSTEM_MACHINE]}",
        f"{prefix}/share/lima/templates/default.yaml",
    ]
    if driver := _DRIVER.get(SYSTEM_MACHINE):
        required_files.append(f"{prefix}/libexec/lima/{driver}")

    missing = [
        path
        for path in required_files
        if not os.path.isfile(path) or os.path.getsize(path) == 0
    ]
    executable_files = [f"{prefix}/bin/lima", f"{prefix}/bin/limactl"]
    if driver:
        executable_files.append(f"{prefix}/libexec/lima/{driver}")
    for path in executable_files:
        if os.path.isfile(path) and not os.access(path, os.X_OK):
            missing.append(path)
    return tuple(missing)


def install_global() -> None:
    version = "2.2.1"
    cfg = {
        "darwin_x86_64": f"https://github.com/lima-vm/lima/releases/download/v{version}/lima-{version}-Darwin-x86_64.tar.gz",
        "darwin_x86_64_sha256": "6b776e4bc41f358e6ee01fefcc78e2eb26f11635a0fcff632234af77a566c6c4",
        "darwin_arm64": f"https://github.com/lima-vm/lima/releases/download/v{version}/lima-{version}-Darwin-arm64.tar.gz",
        "darwin_arm64_sha256": "9e9eacce88f37e185c346bad73aa6136f738d8cdf8c3bb23cd42b071824bc66e",
    }

    binroot = f"{root}/bin"
    installed_version = _installed_version(binroot)
    missing = _missing_required_payload(root)
    if installed_version == version and not missing:
        return

    if installed_version is not None:
        if installed_version != version:
            print(f"installed limactl {installed_version} is unexpected!")
    if missing:
        print(
            f"limactl {version} is missing {', '.join(missing)}; reinstalling"
        )

    _install(cfg[SYSTEM_MACHINE], cfg[f"{SYSTEM_MACHINE}_sha256"], binroot)

    installed_version = _installed_version(binroot)
    if installed_version != version:
        raise SystemExit(
            f"Failed to install Lima {version}! Found: {installed_version}"
        )


def install(version: str, url: str, sha256: str, reporoot: str) -> None:
    install_global()
