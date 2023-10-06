from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from devenv import doctor
from devenv.tests.doctor.devenv.checks import broken_check
from devenv.tests.doctor.devenv.checks import failing_check
from devenv.tests.doctor.devenv.checks import failing_check_with_msg
from devenv.tests.doctor.devenv.checks import passing_check


def test_run_checks_no_checks() -> None:
    assert doctor.run_checks([], ThreadPoolExecutor()) == {}


def test_run_checks_one_passing_check() -> None:
    check = doctor.Check(passing_check)
    assert doctor.run_checks([check], ThreadPoolExecutor()) == {check: (True, "")}


def test_run_checks_one_failing_check() -> None:
    check = doctor.Check(failing_check)
    assert doctor.run_checks([check], ThreadPoolExecutor()) == {check: (False, "")}


def test_run_checks_one_failing_check_with_msg() -> None:
    check = doctor.Check(failing_check_with_msg)
    assert doctor.run_checks([check], ThreadPoolExecutor()) == {check: (False, "check failed")}


def test_run_checks_one_passing_and_one_failing_check() -> None:
    first_check = doctor.Check(passing_check)
    second_check = doctor.Check(failing_check)
    assert doctor.run_checks([first_check, second_check], ThreadPoolExecutor()) == {
        first_check: (True, ""),
        second_check: (False, ""),
    }


def test_run_checks_skip(capsys) -> None:  # type: ignore
    first_check = doctor.Check(passing_check)
    second_check = doctor.Check(failing_check)
    assert doctor.run_checks(
        [first_check, second_check],
        ThreadPoolExecutor(),
        skip=[second_check],
    ) == {first_check: (True, "")}
    captured = capsys.readouterr()
    assert captured.out == "    ⏭️  Skipped failing check\n"


def test_run_checks_multiple_failing_checks() -> None:
    first_check = doctor.Check(failing_check)
    second_check = doctor.Check(failing_check_with_msg)
    assert doctor.run_checks([first_check, second_check], ThreadPoolExecutor()) == {
        first_check: (False, ""),
        second_check: (False, "check failed"),
    }


def test_run_checks_broken_check() -> None:
    check = doctor.Check(broken_check)
    assert doctor.run_checks([check], ThreadPoolExecutor()) == {
        check: (False, "Check threw a runtime exception: division by zero")
    }
