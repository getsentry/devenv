from __future__ import annotations

import os
from subprocess import CalledProcessError
from subprocess import run


def packages() -> list[str]:
    # note: brew leaves will not print out top-level casks unfortunately
    try:
        proc = run(
            ("brew", "list"),
            check=True,
            capture_output=True,
            env={
                **os.environ,
                "HOMEBREW_NO_AUTO_UPDATE": "1",
                "HOMEBREW_NO_INSTALLED_DEPENDENTS_CHECK": "1",
                "HOMEBREW_NO_INSTALL_CLEANUP": "1",
                "HOMEBREW_NO_ANALYTICS": "1",
            },
        )
        leaves = proc.stdout.decode().split()
    except CalledProcessError as e:
        raise SystemExit(f"brew failed: {e.stderr}")
    return leaves
