from __future__ import annotations

from unittest import mock

from devenv.checks import colimaSve
from devenv.lib import colima


def test_check_ok() -> None:
    with mock.patch.object(colima, "vm_misreports_sve", return_value=False):
        assert colimaSve.check() == (True, "")


def test_check_misreported() -> None:
    with mock.patch.object(colima, "vm_misreports_sve", return_value=True):
        assert colimaSve.check() == (
            False,
            "colima's VM kernel reports SVE2, but this CPU has no SVE. "
            "Programs that use it crash with 'Illegal instruction'.",
        )


def test_check_colima_not_running() -> None:
    # another check reports that, and its fix starts colima,
    # which fixes this too
    with mock.patch.object(
        colima,
        "vm_misreports_sve",
        side_effect=RuntimeError("Command `colima ssh` failed! (code 1)"),
    ):
        assert colimaSve.check() == (True, "")


def test_fix() -> None:
    with (
        mock.patch.object(
            colima, "start", return_value=colima.ColimaStatus.UP
        ) as start,
        mock.patch.object(colima, "vm_misreports_sve", return_value=False),
    ):
        assert colimaSve.fix() == (True, "")
    start.assert_called_once_with(restart=True)


def test_fix_didnt_take() -> None:
    # e.g. apt couldn't reach the mirror, which start only warns about
    with (
        mock.patch.object(colima, "start", return_value=colima.ColimaStatus.UP),
        mock.patch.object(colima, "vm_misreports_sve", return_value=True),
    ):
        assert colimaSve.fix() == (
            False,
            "colima's VM still misreports SVE, see above",
        )


def test_fix_unhealthy() -> None:
    with mock.patch.object(
        colima, "start", return_value=colima.ColimaStatus.UNHEALTHY
    ):
        assert colimaSve.fix() == (False, "colima is unhealthy")
