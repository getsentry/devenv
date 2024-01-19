from __future__ import annotations

import os
from collections.abc import Sequence
from typing import Dict

from devenv.lib import proc
from devenv.lib import venv

help = """Executes a command, using devenv's repo-specific environment.
Useful if your local environment's broken."""


def main(context: Dict[str, str], argv: Sequence[str] | None = None) -> None:
    repo = context["repo"]
    if repo not in {"sentry", "getsentry"}:
        print(f"repo {repo} not supported yet!")
        return 1

    reporoot = context["reporoot"]

    env = {**os.environ}

    venv_status = venv.check(reporoot)
    if (
        venv_status == venv.VENV_NOT_PRESENT
        or venv_status == venv.VENV_VERSION_MISMATCH
    ):
        print(
            "WARN: venv doesn't exist or isn't up to date. You should create it with devenv sync.",
            # unflushed stdout is likely to dissappear due to the imminent exec
            flush=True,
        )
    elif venv_status == venv.VENV_OK:
        # if there is a good venv, we should use it for the exec.
        env["VIRTUAL_ENV"] = f"{reporoot}/.venv"
        env["PATH"] = f"{reporoot}/.venv/bin:{proc.base_path}"

    # note: p variant of exec does in fact take env["PATH"] into
    #       account for searches (you would think we may need to
    #       also modify os.environ but it works without it)
    os.execvpe(argv[0], argv, env)
