from __future__ import annotations

import os
import shutil
import tempfile

from devenv.lib import archive
from devenv.lib import fs
from devenv.lib import proc


_shims = ("node", "npm", "npx", "yarn", "pnpm")


def _install(url: str, sha256: str, into: str) -> None:
    os.makedirs(into, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=into) as tmpd:
        archive_file = archive.download(url, sha256, dest=f"{tmpd}/download")
        top_level_dir = "node-env"
        archive.unpack(
            archive_file,
            tmpd,
            perform_strip1=True,
            strip1_new_prefix=top_level_dir,
        )

        # the archive was atomically placed into tmpd so
        # these are on the same fs and can be atomically moved too
        os.replace(f"{tmpd}/{top_level_dir}", f"{into}/{top_level_dir}")


def uninstall(binroot: str) -> None:
    shutil.rmtree(f"{binroot}/node-env", ignore_errors=True)

    for shim in (*_shims, "yarn"):
        fp = f"{binroot}/{shim}"
        try:
            os.remove(fp)
        except FileNotFoundError:
            # it's better to do this than to guard with
            # os.path.exists(fp) because if it's an invalid or circular
            # symlink the result'll be False!
            pass


def installed(version: str, binroot: str) -> bool:
    if shutil.which(
        "node", path=binroot
    ) != f"{binroot}/node" or not os.path.exists(
        f"{binroot}/node-env/bin/node"
    ):
        return False

    with open(f"{binroot}/node", "r") as f:
        sample = f.read(64)
        if "VOLTA_HOME" in sample:
            print("volta-based node detected")
            return False

    try:
        stdout = proc.run((f"{binroot}/node", "--version"), stdout=True)
    except RuntimeError:
        print("installed node failed to start!")
        return False
    else:
        installed_version = stdout.strip()
        if version == installed_version:
            return True

        print(f"installed node {installed_version} is unexpected!")
        return False


def install(version: str, url: str, sha256: str, reporoot: str) -> None:
    binroot = fs.ensure_binroot(reporoot)

    if installed(version, binroot):
        return

    print(f"installing node {version}...")
    uninstall(binroot)
    _install(url, sha256, binroot)

    # NPM_CONFIG_PREFIX is needed to ensure npm install -g yarn
    # puts yarn into our node-env.

    for shim in _shims:
        fs.write_script(
            f"{binroot}/{shim}",
            """#!/bin/sh
export PATH={binroot}/node-env/bin:"${{PATH}}"
export NPM_CONFIG_PREFIX={binroot}/node-env
exec {binroot}/node-env/bin/{shim} "$@"
""",
            shell_escape={"binroot": binroot, "shim": shim},
        )

    if not installed(version, binroot):
        raise SystemExit(f"failed to install node {version}!")


def installed_yarn(version: str, binroot: str) -> bool:
    if shutil.which(
        "yarn", path=binroot
    ) != f"{binroot}/yarn" or not os.path.exists(
        f"{binroot}/node-env/bin/yarn"
    ):
        return False

    with open(f"{binroot}/yarn", "r") as f:
        sample = f.read(64)
        if "VOLTA_HOME" in sample:
            print("volta-based yarn detected")
            return False

    stdout = proc.run((f"{binroot}/yarn", "--version"), stdout=True)
    installed_version = stdout.strip()
    if version == installed_version:
        return True

    print(f"installed yarn {installed_version} is unexpected!")
    return False


def install_yarn(version: str, reporoot: str) -> None:
    binroot = fs.ensure_binroot(reporoot)

    if installed_yarn(version, binroot):
        return

    # not explicitly uninstalling here, following steps
    # will pave over it
    print(f"installing yarn {version}...")

    proc.run((f"{binroot}/npm", "install", "-g", f"yarn@{version}"))

    fs.write_script(
        f"{binroot}/yarn",
        """#!/bin/sh
export PATH={binroot}/node-env/bin:"${{PATH}}"
exec {binroot}/node-env/bin/yarn "$@"
""",
        shell_escape={"binroot": binroot},
    )

    if not installed_yarn(version, binroot):
        raise SystemExit(f"failed to install yarn {version}!")
