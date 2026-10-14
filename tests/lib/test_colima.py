from __future__ import annotations

from unittest.mock import patch

from devenv.lib import colima
from devenv.lib.colima import ColimaStatus


def test_start_is_a_noop_when_up() -> None:
    with (
        patch("devenv.lib.colima.check", return_value=ColimaStatus.UP),
        patch("devenv.lib.colima.proc.run") as mock_run,
    ):
        assert colima.start() == ColimaStatus.UP

    # neither restart a healthy vm nor leave docker on the "default" context
    mock_run.assert_not_called()


def test_start_switches_context_around_starting() -> None:
    with (
        patch(
            "devenv.lib.colima.check",
            side_effect=[ColimaStatus.DOWN, ColimaStatus.UP],
        ),
        patch("devenv.lib.colima.rosetta.ensure"),
        patch("devenv.lib.colima.proc.run") as mock_run,
    ):
        assert colima.start() == ColimaStatus.UP

    cmds = [c.args[0][:3] for c in mock_run.call_args_list]
    assert cmds == [
        ("docker", "context", "use"),
        ("colima", "stop", "-f"),
        ("colima", "start", "--verbose"),
        ("docker", "context", "use"),
    ]
    assert mock_run.call_args_list[0].args[0][3] == "default"
    assert mock_run.call_args_list[-1].args[0][3] == "colima"


def test_restart_when_up() -> None:
    with (
        patch(
            "devenv.lib.colima.check",
            side_effect=[ColimaStatus.UP, ColimaStatus.UP],
        ),
        patch("devenv.lib.colima.rosetta.ensure"),
        patch("devenv.lib.colima.proc.run") as mock_run,
    ):
        assert colima.restart() == ColimaStatus.UP

    cmds = [c.args[0][:2] for c in mock_run.call_args_list]
    assert ("colima", "stop") in cmds
    assert ("colima", "start") in cmds
