from __future__ import annotations

import os

from devenv.constants import DARWIN
from devenv.constants import MACHINE
from devenv.lib import proc


def ensure() -> None:
    if not (DARWIN and (MACHINE == "arm64")):
        return

    # this file doesn't exist if rosetta 2 isn't installed
    # (alternatively: try arch -x86_64 ... and it should fail with "bad CPU type")
    if not os.path.exists("/Library/Apple/usr/libexec/oah/libRosettaRuntime"):
        proc.run(
            ("softwareupdate", "--install-rosetta", "--agree-to-license"),
            exit=True,
        )

    # if rosetta 2 is installed and not running, the fastest way to start
    # /usr/libexec/rosetta/oahd is to request an emulated program with /usr/bin/arch
    stdout = proc.run(
        ("/usr/bin/arch", "-x86_64", "/bin/sh", "-c", "/usr/bin/uname -m"),
        stdout=True,
    )

    # we can also verify it's actually working, compared to pgrep -f /usr/libexec/rosetta/oahd
    # this is also more precise than merely checking sysctl -n sysctl.proc_translated == 1
    if stdout.strip() != "x86_64":
        raise SystemExit(f"Rosetta 2 not working as expected.\ndebug: {stdout}")
