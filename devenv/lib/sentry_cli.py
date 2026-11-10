from __future__ import annotations

import gzip
import os
import shutil
import tempfile

from devenv.constants import SYSTEM_MACHINE
from devenv.constants import home
from devenv.constants import homebrew_bin
from devenv.constants import root
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
}


def _installed() -> bool:
    # Where the CLI's own installer (curl and brew) and devenv put it.
    # Don't look on PATH: in a sentry checkout, .venv/bin/sentry is
    # sentry's own server CLI.
    return any(
        os.path.exists(f"{d}/sentry")
        for d in (
            f"{root}/bin",
            f"{home}/.local/bin",
            f"{home}/bin",
            f"{home}/.sentry/bin",
            homebrew_bin,
        )
    )


def install() -> None:
    if _installed():
        return

    binroot = f"{root}/bin"
    name, sha256 = _assets[SYSTEM_MACHINE]
    url = f"https://github.com/getsentry/toolkit/releases/download/cli@{_version}/{name}"

    print(f"installing sentry cli {_version}...")
    with tempfile.TemporaryDirectory() as tmpd:
        downloaded = archive.download(url, sha256, dest=f"{tmpd}/{name}")
        binary = f"{tmpd}/sentry"
        with gzip.open(downloaded, "rb") as src, open(binary, "wb") as dst:
            shutil.copyfileobj(src, dst)
        os.chmod(binary, 0o775)

        # setup copies the binary into SENTRY_INSTALL_DIR and records it
        # as a curl install, so `sentry cli upgrade` updates it in place.
        # devenv already puts binroot on PATH.
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
            env={"SENTRY_INSTALL_DIR": binroot},
        )

    version = proc.run((f"{binroot}/sentry", "--version"), stdout=True)
    if version != _version:
        raise SystemExit(
            f"Failed to install sentry cli {_version}! Found: {version}"
        )
