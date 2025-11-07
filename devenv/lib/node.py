from __future__ import annotations

import json
import os
import shutil
import tempfile

from devenv.lib import archive
from devenv.lib import fs
from devenv.lib import proc


_shims = ("node", "npm", "npx")


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

    for shim in (*_shims, "pnpm"):
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


def installed_pnpm(version: str, binroot: str) -> bool:
    if shutil.which(
        "pnpm", path=binroot
    ) != f"{binroot}/pnpm" or not os.path.exists(
        f"{binroot}/node-env/bin/pnpm"
    ):
        return False

    stdout = proc.run((f"{binroot}/pnpm", "--version"), stdout=True)
    installed_version = stdout.strip()
    return version == installed_version


def install_pnpm(reporoot: str) -> None:
    binroot = fs.ensure_binroot(reporoot)

    with open(f"{reporoot}/package.json") as f:
        package_json = json.load(f)
        pnpm = package_json["packageManager"]
        pnpm_version = pnpm.split("@")[-1]

    if installed_pnpm(pnpm_version, binroot):
        return

    print(f"installing pnpm {pnpm_version}...")

    # {binroot}/npm is a devenv-managed shim, so
    # this install -g ends up putting pnpm into
    # .devenv/bin/node-env/bin/pnpm which is pointed
    # to by the {binroot}/pnpm shim
    proc.run(
        (f"{binroot}/npm", "install", "-g", f"pnpm@{pnpm_version}"), stdout=True
    )

    fs.write_script(
        f"{binroot}/pnpm",
        """#!/bin/sh
export PATH={binroot}/node-env/bin:"${{PATH}}"
export NPM_CONFIG_PREFIX={binroot}/node-env
exec {binroot}/node-env/bin/pnpm "$@"
""",
        shell_escape={"binroot": binroot},
    )


def install(version: str, url: str, sha256: str, reporoot: str) -> None:
    binroot = fs.ensure_binroot(reporoot)

    if installed(version, binroot):
        return

    print(f"installing node {version}...")
    uninstall(binroot)
    _install(url, sha256, binroot)

    # NPM_CONFIG_PREFIX is needed to ensure npm install -g pnpm
    # puts pnpm into our node-env.
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
