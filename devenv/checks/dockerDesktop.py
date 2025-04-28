from __future__ import annotations

import time

from devenv.lib import proc
from devenv.lib_check.types import checker
from devenv.lib_check.types import fixer

tags: set[str] = {"builtin"}
name = "docker desktop shouldn't be running"


def docker_desktop_is_running() -> bool:
    procs = proc.run(("/bin/ps", "-Ac", "-o", "comm"), stdout=True)
    return "Docker Desktop" in procs.split("\n")


@checker
def check() -> tuple[bool, str]:
    if docker_desktop_is_running():
        return (
            False,
            "Docker Desktop is running. We don't support it, and it conflicts with colima.",
        )

    return True, ""


@fixer
def fix() -> tuple[bool, str]:
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
