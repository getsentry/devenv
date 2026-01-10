from __future__ import annotations

import shutil
import sys

from devenv.lib import colima
from devenv.lib import docker
from devenv.lib import proc
from devenv.lib_check.types import checker
from devenv.lib_check.types import fixer

tags: set[str] = {"builtin"}
name = "colima's DNS isn't working"


def is_using_colima() -> bool:
    """Check if we're using Colima."""
    if not shutil.which("colima"):
        return False
    # If Docker works without colima, we're not using Colima
    if docker.is_docker_available():
        try:
            stdout = proc.run(("docker", "context", "show"), stdout=True)
            return stdout.strip() == "colima"
        except RuntimeError:
            return False
    return False


@checker
def check() -> tuple[bool, str]:
    # Skip this check if not using Colima
    if not is_using_colima():
        return True, ""

    # dns resolution can... stop working if colima's running
    # and wifi changes to some other network that gives macos some
    # weird nameservers

    status = colima.check()
    if status != colima.ColimaStatus.UP:
        return False, "Colima isn't running."

    try:
        proc.run(
            (
                "colima",
                "exec",
                "--",
                "python3",
                "-Su",
                "-c",
                """
import socket

try:
    socket.getaddrinfo("ghcr.io", None)
except socket.gaierror as e:
    raise SystemExit(f"failed to resolve ghcr.io: {e}")
""",
            ),
            stdout=True,
        )
    except RuntimeError as e:
        return False, f"{e}"

    return True, ""


@fixer
def fix() -> tuple[bool, str]:
    status = colima.start()
    if status == colima.ColimaStatus.UNHEALTHY:
        return False, "colima started, but it's unhealthy"

    try:
        proc.run(
            (
                "colima",
                "exec",
                "--",
                "sudo",
                "systemctl",
                "restart",
                "systemd-resolved.service",
            ),
            stdout=True,
        )
    except RuntimeError as e:
        print(
            f"""
failed to restart the vm's resolved:
{e}

we're going to try restarting colima
"""
        )
        try:
            proc.run(
                (sys.executable, "-P", "-m", "devenv", "colima", "restart")
            )
        except RuntimeError as e:
            return False, f"{e}"

    return True, ""
