from __future__ import annotations

import os

from devenv import doctor


def test_load_checks_no_checks() -> None:
    assert (
        doctor.load_checks(
            {
                "reporoot": "not a real path",
            },
            set(),
        )
        == []
    )


def test_load_checks_test_checks() -> None:
    loaded_checks = doctor.load_checks(
        {
            "reporoot": os.path.join(os.path.dirname(__file__)),
        },
        set(),
    )
    loaded_check_names = [check.name for check in loaded_checks]
    assert len(loaded_check_names) == 2
    assert "passing check" in loaded_check_names
    assert "failing check" in loaded_check_names
