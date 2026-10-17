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


def _write_post_fetch(config_path: pathlib.Path) -> None:
    config_path.mkdir(parents=True)
    (config_path / "config.ini").write_text("")
    (config_path / "post_fetch.py").write_text(
        "def main(context):\n"
        "    open(context['reporoot'] + '/ran', 'w').close()\n"
        "    return 0\n"
    )


def test_post_fetch_from_dot_devenv(tmp_path: pathlib.Path) -> None:
    _write_post_fetch(tmp_path / "repo" / ".devenv")

    fetch.fetch(str(tmp_path), "repo", sync=False)

    assert (tmp_path / "repo" / "ran").exists()


def test_post_fetch_from_devenv(tmp_path: pathlib.Path) -> None:
    _write_post_fetch(tmp_path / "repo" / "devenv")

    fetch.fetch(str(tmp_path), "repo", sync=False)

    assert (tmp_path / "repo" / "ran").exists()
