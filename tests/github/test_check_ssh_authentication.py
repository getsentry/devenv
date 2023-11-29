from __future__ import annotations

from unittest.mock import patch

from devenv.lib.github import check_ssh_authentication


def test_check_ssh_authentication_success() -> None:
    with patch(
        "devenv.lib.github.proc.run",
        side_effect=[RuntimeError("You've successfully authenticated")],
    ):
        assert check_ssh_authentication()


def test_check_ssh_authentication_failure() -> None:
    with patch(
        "devenv.lib.github.proc.run",
        side_effect=[RuntimeError("Authentication failed")],
    ):
        assert not check_ssh_authentication()
