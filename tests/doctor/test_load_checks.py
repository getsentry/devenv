from __future__ import annotations

import os

import pytest

from devenv import doctor


def test_load_checks_no_checks() -> None:
    assert doctor.load_checks({"reporoot": "not a real path"}, set()) == []


def test_load_checks_test_checks(capsys: pytest.CaptureFixture[str]) -> None:
    loaded_checks = doctor.load_checks(
        {"reporoot": os.path.join(os.path.dirname(__file__))}, set()
    )
    loaded_check_names = [check.name for check in loaded_checks]
    assert len(loaded_check_names) == 5
    assert "passing check" in loaded_check_names
    assert "failing check" in loaded_check_names
    assert "failing check with msg" in loaded_check_names
    assert "broken check" in loaded_check_names
    assert "broken fix" in loaded_check_names
    captured = capsys.readouterr()
    assert (
        captured.out
        == """⚠️ Skipping bad_check: `check(...)` should return a tuple of (bool, str)
⚠️ Skipping bad_fix: `fix(...)` should return a tuple of (bool, str)
⚠️ Skipping no_check: must have a `check` function
⚠️ Skipping no_name: missing the `name` attribute
⚠️ Skipping no_tags: missing the `tags` attribute\n"""
    )


def test_load_checks_only_passing_tag() -> None:
    loaded_checks = doctor.load_checks(
        {"reporoot": os.path.join(os.path.dirname(__file__))}, {"pass"}
    )
    loaded_check_names = [check.name for check in loaded_checks]
    assert len(loaded_check_names) == 1
    assert "passing check" in loaded_check_names


def test_load_checks_only_failing_tag() -> None:
    loaded_checks = doctor.load_checks(
        {"reporoot": os.path.join(os.path.dirname(__file__))}, {"fail"}
    )
    loaded_check_names = [check.name for check in loaded_checks]
    assert len(loaded_check_names) == 2
    assert "failing check" in loaded_check_names
    assert "failing check with msg" in loaded_check_names


def test_load_checks_passing_and_failing_tag() -> None:
    loaded_checks = doctor.load_checks(
        {"reporoot": os.path.join(os.path.dirname(__file__))}, {"pass", "fail"}
    )
    loaded_check_names = [check.name for check in loaded_checks]
    assert len(loaded_check_names) == 0


def test_load_checks_test_tag() -> None:
    loaded_checks = doctor.load_checks(
        {"reporoot": os.path.join(os.path.dirname(__file__))}, {"test"}
    )
    loaded_check_names = [check.name for check in loaded_checks]
    assert len(loaded_check_names) == 5
    assert "passing check" in loaded_check_names
    assert "failing check" in loaded_check_names
    assert "failing check with msg" in loaded_check_names
    assert "broken check" in loaded_check_names
    assert "broken fix" in loaded_check_names
