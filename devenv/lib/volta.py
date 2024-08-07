from __future__ import annotations

import os
import platform
import shutil
from typing import Optional

from devenv.constants import homebrew_bin
from devenv.constants import root
from devenv.lib import archive
from devenv.lib import fs
from devenv.lib import proc

_version = "1.1.1"
_sha256 = {
    f"volta-{_version}-macos-aarch64.tar.gz": "013d419550525fa6a212c2693798f9e2e65737e887e3604b08bc15a6be737e01",
    f"volta-{_version}-macos.tar.gz": "778ccaa943de8729d91e9df02a2767b470d97e8d5551faf6d89978db6f5f3c64",
    f"volta-{_version}-linux.tar.gz": "ab14e5d50ef836f8f43b56323cfbe7ba95a004bad05450b453c5b06a0b433d7b",
}


class UnexpectedPlatformError(Exception):
    pass


def determine_platform(unpack_into: str) -> str | None:
    system = platform.system()
    if system == "Linux":
        if platform.machine() == "x86_64":
            return f"volta-{_version}-linux.tar.gz"
        else:
            proc.run(("brew", "install", "volta"), exit=True)
            proc.run(
                ("sh", "-c", f"ln -sfn {homebrew_bin}/volta* {unpack_into}/"),
                exit=True,
            )
            return None
    elif system == "Darwin":
        suffix = "-aarch64" if platform.machine() == "arm64" else ""
        return f"volta-{_version}-macos{suffix}.tar.gz"
    else:
        raise UnexpectedPlatformError(f"Unexpected OS: {platform.platform()}")


def download_and_unpack_archive(name: str, unpack_into: str) -> None:
    url = (
        "https://github.com/volta-cli/volta/releases/download/"
        f"v{_version}/{name}"
    )

    archive_file = archive.download(url, _sha256[name])
    archive.unpack(archive_file, unpack_into)


def _install(unpack_into: str) -> None:
    name = determine_platform(unpack_into)
    if name is None:
        return
    download_and_unpack_archive(name, unpack_into)


def populate_volta_home_with_shims(unpack_into: str, volta_home: str) -> None:
    # executing volta -v will populate the VOLTA_HOME directory
    # with node/npm/yarn shims
    proc.run((f"{unpack_into}/volta-migrate",), env={"VOLTA_HOME": volta_home})
    version = proc.run(
        (f"{unpack_into}/volta", "-v"),
        env={"VOLTA_HOME": volta_home},
        stdout=True,
    )
    assert version == _version, (version, _version)


def uninstall(binroot: str, volta_home: str) -> None:
    shutil.rmtree(volta_home, ignore_errors=True)

    for executable in ("node", "npm", "npx", "yarn", "pnpm"):
        fp = f"{binroot}/{executable}"
        try:
            os.remove(fp)
        except FileNotFoundError:
            # it's better to do this than to guard with
            # os.path.exists(fp) because if it's an invalid or circular
            # symlink the result'll be False!
            pass


def install(reporoot: Optional[str] = "") -> None:
    print(
        """

****************************************************************
DEPRECATION NOTICE: devenv.lib.node is superseding volta, please
use that for your node+yarn needs!
****************************************************************

"""
    )

    if reporoot:
        binroot = fs.ensure_binroot(reporoot)
        VOLTA_HOME = f"{binroot}/volta-home"
    else:
        # compatibility with devenv <= 1.4.0
        binroot = f"{root}/bin"
        os.makedirs(binroot, exist_ok=True)
        VOLTA_HOME = f"{root}/volta"

    if (
        shutil.which("volta", path=binroot) == f"{binroot}/volta"
        and shutil.which("node", path=f"{VOLTA_HOME}/bin")
        == f"{VOLTA_HOME}/bin/node"
        and os.path.exists(f"{binroot}/node")
        # <= 1.6.0 had symlinks, now we have VOLTA_HOME shims
        and not os.path.islink(f"{binroot}/node")
    ):
        return

    print(f"installing volta {_version}...")
    uninstall(binroot, VOLTA_HOME)
    _install(binroot)
    populate_volta_home_with_shims(binroot, VOLTA_HOME)

    if not os.path.exists(f"{VOLTA_HOME}/bin/node"):
        raise SystemExit("Failed to install volta!")

    for executable in ("node", "npm", "npx", "yarn", "pnpm"):
        # This forces these repo-local bins to use the repo-local
        # volta home for full containment. Otherwise, the default
        # is to use ~/.volta.
        fs.write_script(
            f"{binroot}/{executable}",
            f"""#!/bin/sh
    exec /usr/bin/env VOLTA_HOME={VOLTA_HOME} {VOLTA_HOME}/bin/{executable} "$@"
""",
        )
