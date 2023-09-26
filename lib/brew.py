from __future__ import annotations

import os
from shutil import which

from devenv.lib import fs
from devenv.lib import proc

homebrew_repo = "/opt/homebrew"


def install() -> None:
    # idempotent: skip if brew is on the executing shell's path,
    #             and it resolves to the expected location
    if which("brew") == f"{homebrew_repo}/bin/brew":
        return

    shellrc = fs.shellrc()
    print("You may be prompted for your password to install homebrew.")
    while True:
        try:
            proc.run(
                (
                    "sudo",
                    "bash",
                    "-c",
                    f"""
mkdir -p {homebrew_repo}
chown {os.environ['USER']} {homebrew_repo}
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

    out = proc.run(("/opt/homebrew/bin/brew", "shellenv"))
    fs.idempotent_add(shellrc, out)
