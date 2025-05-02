from __future__ import annotations

import json
import os
import shutil

from devenv.lib_check.types import checker
from devenv.lib_check.types import fixer

tags: set[str] = {"builtin"}
name = "correct docker configuration"


@checker
def check() -> tuple[bool, str]:
    # When Docker Desktop is opened, it inserts "desktop" as the value
    # for credsStore. This requires docker-credential-desktop which isn't
    # generally installed. Most people don't need to login to docker anyways.
    with open(os.path.expanduser("~/.docker/config.json"), "rb") as f:
        config = json.load(f)

    store = config.get("credsStore", "")
    if store and not shutil.which(f"docker-credential-{store}"):
        return False, "credsStore requires nonexistent binary"

    # When docker-buildx is installed via brew, brew adds cliPluginsExtraDirs
    # which takes precedence over the default plugin path we rely on.
    # This ensures the devenv-managed global docker cli uses the default plugin path.
    if config.get("cliPluginsExtraDirs"):
        return (
            False,
            "cliPluginsExtraDirs exists, which overshadows the default plugin path",
        )

    return True, ""


@fixer
def fix() -> tuple[bool, str]:
    try:
        with open(os.path.expanduser("~/.docker/config.json"), "rb") as f:
            config = json.load(f)

        config.pop("credsStore", None)
        config.pop("cliPluginsExtraDirs", None)

        with open(os.path.expanduser("~/.docker/config.json"), "w") as f:
            json.dump(config, f)
    except Exception as e:
        return False, f"{e}"

    return True, ""
