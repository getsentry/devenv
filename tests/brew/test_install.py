from __future__ import annotations

from unittest.mock import patch

from devenv.lib.brew import install


def test_install_brew_already_installed() -> None:
    with patch(
        "devenv.lib.brew.which", return_value="/usr/local/bin/brew"
    ), patch(
        "devenv.lib.brew.add_brew_to_shellrc"
    ) as mock_add_brew_to_shellrc, patch(
        "devenv.lib.brew.proc.run"
    ) as mock_run, patch(
        "os.symlink"
    ) as mock_symlink:
        install()
        mock_run.assert_not_called()
        mock_run.assert_not_called()
        mock_symlink.assert_not_called()
        mock_add_brew_to_shellrc.assert_not_called()


def test_install_brew_not_installed_intel_mac() -> None:
    # Mock the necessary dependencies
    homebrew_repo = "/path/to/homebrew_repo"
    homebrew_bin = "/path/to/homebrew/bin"

    with patch("devenv.lib.brew.which", return_value=None), patch(
        "devenv.lib.brew.create_dirs"
    ) as mock_create_dirs, patch(
        "devenv.lib.brew.add_brew_to_shellrc"
    ) as mock_add_brew_to_shellrc, patch(
        "devenv.lib.brew.INTEL_MAC", True
    ), patch(
        "devenv.lib.brew.proc.run"
    ) as mock_run, patch(
        "os.symlink"
    ) as mock_symlink, patch.multiple(
        "devenv.lib.brew",
        homebrew_repo=homebrew_repo,
        homebrew_bin=homebrew_bin,
    ):
        install()
        mock_create_dirs.assert_called_once()
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
        mock_symlink.assert_called_once_with(
            f"{homebrew_repo}/bin/brew", f"{homebrew_bin}/brew"
        )
        mock_add_brew_to_shellrc.assert_called_once()


def test_install_brew_not_installed_non_intel_mac() -> None:
    # Mock the necessary dependencies
    homebrew_repo = "/path/to/homebrew_repo"
    homebrew_bin = "/path/to/homebrew/bin"

    with patch("devenv.lib.brew.which", return_value=None), patch(
        "devenv.lib.brew.create_dirs"
    ) as mock_create_dirs, patch(
        "devenv.lib.brew.add_brew_to_shellrc"
    ) as mock_add_brew_to_shellrc, patch(
        "devenv.lib.brew.INTEL_MAC", False
    ), patch(
        "devenv.lib.brew.proc.run"
    ) as mock_run, patch(
        "os.symlink"
    ) as mock_symlink, patch.multiple(
        "devenv.lib.brew",
        homebrew_repo=homebrew_repo,
        homebrew_bin=homebrew_bin,
    ):
        install()
        mock_create_dirs.assert_called_once()
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
        # We don't symlink brew on non-Intel Macs
        mock_symlink.assert_not_called()
        mock_add_brew_to_shellrc.assert_called_once()
