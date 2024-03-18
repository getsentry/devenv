from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor

import pytest

from devenv import doctor
from tests.utils import import_module_from_file

here = os.path.join(os.path.dirname(__file__))


def test_run_checks_no_checks() -> None:
    assert doctor.run_checks([], ThreadPoolExecutor()) == {}


def test_run_checks_one_passing_check() -> None:
    passing_check = import_module_from_file(
        f"{here}/checks/passing_check.py", "passing_check"
    )

    check = doctor.Check(passing_check)
    assert doctor.run_checks([check], ThreadPoolExecutor()) == {
        check: (True, "")
    }


def test_run_checks_one_failing_check() -> None:
    failing_check = import_module_from_file(
        f"{here}/checks/failing_check.py", "failing_check"
    )

    check = doctor.Check(failing_check)
    assert doctor.run_checks([check], ThreadPoolExecutor()) == {
        check: (False, "")
    }


def test_run_checks_one_failing_check_with_msg() -> None:
    failing_check_with_msg = import_module_from_file(
        f"{here}/checks/failing_check_with_msg.py", "failing_check_with_msg"
    )

    check = doctor.Check(failing_check_with_msg)
    assert doctor.run_checks([check], ThreadPoolExecutor()) == {
        check: (False, "check failed")
    }


def test_run_checks_one_passing_and_one_failing_check() -> None:
    passing_check = import_module_from_file(
        f"{here}/checks/passing_check.py", "passing_check"
    )
    failing_check = import_module_from_file(
        f"{here}/checks/failing_check.py", "failing_check"
    )

    first_check = doctor.Check(passing_check)
    second_check = doctor.Check(failing_check)
    assert doctor.run_checks(
        [first_check, second_check], ThreadPoolExecutor()
    ) == {first_check: (True, ""), second_check: (False, "")}


def test_run_checks_skip(capsys: pytest.CaptureFixture[str]) -> None:
    passing_check = import_module_from_file(
        f"{here}/checks/passing_check.py", "passing_check"
    )
    failing_check = import_module_from_file(
        f"{here}/checks/failing_check.py", "failing_check"
    )

    first_check = doctor.Check(passing_check)
    second_check = doctor.Check(failing_check)
    assert doctor.run_checks(
        [first_check, second_check], ThreadPoolExecutor(), skip=[second_check]
    ) == {first_check: (True, "")}
    captured = capsys.readouterr()
    assert captured.out == "    ⏭️  Skipped failing check\n"


def test_run_checks_multiple_failing_checks() -> None:
    failing_check = import_module_from_file(
        f"{here}/checks/failing_check.py", "failing_check"
    )
    failing_check_with_msg = import_module_from_file(
        f"{here}/checks/failing_check_with_msg.py", "failing_check_with_msg"
    )

    first_check = doctor.Check(failing_check)
    second_check = doctor.Check(failing_check_with_msg)
    assert doctor.run_checks(
        [first_check, second_check], ThreadPoolExecutor()
    ) == {first_check: (False, ""), second_check: (False, "check failed")}


def test_run_checks_broken_check() -> None:
    broken_check = import_module_from_file(
        f"{here}/checks/broken_check.py", "broken_check"
    )

    check = doctor.Check(broken_check)
    assert doctor.run_checks([check], ThreadPoolExecutor()) == {
        check: (False, "Check threw a runtime exception: division by zero")
    }
