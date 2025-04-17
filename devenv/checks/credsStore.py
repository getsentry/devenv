from __future__ import annotations

import json
import os
import shutil

from devenv.lib_check.types import checker
from devenv.lib_check.types import fixer

tags: set[str] = {"builtin"}
name = "credsStore fix"


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

    return True, ""


@fixer
def fix() -> tuple[bool, str]:
    try:
        with open(os.path.expanduser("~/.docker/config.json"), "rb") as f:
            config = json.load(f)

        config.pop("credsStore", None)

        with open(os.path.expanduser("~/.docker/config.json"), "w") as f:
            json.dump(config, f)
    except Exception as e:
        return False, f"{e}"

    return True, ""
