from devenv import doctor
from devenv.tests.doctor.devenv.checks import failing_check
from devenv.tests.doctor.devenv.checks import passing_check


def test_filter_failing_checks_no_checks() -> None:
    assert doctor.filter_failing_checks({}) == []


def test_filter_failing_checks_one_passing_check() -> None:
    assert doctor.filter_failing_checks({passing_check: (True, "")}) == []


def test_filter_failing_checks_one_failing_check() -> None:
    assert doctor.filter_failing_checks({failing_check: (False, "")}) == [failing_check]


def test_filter_failing_checks_one_passing_and_one_failing_check() -> None:
    assert doctor.filter_failing_checks(
        {passing_check: (True, ""), failing_check: (False, "")}
    ) == [failing_check]


def test_filter_failing_checks_no_duplicate_checks() -> None:
    assert doctor.filter_failing_checks(
        {
            passing_check: (True, ""),
            failing_check: (False, ""),
            failing_check: (False, ""),
        }
    ) == [failing_check]
