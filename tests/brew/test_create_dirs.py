from __future__ import annotations

from unittest.mock import patch

from devenv.lib.brew import create_dirs


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
