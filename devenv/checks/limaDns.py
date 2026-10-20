from __future__ import annotations

import sys

from devenv.lib import colima
from devenv.lib import proc
from devenv.lib_check.types import checker
from devenv.lib_check.types import fixer

tags: set[str] = {"builtin", "colima"}
name = "colima's DNS isn't working"


@checker
def check() -> tuple[bool, str]:
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


def _resolver_service() -> str:
    # VMs created since colima 0.9 come with dnsmasq, and colima makes it
    # their resolver instead of systemd-resolved. Check that it's installed
    # rather than running: if dnsmasq died, it's the one to restart.
    try:
        proc.run(
            ("colima", "exec", "--", "systemctl", "cat", "dnsmasq.service"),
            stdout=True,
        )
    except RuntimeError:
        return "systemd-resolved.service"
    return "dnsmasq.service"


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
                _resolver_service(),
            ),
            stdout=True,
        )
    except RuntimeError as e:
        print(f"""
failed to restart the vm's dns resolver:
{e}

we're going to try restarting colima
""")
        try:
            proc.run(
                (sys.executable, "-P", "-m", "devenv", "colima", "restart")
            )
        except RuntimeError as e:
            return False, f"{e}"

    return True, ""
