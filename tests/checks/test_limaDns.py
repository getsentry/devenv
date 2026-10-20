from __future__ import annotations

from unittest import mock

import pytest

from devenv.checks import limaDns
from devenv.lib import colima


@pytest.mark.parametrize(
    ("dnsmasq_installed", "dnsmasq_active", "service"),
    (
        (True, True, "dnsmasq.service"),
        # e.g. dnsmasq crashed, which is why DNS is broken
        (True, False, "dnsmasq.service"),
        # VMs created before colima 0.9
        (False, False, "systemd-resolved.service"),
    ),
)
def test_fix_restarts_the_vms_resolver(
    dnsmasq_installed: bool, dnsmasq_active: bool, service: str
) -> None:
    cmds: list[tuple[str, ...]] = []

    def run(cmd: tuple[str, ...], stdout: bool = False) -> str:
        cmds.append(cmd)
        vm_cmd = cmd[3:]
        if vm_cmd == ("systemctl", "cat", "dnsmasq.service"):
            if not dnsmasq_installed:
                raise RuntimeError("Command failed! (code 1)")
        elif vm_cmd[:2] == ("systemctl", "is-active") and not dnsmasq_active:
            raise RuntimeError("Command failed! (code 3)")
        return ""

    with (
        mock.patch.object(colima, "start", return_value=colima.ColimaStatus.UP),
        mock.patch("devenv.checks.limaDns.proc.run", side_effect=run),
    ):
        assert limaDns.fix() == (True, "")

    assert cmds[-1] == (
        "colima",
        "exec",
        "--",
        "sudo",
        "systemctl",
        "restart",
        service,
    )
