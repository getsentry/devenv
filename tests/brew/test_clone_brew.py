from __future__ import annotations

from unittest.mock import patch

from devenv.lib.brew import clone_brew


def test_clone_brew() -> None:
    # Mock the necessary dependencies
    homebrew_repo = "/path/to/homebrew_repo"

    # Mock the proc.run function
    with patch("devenv.lib.brew.proc.run") as mock_run, patch(
        "devenv.lib.brew.homebrew_repo", homebrew_repo
    ):
        clone_brew()
        mock_run.assert_called_once_with(
            (
                "git",
                "-C",
                homebrew_repo,
                "clone",
                "--depth=1",
                "https://github.com/Homebrew/brew",
                ".",
            )
        )
