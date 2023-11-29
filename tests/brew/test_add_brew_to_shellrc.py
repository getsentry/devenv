from __future__ import annotations

from unittest.mock import patch

from devenv.lib.brew import add_brew_to_shellrc


def test_add_brew_to_shellrc() -> None:
    # Mock the necessary dependencies
    homebrew_bin = "/path/to/homebrew/bin"

    with patch("devenv.lib.brew.fs.shellrc") as mock_shellrc, patch(
        "devenv.lib.brew.fs.idempotent_add"
    ) as mock_idempotent_add, patch(
        "devenv.lib.brew.homebrew_bin", homebrew_bin
    ):
        mock_shellrc.return_value = "/path/to/shellrc"

        add_brew_to_shellrc()

        mock_shellrc.assert_called_once()
        mock_idempotent_add.assert_called_once_with(
            "/path/to/shellrc", f'\neval "$({homebrew_bin}/brew shellenv)"\n'
        )
