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
_DRIVER = {"darwin_arm64": "lima-driver-krunkit"}


def _remove_managed_path(path: str) -> None:
    try:
        mode = os.lstat(path).st_mode
    except FileNotFoundError:
        return

    if stat.S_ISDIR(mode):
        shutil.rmtree(path)
    else:
        os.remove(path)


def _managed_paths(binroot: str) -> tuple[str, ...]:
    prefix = os.path.dirname(binroot)
    return (
        f"{prefix}/share/lima",
        f"{prefix}/libexec/lima",
        f"{binroot}/templates",
        f"{binroot}/lima",
        f"{binroot}/limactl",
        f"{binroot}/lima-guestagent.Linux-aarch64",
        f"{binroot}/lima-guestagent.Linux-x86_64",
    )


def uninstall(binroot: str) -> None:
    for path in _managed_paths(binroot):
        _remove_managed_path(path)


def _install(
    url: str, sha256: str, into: str, *, expected_version: str | None = None
) -> None:
    prefix = os.path.dirname(into)
    os.makedirs(into, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=into) as tmpd:
        archive_file = archive.download(url, sha256, dest=f"{tmpd}/download")
        archive.unpack(archive_file, tmpd)
        missing = _missing_required_payload(tmpd)
        if missing:
            raise RuntimeError(
                f"Lima release is incomplete: {', '.join(missing)}"
            )

        if expected_version is not None:
            staged_version = _staged_version(tmpd)
            if staged_version != expected_version:
                raise RuntimeError(
                    f"Lima release reported {staged_version}, expected "
                    f"{expected_version}"
                )

        backup = tempfile.mkdtemp(prefix=".lima-install-", dir=prefix)
        backed_up: list[tuple[str, str]] = []
        installed: list[str] = []
        try:
            for target in _managed_paths(into):
                if not os.path.lexists(target):
                    continue
                backup_target = os.path.join(
                    backup, os.path.relpath(target, prefix)
                )
                os.makedirs(os.path.dirname(backup_target), exist_ok=True)
                os.replace(target, backup_target)
                backed_up.append((backup_target, target))

            for directory in _DATA_DIRS:
                destination = f"{prefix}/{directory}"
                os.makedirs(os.path.dirname(destination), exist_ok=True)
                os.replace(f"{tmpd}/{directory}", destination)
                installed.append(destination)

            for name in ("lima", "limactl"):
                destination = f"{into}/{name}"
                os.replace(f"{tmpd}/bin/{name}", destination)
                installed.append(destination)

            missing = _missing_required_payload(prefix)
            if missing:
                raise RuntimeError(
                    f"Installed Lima release is incomplete: {', '.join(missing)}"
                )
            if expected_version is not None:
                installed_version = _installed_version(into)
                if installed_version != expected_version:
                    raise RuntimeError(
                        f"Installed Lima reported {installed_version}, expected "
                        f"{expected_version}"
                    )
        except BaseException as error:
            rollback_errors = []
            for target in reversed(installed):
                try:
                    _remove_managed_path(target)
                except OSError as rollback_error:
                    rollback_errors.append(str(rollback_error))
            for backup_target, target in reversed(backed_up):
                try:
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    os.replace(backup_target, target)
                except OSError as rollback_error:
                    rollback_errors.append(str(rollback_error))
            if rollback_errors:
                raise RuntimeError(
                    f"Lima installation failed: {error}. Could not restore "
                    f"the previous installation: {'; '.join(rollback_errors)}. "
                    f"Previous files remain in {backup}."
                ) from error
            shutil.rmtree(backup)
            raise
        shutil.rmtree(backup)


def _staged_version(prefix: str) -> str | None:
    versions = []
    for name in ("lima", "limactl"):
        try:
            env = (
                {"LIMACTL": f"{prefix}/bin/limactl"} if name == "lima" else None
            )
            stdout = proc.run(
                (f"{prefix}/bin/{name}", "--version"), stdout=True, env=env
            )
        except RuntimeError:
            return None
        words = stdout.strip().split()
        if not words:
            return None
        versions.append(words[-1])
    return versions[0] if versions[0] == versions[1] else "/".join(versions)


def _installed_version(binroot: str) -> str | None:
    if any(
        shutil.which(name, path=binroot) != f"{binroot}/{name}"
        for name in ("lima", "limactl")
    ):
        return None
    versions = []
    for name in ("lima", "limactl"):
        try:
            env = {"LIMACTL": f"{binroot}/limactl"} if name == "lima" else None
            stdout = proc.run(
                (f"{binroot}/{name}", "--version"), stdout=True, env=env
            )
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

    _install(
        cfg[SYSTEM_MACHINE],
        cfg[f"{SYSTEM_MACHINE}_sha256"],
        binroot,
        expected_version=version,
    )

    installed_version = _installed_version(binroot)
    if installed_version != version:
        raise SystemExit(
            f"Failed to install Lima {version}! Found: {installed_version}"
        )


def install(version: str, url: str, sha256: str, reporoot: str) -> None:
    install_global()
