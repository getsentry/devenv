from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor

from devenv import doctor
from tests.utils import import_module_from_file

here = os.path.join(os.path.dirname(__file__))


def test_attempt_fix_success() -> None:
    passing_check = import_module_from_file(
        f"{here}/checks/passing_check.py", "passing_check"
    )

    check = doctor.Check(passing_check)
    assert doctor.attempt_fix(check, ThreadPoolExecutor()) == (True, "")


def test_attempt_fix_failure() -> None:
    failing_check = import_module_from_file(
        f"{here}/checks/failing_check.py", "failing_check"
    )

    check = doctor.Check(failing_check)
    assert doctor.attempt_fix(check, ThreadPoolExecutor()) == (False, "")


def test_attempt_fix_failure_with_msg() -> None:
    failing_check_with_msg = import_module_from_file(
        f"{here}/checks/failing_check_with_msg.py", "failing_check_with_msg"
    )

    check = doctor.Check(failing_check_with_msg)
    assert doctor.attempt_fix(check, ThreadPoolExecutor()) == (
        False,
        "fix failed",
    )


def test_attempt_fix_broken_fix() -> None:
    broken_fix = import_module_from_file(
        f"{here}/checks/broken_fix.py", "broken_fix"
    )

    check = doctor.Check(broken_fix)
    assert doctor.attempt_fix(check, ThreadPoolExecutor()) == (
        False,
        "Fix threw a runtime exception: division by zero",
    )
