from __future__ import annotations

import os

from devenv.lib import proc


def packages() -> list[str]:
    # note: brew leaves will not print out top-level casks unfortunately
    stdout = proc.run(
        ("brew", "list"),
        exit=True,
        env={
            **os.environ,
            "HOMEBREW_NO_AUTO_UPDATE": "1",
            "HOMEBREW_NO_INSTALLED_DEPENDENTS_CHECK": "1",
            "HOMEBREW_NO_INSTALL_CLEANUP": "1",
            "HOMEBREW_NO_ANALYTICS": "1",
        },
        stdout=True,
    )
    return stdout.split()
