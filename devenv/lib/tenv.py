from __future__ import annotations

import os
import shutil
import tempfile

from devenv.lib import archive
from devenv.lib import fs
from devenv.lib import proc

# binaries shipped inside the tenv archive, extracted into TENV_ROOT/bin
BINARIES = ("tenv", "tofu", "terraform", "terragrunt", "tf")

# the subset we put on PATH as shims. `tf` is left out because repos ship
# their own `tf` wrapper and our shim would shadow it.
SHIMS = tuple(binary for binary in BINARIES if binary != "tf")

# This makes sure we're executing with our custom TENV_ROOT, otherwise
# there's potential for collision with ~/.tenv. This isolation also makes
# uninstallation safe.
SHIM = """#!/bin/sh
export TENV_ROOT={TENV_ROOT}
exec {TENV_ROOT}/bin/{binary} "$@"
"""


def _install(url: str, sha256: str, into: str) -> None:
    TENV_ROOT = f"{into}/tenv-root"
    os.makedirs(f"{TENV_ROOT}/bin", exist_ok=True)

    with tempfile.TemporaryDirectory(dir=into) as tmpd:
        archive_file = archive.download(url, sha256, dest=f"{tmpd}/download")
        archive.unpack(archive_file, tmpd)

        # the archive was atomically placed into tmpd so
        # these are on the same fs and can be atomically moved too
        #
        # those all need to go inside a bin instead of like,
        # TENV_ROOT/terraform because tenv wants to mkdir that
        for binary in BINARIES:
            os.replace(f"{tmpd}/{binary}", f"{TENV_ROOT}/bin/{binary}")

    for binary in SHIMS:
        fs.write_script(
            f"{into}/{binary}",
            SHIM,
            shell_escape={"TENV_ROOT": TENV_ROOT, "binary": binary},
        )


def uninstall(binroot: str) -> None:
    # the shims go first: interrupted here, the next sync sees no tenv on
    # PATH and reinstalls cleanly. the other order strands shims pointing
    # at a tenv-root that's already gone.
    for binary in SHIMS:
        try:
            os.remove(f"{binroot}/{binary}")
        except FileNotFoundError:
            # it's better to do this than to guard with
            # os.path.exists(fp) because if it's an invalid or circular
            # symlink the result'll be False!
            pass

    shutil.rmtree(f"{binroot}/tenv-root", ignore_errors=True)


def _missing_shims(binroot: str) -> tuple[str, ...]:
    return tuple(
        binary
        for binary in SHIMS
        if not os.path.exists(f"{binroot}/{binary}")
        or not os.path.exists(f"{binroot}/tenv-root/bin/{binary}")
    )


def _version(binpath: str) -> str:
    try:
        stdout = proc.run((binpath, "version"), stdout=True)
    except RuntimeError:
        # a shim whose TENV_ROOT is gone exits 126, and a truncated or
        # wrong-arch binary won't run either. either way it's reinstallable,
        # so don't take the whole sync down with us.
        return ""
    # tenv version v1.3.0
    return stdout.split()[-1]


def install(version: str, url: str, sha256: str, reporoot: str) -> None:
    binroot = fs.ensure_binroot(reporoot)
    binpath = f"{binroot}/tenv"

    if shutil.which("tenv", path=binroot) == binpath:
        missing = _missing_shims(binroot)
        if missing:
            print(f"tenv {version} is missing {', '.join(missing)}...")
        else:
            installed_version = _version(binpath)
            if version == installed_version:
                return
            print(f"installed tenv {installed_version} is unexpected!")

    print(f"installing tenv {version}...")
    uninstall(binroot)
    _install(url, sha256, binroot)

    installed_version = _version(binpath)
    if version != installed_version:
        raise SystemExit(f"Failed to install tenv {version}!")
