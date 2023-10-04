from __future__ import annotations

from devenv import doctor
from devenv.tests.doctor.devenv.checks import failing_check
from devenv.tests.doctor.devenv.checks import passing_check


def test_run_checks_no_checks() -> None:
    assert doctor.run_checks([], doctor.ThreadPoolExecutor()) == {}


def test_run_checks_one_passing_check() -> None:
    assert doctor.run_checks([passing_check], doctor.ThreadPoolExecutor()) == {
        passing_check: (True, "")
    }


def test_run_checks_one_failing_check() -> None:
    assert doctor.run_checks([failing_check], doctor.ThreadPoolExecutor()) == {
        failing_check: (False, "")
    }


def test_run_checks_one_passing_and_one_failing_check() -> None:
    assert doctor.run_checks([passing_check, failing_check], doctor.ThreadPoolExecutor()) == {
      passing_check: (True, ""),
      failing_check: (False, ""),
    }


def test_run_checks_skip(capsys) -> None:
    assert doctor.run_checks(
        [passing_check, failing_check],
        doctor.ThreadPoolExecutor(),
        skip=[failing_check],
    ) == {passing_check: (True, "")}
    captured = capsys.readouterr()
    assert captured.out == "    ⏭️ Skipped failing check\n"
