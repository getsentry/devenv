from __future__ import annotations

import os
import shutil
import tempfile

from devenv.lib import archive
from devenv.lib import fs
from devenv.lib import proc


def _install(url: str, sha256: str, into: str) -> None:
    TENV_ROOT = f"{into}/tenv-root"
    os.makedirs(f"{TENV_ROOT}/bin", exist_ok=True)

    with tempfile.TemporaryDirectory(dir=into) as tmpd:
        archive_file = archive.download(url, sha256, dest=f"{tmpd}/download")
        archive.unpack(archive_file, tmpd)

        # the archive was atomically placed into tmpd so
        # these are on the same fs and can be atomically moved too
        os.replace(f"{tmpd}/terraform", f"{TENV_ROOT}/bin/terraform")
        os.replace(f"{tmpd}/tf", f"{TENV_ROOT}/bin/tf")
        os.replace(f"{tmpd}/terragrunt", f"{TENV_ROOT}/bin/terragrunt")
        os.replace(f"{tmpd}/tenv", f"{TENV_ROOT}/bin/tenv")

        # those all need to go inside a bin instead of like, TENV_ROOT/terraform
        # because tenv wants to mkdir that

    # These shims make sure we're executing with our custom TENV_ROOT,
    # otherwise there's potential for collision with ~/.tenv.
    # This isolation also makes uninstallation safe.
    fs.write_script(
        f"{into}/tenv",
        """#!/bin/sh
export TENV_ROOT={TENV_ROOT}
exec {TENV_ROOT}/bin/tenv "$@"
""",
        shell_escape={"TENV_ROOT": TENV_ROOT},
    )
    fs.write_script(
        f"{into}/terraform",
        """#!/bin/sh
export TENV_ROOT={TENV_ROOT}
exec {TENV_ROOT}/bin/terraform "$@"
""",
        shell_escape={"TENV_ROOT": TENV_ROOT},
    )
    fs.write_script(
        f"{into}/terragrunt",
        """#!/bin/sh
export TENV_ROOT={TENV_ROOT}
exec {TENV_ROOT}/bin/terragrunt "$@"
""",
        shell_escape={"TENV_ROOT": TENV_ROOT},
    )


def uninstall(binroot: str) -> None:
    for d in (f"{binroot}/tenv-root",):
        shutil.rmtree(d, ignore_errors=True)

    for fp in (
        f"{binroot}/tenv",
        f"{binroot}/terraform",
        f"{binroot}/terragrunt",
    ):
        try:
            os.remove(fp)
        except FileNotFoundError:
            # it's better to do this than to guard with
            # os.path.exists(fp) because if it's an invalid or circular
            # symlink the result'll be False!
            pass


def _version(binpath: str) -> str:
    stdout = proc.run((binpath, "version"), stdout=True)
    # tenv version v1.3.0
    return stdout.split()[-1]


def install(version: str, url: str, sha256: str, reporoot: str) -> None:
    binroot = fs.ensure_binroot(reporoot)
    binpath = f"{binroot}/tenv"

    if shutil.which("tenv", path=binroot) == binpath:
        installed_version = _version(binpath)
        if version == installed_version:
            return
        print(f"installed tenv {installed_version} is outdated!")

    print(f"installing tenv {version}...")
    uninstall(binroot)
    _install(url, sha256, binroot)

    installed_version = _version(binpath)
    if version != installed_version:
        raise SystemExit("Failed to install tenv {version}!")
