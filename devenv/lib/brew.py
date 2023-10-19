from __future__ import annotations

import os
from shutil import which

from devenv.constants import INTEL_MAC
from devenv.lib import fs
from devenv.lib import proc

homebrew_repo = "/opt/homebrew"
homebrew_bin = f"{homebrew_repo}/bin/brew"

if INTEL_MAC:
    homebrew_repo = "/usr/local/Homebrew"
    homebrew_bin = "/usr/local/bin/brew"


def install() -> None:
    # idempotent: skip if brew is on the executing shell's path,
    #             and it resolves to the expected location
    if which("brew") == homebrew_bin:
        return

    shellrc = fs.shellrc()
    print("You may be prompted for your password to install homebrew.")
    while True:
        dirs = homebrew_repo
        if INTEL_MAC:
            dirs = f"{dirs} /usr/local/Cellar /usr/local/Caskroom /usr/local/Frameworks /usr/local/bin /usr/local/etc /usr/local/include /usr/local/lib /usr/local/opt /usr/local/sbin /usr/local/share /usr/local/var"  # noqa: E501
        try:
            proc.run(
                (
                    "sudo",
                    "bash",
                    "-c",
                    f"""
mkdir -p {dirs}
chown {os.environ['USER']} {dirs}
""",
                ),
                exit=False,
            )
        except RuntimeError:
            continue
        break

    proc.run(
        (
            "git",
            "-C",
            homebrew_repo,
            "clone",
            # homebrew works without any previous history as updating is just pulling
            "--depth=1",
            "https://github.com/Homebrew/brew",
            ".",
        ),
    )

    if INTEL_MAC:
        os.symlink(f"{homebrew_repo}/bin/brew", homebrew_bin)

    out = proc.run((homebrew_bin, "shellenv"))
    fs.idempotent_add(shellrc, out)
