from __future__ import annotations

import pathlib
from unittest.mock import patch

from devenv import fetch


def test_defaults_to_getsentry_organization(tmp_path: pathlib.Path) -> None:
    with patch("devenv.fetch.proc.run") as run:
        fetch.fetch(str(tmp_path), "repo", sync=False)

    run.assert_called_once_with(
        ("git", "-C", str(tmp_path), "clone", "git@github.com:getsentry/repo"),
        exit=True,
    )
