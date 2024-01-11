from __future__ import annotations

from unittest.mock import patch

from devenv.lib.brew import add_brew_to_shellrc
from devenv.lib.brew import create_dirs
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
        "devenv.lib.brew.DARWIN", True
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
        "devenv.lib.brew.DARWIN", True
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


def test_add_brew_to_shellrc() -> None:
    # Mock the necessary dependencies
    shellrc_path = "/path/to/shellrc"
    homebrew_bin = "/path/to/homebrew/bin"

    with patch(
        "devenv.lib.brew.fs.shellrc", return_value=shellrc_path
    ) as mock_shellrc, patch(
        "devenv.lib.brew.fs.idempotent_add"
    ) as mock_idempotent_add, patch(
        "devenv.lib.brew.homebrew_bin", homebrew_bin
    ):
        add_brew_to_shellrc()

        mock_shellrc.assert_called_once()
        mock_idempotent_add.assert_called_once_with(
            shellrc_path, f'\neval "$({homebrew_bin}/brew shellenv)"\n'
        )


def test_create_dirs() -> None:
    # Mock the necessary dependencies
    homebrew_repo = "/path/to/homebrew/repo"
    user = "test_user"
    INTEL_MAC = False

    # Mock the proc.run function
    with patch("devenv.lib.brew.proc.run") as mock_run, patch.multiple(
        "devenv.lib.brew",
        user=user,
        homebrew_repo=homebrew_repo,
        INTEL_MAC=INTEL_MAC,
    ):
        create_dirs()

        # Assert that proc.run was called with the correct arguments
        mock_run.assert_called_once_with(
            (
                "sudo",
                "bash",
                "-c",
                f"""
mkdir -p {homebrew_repo}
chown {user} {homebrew_repo}
""",
            ),
            exit=False,
        )


def test_create_dirs_intel_mac() -> None:
    # Mock the necessary dependencies
    homebrew_repo = "/path/to/homebrew/repo"
    user = "test_user"
    INTEL_MAC = True

    # Mock the proc.run function
    with patch("devenv.lib.brew.proc.run") as mock_run, patch.multiple(
        "devenv.lib.brew",
        user=user,
        homebrew_repo=homebrew_repo,
        INTEL_MAC=INTEL_MAC,
    ):
        create_dirs()

        # Assert that proc.run was called with the correct arguments
        mock_run.assert_called_once_with(
            (
                "sudo",
                "bash",
                "-c",
                f"""
mkdir -p {homebrew_repo} /usr/local/Cellar /usr/local/Caskroom /usr/local/Frameworks /usr/local/bin /usr/local/etc /usr/local/include /usr/local/lib /usr/local/opt /usr/local/sbin /usr/local/share /usr/local/var
chown {user} {homebrew_repo} /usr/local/Cellar /usr/local/Caskroom /usr/local/Frameworks /usr/local/bin /usr/local/etc /usr/local/include /usr/local/lib /usr/local/opt /usr/local/sbin /usr/local/share /usr/local/var
""",
            ),
            exit=False,
        )
