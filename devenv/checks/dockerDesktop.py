from __future__ import annotations

import shutil
import time

from devenv.constants import DARWIN
from devenv.lib import docker
from devenv.lib import proc
from devenv.lib_check.types import checker
from devenv.lib_check.types import fixer

tags: set[str] = {"builtin"}
name = "docker desktop shouldn't conflict with colima"


def docker_desktop_is_running() -> bool:
    if not DARWIN:
        # On Linux, Docker Desktop detection is different and we allow it
        return False
    procs = proc.run(("/bin/ps", "-Ac", "-o", "comm"), stdout=True)
    return "Docker Desktop" in procs.split("\n")


def is_using_colima() -> bool:
    """Check if we're using Colima (colima is installed and Docker context is colima)."""
    if not shutil.which("colima"):
        return False
    # If Docker works without colima context, user is on native Docker
    if docker.is_docker_available():
        try:
            # Check if current context is colima
            stdout = proc.run(("docker", "context", "show"), stdout=True)
            return stdout.strip() == "colima"
        except RuntimeError:
            return False
    return False


@checker
def check() -> tuple[bool, str]:
    # Skip this check if user is using Docker Desktop (not Colima)
    if not is_using_colima():
        return True, ""

    if docker_desktop_is_running():
        return (
            False,
            "Docker Desktop is running, which conflicts with colima. "
            "Either stop Docker Desktop to use Colima, or switch to Docker Desktop.",
        )

    return True, ""


@fixer
def fix() -> tuple[bool, str]:
    if not DARWIN:
        return True, ""

    # regular pkill won't stop the Docker Desktop UI,
    # it'll just spin. the proper way to terminate it
    # without SIGKILL is to use osascript.
    print("Attempting to stop Docker Desktop.")
    try:
        proc.run(("osascript", "-e", 'quit app "Docker Desktop"'))
    except RuntimeError as e:
        return False, f"failed to quit Docker Desktop:\n{e}\n"

    # osascript doesn't wait to make sure it finishes quitting
    # so let's block for up to 5 secs
    for _ in range(10):
        time.sleep(0.5)
        if not docker_desktop_is_running():
            return True, ""

    return False, "Docker Desktop is taking too long to quit... try again?"
