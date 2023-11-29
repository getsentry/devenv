from __future__ import annotations

from unittest.mock import patch

from devenv.lib.brew import install


def test_install_brew_already_installed() -> None:
    with patch(
        "devenv.lib.brew.which", return_value="/usr/local/bin/brew"
    ), patch("devenv.lib.brew.create_dirs") as mock_create_dirs, patch(
        "devenv.lib.brew.clone_brew"
    ) as mock_clone_brew, patch(
        "devenv.lib.brew.symlink_brew"
    ) as mock_symlink_brew, patch(
        "devenv.lib.brew.add_brew_to_shellrc"
    ) as mock_add_brew_to_shellrc:
        install()
        mock_create_dirs.assert_not_called()
        mock_clone_brew.assert_not_called()
        mock_symlink_brew.assert_not_called()
        mock_add_brew_to_shellrc.assert_not_called()


def test_install_brew_not_installed_intel_mac() -> None:
    with patch("devenv.lib.brew.which", return_value=None), patch(
        "devenv.lib.brew.create_dirs"
    ) as mock_create_dirs, patch(
        "devenv.lib.brew.clone_brew"
    ) as mock_clone_brew, patch(
        "devenv.lib.brew.symlink_brew"
    ) as mock_symlink_brew, patch(
        "devenv.lib.brew.add_brew_to_shellrc"
    ) as mock_add_brew_to_shellrc, patch(
        "devenv.lib.brew.INTEL_MAC", True
    ):
        install()
        mock_create_dirs.assert_called_once()
        mock_clone_brew.assert_called_once()
        mock_symlink_brew.assert_called_once()
        mock_add_brew_to_shellrc.assert_called_once()


def test_install_brew_not_installed_non_intel_mac() -> None:
    with patch("devenv.lib.brew.which", return_value=None), patch(
        "devenv.lib.brew.create_dirs"
    ) as mock_create_dirs, patch(
        "devenv.lib.brew.clone_brew"
    ) as mock_clone_brew, patch(
        "devenv.lib.brew.symlink_brew"
    ) as mock_symlink_brew, patch(
        "devenv.lib.brew.add_brew_to_shellrc"
    ) as mock_add_brew_to_shellrc, patch(
        "devenv.lib.brew.INTEL_MAC", False
    ):
        install()
        mock_create_dirs.assert_called_once()
        mock_clone_brew.assert_called_once()
        # We don't symlink brew on non-Intel Macs
        mock_symlink_brew.assert_not_called()
        mock_add_brew_to_shellrc.assert_called_once()
