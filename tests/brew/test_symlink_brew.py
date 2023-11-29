from __future__ import annotations

from unittest.mock import patch

from devenv.lib.brew import symlink_brew


def test_symlink_brew() -> None:
    # Mock the necessary dependencies
    homebrew_repo = "/path/to/homebrew/repo"
    homebrew_bin = "/path/to/homebrew/bin"

    with patch.multiple(
        "devenv.lib.brew",
        homebrew_repo=homebrew_repo,
        homebrew_bin=homebrew_bin,
    ), patch("os.symlink") as mock_symlink:
        symlink_brew()
        mock_symlink.assert_called_once_with(
            f"{homebrew_repo}/bin/brew", f"{homebrew_bin}/brew"
        )
