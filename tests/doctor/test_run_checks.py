from __future__ import annotations

from devenv import doctor
from devenv.tests.doctor.devenv.checks import failing_check
from devenv.tests.doctor.devenv.checks import passing_check


def test_run_checks_no_checks() -> None:
    assert doctor.run_checks([], doctor.ThreadPoolExecutor()) == {}


def test_run_checks_one_passing_check() -> None:
    check = doctor.Check(passing_check)
    assert doctor.run_checks([check], doctor.ThreadPoolExecutor()) == {
        check: (True, "")
    }


def test_run_checks_one_failing_check() -> None:
    check = doctor.Check(failing_check)
    assert doctor.run_checks([check], doctor.ThreadPoolExecutor()) == {
        check: (False, "")
    }


def test_run_checks_one_passing_and_one_failing_check() -> None:
    first_check = doctor.Check(passing_check)
    second_check = doctor.Check(failing_check)
    assert doctor.run_checks([first_check, second_check], doctor.ThreadPoolExecutor()) == {
        first_check: (True, ""),
        second_check: (False, ""),
    }


def test_run_checks_skip(capsys) -> None:
    first_check = doctor.Check(passing_check)
    second_check = doctor.Check(failing_check)
    assert doctor.run_checks(
        [first_check, second_check],
        doctor.ThreadPoolExecutor(),
        skip=[second_check],
    ) == {first_check: (True, "")}
    captured = capsys.readouterr()
    assert captured.out == "    ⏭️ Skipped failing check\n"
