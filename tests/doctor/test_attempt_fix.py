from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from devenv import doctor
from devenv.tests.doctor.devenv.checks import failing_check
from devenv.tests.doctor.devenv.checks import failing_check_with_msg
from devenv.tests.doctor.devenv.checks import passing_check


def test_attempt_fix_success() -> None:
    check = doctor.Check(passing_check)
    assert doctor.attempt_fix(check, ThreadPoolExecutor()) == (True, "")


def test_attempt_fix_failure() -> None:
    check = doctor.Check(failing_check)
    assert doctor.attempt_fix(check, ThreadPoolExecutor()) == (False, "")


def test_attempt_fix_failure_with_msg() -> None:
    check = doctor.Check(failing_check_with_msg)
    assert doctor.attempt_fix(check, ThreadPoolExecutor()) == (False, "fix failed")
