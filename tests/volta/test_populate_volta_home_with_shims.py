from __future__ import annotations

from unittest.mock import call
from unittest.mock import patch

from devenv.lib.volta import populate_volta_home_with_shims


def test_populate_volta_home_with_shims(tmp_path: str) -> None:
    with patch("devenv.lib.volta.proc.run") as mock_run:
        unpack_into = "/path/to/unpack"
        mock_run.side_effect = [
            None,  # mock run for volta-migrate
            "1.1.1",  # mock run for volta -v
        ]

        populate_volta_home_with_shims(unpack_into)

        mock_run.assert_has_calls(
            [
                call((f"{unpack_into}/volta-migrate",)),
                call((f"{unpack_into}/volta", "-v"), stdout=True),
            ]
        )
