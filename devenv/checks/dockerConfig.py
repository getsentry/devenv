from __future__ import annotations

import json
import os
import shutil

from devenv.lib import docker
from devenv.lib_check.types import checker
from devenv.lib_check.types import fixer

tags: set[str] = {"builtin"}
name = "correct docker configuration"


def is_using_colima() -> bool:
    """Check if we're using Colima (colima context is active)."""
    if not shutil.which("colima"):
        return False
    try:
        from devenv.lib import proc

        stdout = proc.run(("docker", "context", "show"), stdout=True)
        return stdout.strip() == "colima"
    except RuntimeError:
        return False


@checker
def check() -> tuple[bool, str]:
    config_path = os.path.expanduser("~/.docker/config.json")

    # If config file doesn't exist, that's fine for native Docker
    if not os.path.exists(config_path):
        return True, ""

    # When Docker Desktop is opened, it inserts "desktop" as the value
    # for credsStore. This requires docker-credential-desktop which isn't
    # generally installed. Most people don't need to login to docker anyways.
    with open(config_path, "rb") as f:
        config = json.load(f)

    store = config.get("credsStore", "")
    if store and not shutil.which(f"docker-credential-{store}"):
        return False, "credsStore requires nonexistent binary"

    # When docker-buildx is installed via brew, brew adds cliPluginsExtraDirs
    # which takes precedence over the default plugin path we rely on.
    # This ensures the devenv-managed global docker cli uses the default plugin path.
    # Only check this if using Colima (devenv-managed docker cli)
    if is_using_colima() and config.get("cliPluginsExtraDirs"):
        return (
            False,
            "cliPluginsExtraDirs exists, which overshadows the default plugin path",
        )

    # Only enforce colima context if colima is installed and Docker works via colima
    # If user has native Docker or Docker Desktop, we don't enforce colima context
    if shutil.which("colima"):
        current_context = config.get("currentContext", "")
        # If context is colima, that's expected when using Colima
        # If context is something else and Docker works, user has their own Docker
        if current_context == "colima":
            return True, ""
        # If Colima is installed but context isn't colima, check if Docker works
        # If it does, user is using native Docker and that's fine
        if docker.is_docker_available():
            return True, ""
        # Docker doesn't work and context isn't colima - this needs fixing
        return (
            False,
            f"currentContext is '{current_context}', should be 'colima'",
        )

    return True, ""


@fixer
def fix() -> tuple[bool, str]:
    config_path = os.path.expanduser("~/.docker/config.json")

    try:
        if os.path.exists(config_path):
            with open(config_path, "rb") as f:
                config = json.load(f)
        else:
            config = {}

        config.pop("credsStore", None)
        if is_using_colima():
            config.pop("cliPluginsExtraDirs", None)
            config["currentContext"] = "colima"

        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(config, f)
    except Exception as e:
        return False, f"{e}"

    return True, ""
