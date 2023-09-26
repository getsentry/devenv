from __future__ import annotations

import os
from shutil import which

from devenv.lib import fs
from devenv.lib import proc

repo_path = "/opt/homebrew"


def install() -> None:
    if which("brew") == f"{repo_path}/bin/brew":
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
mkdir -p {repo_path}
chown {os.environ['USER']} {repo_path}
""",
                ),
                exit=False,
            )
        except RuntimeError:
            continue
        break

    if not os.path.exists(f"{repo_path}/bin/brew"):
        os.makedirs(repo_path, exist_ok=True)
        proc.run(
            (
                "git",
                "-C",
                repo_path,
                "clone",
                # homebrew works without any previous history as updating is just pulling
                "--depth=1",
                "https://github.com/Homebrew/brew",
                ".",
            ),
        )

    out = proc.run(("/opt/homebrew/bin/brew", "shellenv"))
    fs.idempotent_add(shellrc, out)
