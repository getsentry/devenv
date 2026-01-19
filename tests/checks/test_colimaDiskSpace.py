from __future__ import annotations

from unittest import mock

from devenv.checks import colimaDiskSpace
from devenv.lib import colima


def test_check_skipped_when_colima_down() -> None:
    with mock.patch.object(
        colima, "check", return_value=colima.ColimaStatus.DOWN
    ):
        assert colimaDiskSpace.check() == (True, "")


def test_check_skipped_when_colima_unhealthy() -> None:
    with mock.patch.object(
        colima, "check", return_value=colima.ColimaStatus.UNHEALTHY
    ):
        assert colimaDiskSpace.check() == (True, "")


def test_check_passes_when_disk_has_space() -> None:
    with mock.patch.object(
        colima, "check", return_value=colima.ColimaStatus.UP
    ), mock.patch(
        "devenv.checks.colimaDiskSpace.proc.run", return_value="Use%\n 50%"
    ):
        assert colimaDiskSpace.check() == (True, "")


def test_check_passes_at_90_percent() -> None:
    with mock.patch.object(
        colima, "check", return_value=colima.ColimaStatus.UP
    ), mock.patch(
        "devenv.checks.colimaDiskSpace.proc.run", return_value="Use%\n 90%"
    ):
        assert colimaDiskSpace.check() == (True, "")


def test_check_fails_when_disk_full() -> None:
    with mock.patch.object(
        colima, "check", return_value=colima.ColimaStatus.UP
    ), mock.patch(
        "devenv.checks.colimaDiskSpace.proc.run", return_value="Use%\n 95%"
    ):
        ok, msg = colimaDiskSpace.check()
        assert ok is False
        assert "95% full" in msg
        assert "less than 10% free" in msg


def test_check_fails_at_91_percent() -> None:
    with mock.patch.object(
        colima, "check", return_value=colima.ColimaStatus.UP
    ), mock.patch(
        "devenv.checks.colimaDiskSpace.proc.run", return_value="Use%\n 91%"
    ):
        ok, msg = colimaDiskSpace.check()
        assert ok is False


def test_check_skipped_on_df_error() -> None:
    with mock.patch.object(
        colima, "check", return_value=colima.ColimaStatus.UP
    ), mock.patch(
        "devenv.checks.colimaDiskSpace.proc.run",
        side_effect=RuntimeError("command failed"),
    ):
        assert colimaDiskSpace.check() == (True, "")


def test_fix_returns_instructions() -> None:
    ok, msg = colimaDiskSpace.fix()
    assert ok is False
    assert "colima stop" in msg
    assert "colima start --disk 200" in msg
    assert "docker system prune" in msg
