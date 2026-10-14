from __future__ import annotations

from unittest import mock

import pytest

from devenv.checks import limaDns
from devenv.lib import colima


@pytest.mark.parametrize(
    ("dnsmasq_active", "service"),
    ((True, "dnsmasq.service"), (False, "systemd-resolved.service")),
)
def test_fix_restarts_the_vms_resolver(
    dnsmasq_active: bool, service: str
) -> None:
    cmds: list[tuple[str, ...]] = []

    def run(cmd: tuple[str, ...], stdout: bool = False) -> str:
        cmds.append(cmd)
        if "is-active" in cmd and not dnsmasq_active:
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
