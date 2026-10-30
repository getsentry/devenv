from __future__ import annotations

import json
import os
import shutil
import tempfile
import time

from devenv.constants import root
from devenv.lib import archive
from devenv.lib import fs
from devenv.lib import proc

_shims = ("node", "npm", "npx")

# Shared installs that no checkout has synced for this long are removed.
# A checkout still pointing at one gets it back on its next sync.
_unused_after_seconds = 30 * 24 * 60 * 60


def _install(url: str, sha256: str, into: str) -> str:
    """
    Unpacks node into {into}/{sha256} unless it's already there, and returns
    that path. It's shared by every checkout using the same node, so it must
    never be written to after this; see install for how npm is kept out of it.
    """
    dest = f"{into}/{sha256}"
    if os.path.exists(dest):
        return dest

    os.makedirs(into, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=into) as tmpd:
        archive_file = archive.download(url, sha256, dest=f"{tmpd}/download")
        archive.unpack(
            archive_file, tmpd, perform_strip1=True, strip1_new_prefix="node"
        )

        # tmpd is in the same dir as dest so this is atomic: other
        # checkouts never see a partially unpacked node
        try:
            os.replace(f"{tmpd}/node", dest)
        except OSError:
            # a concurrent sync of another checkout got there first,
            # and replacing a non-empty dir isn't allowed
            if not os.path.exists(f"{dest}/bin/node"):
                raise

    return dest


def _remove_unused(into: str, in_use: str) -> None:
    """
    Marks in_use as just used and removes the other installs in into that
    weren't used recently. Nothing records which checkouts use which
    install, so last use (the dir's mtime) is the best signal there is.
    """
    os.utime(in_use)
    cutoff = time.time() - _unused_after_seconds

    for name in os.listdir(into):
        path = f"{into}/{name}"
        if path == in_use:
            continue
        try:
            if os.stat(path).st_mtime >= cutoff:
                continue
        except FileNotFoundError:
            # a concurrent sync removed it first
            continue

        print(f"removing unused node install {path}")
        # move it out of the way first so that a sync running at the same
        # time never sees a partially removed install as a complete one
        trash = tempfile.mkdtemp(dir=into)
        try:
            os.rename(path, f"{trash}/{name}")
        except FileNotFoundError:
            # a concurrent sync removed it first
            pass
        shutil.rmtree(trash)


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

    if not os.path.islink(f"{binroot}/node-env/bin/node"):
        print("per-checkout node detected, replacing with a shared one")
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

    if not installed(version, binroot):
        _install_checkout(version, url, sha256, binroot)

    # {binroot}/node-env/bin/node -> {shared}/bin/node
    shared = os.path.dirname(
        os.path.dirname(os.readlink(f"{binroot}/node-env/bin/node"))
    )
    _remove_unused(os.path.dirname(shared), in_use=shared)


def _install_checkout(
    version: str, url: str, sha256: str, binroot: str
) -> None:
    print(f"installing node {version}...")
    uninstall(binroot)
    shared = _install(url, sha256, f"{root}/node")

    # node-env stays per-checkout because it's the npm global prefix that
    # npm install -g (e.g. install_pnpm) writes into. Only node's own
    # executables (node, npm, npx, corepack) are linked from the shared install.
    os.makedirs(f"{binroot}/node-env/bin")
    for name in os.listdir(f"{shared}/bin"):
        os.symlink(f"{shared}/bin/{name}", f"{binroot}/node-env/bin/{name}")

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
