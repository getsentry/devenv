from __future__ import annotations

from devenv import doctor
from tests.doctor.devenv.checks import failing_check
from tests.doctor.devenv.checks import passing_check


def test_filter_failing_checks_no_checks() -> None:
    assert doctor.filter_failing_checks({}) == []


def test_filter_failing_checks_one_passing_check() -> None:
    check = doctor.Check(passing_check)
    assert doctor.filter_failing_checks({check: (True, "")}) == []


def test_filter_failing_checks_one_failing_check() -> None:
    check = doctor.Check(failing_check)
    assert doctor.filter_failing_checks({check: (False, "")}) == [check]


def test_filter_failing_checks_one_passing_and_one_failing_check() -> None:
    first_check = doctor.Check(passing_check)
    second_check = doctor.Check(failing_check)
    assert doctor.filter_failing_checks(
        {first_check: (True, ""), second_check: (False, "")}
    ) == [second_check]


def test_filter_failing_checks_no_duplicate_checks() -> None:
    first_check = doctor.Check(passing_check)
    second_check = doctor.Check(failing_check)
    assert doctor.filter_failing_checks(
        {
            first_check: (True, ""),
            second_check: (False, ""),
            second_check: (False, ""),
        }
    ) == [second_check]
