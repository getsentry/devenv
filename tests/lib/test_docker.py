from __future__ import annotations

import socket
from collections.abc import Sequence
from unittest.mock import patch

from devenv.lib import docker


def _fake_docker_run(args: Sequence[str]) -> int:
    # stands in for the container: nc's port is the last word of the command
    port = int(args[-1].split()[-1])
    with socket.create_connection(("127.0.0.1", port)):
        pass
    return 0


def test_check_docker_to_host_connectivity_pins_context() -> None:
    with patch(
        "devenv.lib.docker.subprocess.call", side_effect=_fake_docker_run
    ) as mock_call:
        assert docker.check_docker_to_host_connectivity(context="colima")

    # the current context may be "default" (see colima.start), whose
    # /var/run/docker.sock usually doesn't exist on colima-only machines
    assert mock_call.call_args.args[0][:3] == (
        "docker",
        "--context=colima",
        "run",
    )


def test_check_docker_to_host_connectivity_fails() -> None:
    with patch("devenv.lib.docker.subprocess.call", return_value=1):
        assert not docker.check_docker_to_host_connectivity(context="colima")
