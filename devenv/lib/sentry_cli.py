from __future__ import annotations

import gzip
import os
import shutil
import tempfile

from devenv.constants import SYSTEM_MACHINE
from devenv.constants import home
from devenv.constants import root
from devenv.constants import user_environ
from devenv.lib import archive
from devenv.lib import proc

# The Sentry CLI (https://cli.sentry.dev) upgrades itself, so this pin only
# sets the version for new installs.
_version = "0.49.0"

_assets = {
    "darwin_arm64": (
        "sentry-darwin-arm64.gz",
        "40ddc80ecfd3da4bb106a9199734f9e07baa7bcc03d945f6ec2ac4ee10714bb6",
    ),
    "darwin_x86_64": (
        "sentry-darwin-x64.gz",
        "ba44f32bdc2fbfe40b139fb201f40ba116191239b339e20191f0890a824c8f6c",
    ),
    "linux_aarch64": (
        "sentry-linux-arm64.gz",
        "776711626b059d13d4bf319d2982b6fa60f406b562dd02b8d0645c7fe9c394e7",
    ),
    "linux_x86_64": (
        "sentry-linux-x64.gz",
        "e8eede9626bc07cfd880ee21c2ab6d86ad979f61583ca18c5ccedd10668c6e81",
    ),
}


def _install_dir() -> str:
    # Mirrors the CLI's own install dir resolution (determineInstallDir),
    # so devenv and the CLI's installer agree on where it lives.
    if d := user_environ.get("SENTRY_INSTALL_DIR"):
        return d
    xdg_bin_home = user_environ.get("XDG_BIN_HOME", "")
    if os.path.isabs(xdg_bin_home):
        return xdg_bin_home
    path = {
        os.path.normpath(p) for p in user_environ.get("PATH", "").split(":")
    }
    for d in (f"{home}/.local/bin", f"{home}/bin"):
        if os.path.isdir(d) and d in path:
            return d
    return f"{home}/.local/bin"


def _install(into: str) -> None:
    name, sha256 = _assets[SYSTEM_MACHINE]
    url = f"https://github.com/getsentry/toolkit/releases/download/cli@{_version}/{name}"

    print(f"installing sentry cli {_version} into {into}...")
    with tempfile.TemporaryDirectory() as tmpd:
        downloaded = archive.download(url, sha256, dest=f"{tmpd}/{name}")
        binary = f"{tmpd}/sentry"
        with gzip.open(downloaded, "rb") as src, open(binary, "wb") as dst:
            shutil.copyfileobj(src, dst)
        os.chmod(binary, 0o775)

        # setup copies the binary into SENTRY_INSTALL_DIR and records it
        # as a curl install, so `sentry cli upgrade` updates it in place.
        # devenv links it into its own bin, which is already on PATH.
        proc.run(
            (
                binary,
                "cli",
                "setup",
                "--install",
                "--method",
                "curl",
                "--channel",
                "stable",
                "--no-modify-path",
                "--quiet",
            ),
            env={"SENTRY_INSTALL_DIR": into},
        )

    version = proc.run((f"{into}/sentry", "--version"), stdout=True)
    if version != _version:
        raise SystemExit(
            f"Failed to install sentry cli {_version}! Found: {version}"
        )


def install() -> None:
    into = _install_dir()
    binary = f"{into}/sentry"
    # An existing install updates itself, so leave it be.
    if not os.path.exists(binary):
        _install(into)

    link = f"{root}/bin/sentry"
    if os.path.realpath(into) == os.path.realpath(f"{root}/bin"):
        return
    if os.path.islink(link) and os.readlink(link) == binary:
        return
    if os.path.lexists(link):
        os.remove(link)
    os.symlink(binary, link)
