from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from devenv.lib.github import add_to_known_hosts
from devenv.lib.github import check_ssh_access
from devenv.lib.github import check_ssh_authentication
from devenv.lib.github import fingerprints
from devenv.lib.github import generate_and_configure_ssh_keypair


def test_generate_and_configure_ssh_keypair(tmp_path: str) -> None:
    home = tmp_path
    private_key_path = f"{home}/.ssh/sentry-github"
    public_key_path = f"{private_key_path}.pub"

    with patch("devenv.lib.github.home", home), patch(
        "devenv.lib.github.fs.idempotent_add"
    ) as mock_idempotent_add, patch(
        "devenv.lib.github.os.path.exists", return_value=False
    ) as mock_exists, patch(
        "devenv.lib.github.proc.run"
    ), patch(
        "builtins.open"
    ) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = (
            "public_key"
        )

        result = generate_and_configure_ssh_keypair()

        assert result == "public_key"
        mock_idempotent_add.assert_called_once_with(
            f"{home}/.ssh/config",
            """Host github.com
  User git
  Hostname github.com
  PreferredAuthentications publickey
  IdentityFile ~/.ssh/sentry-github""",
        )
        mock_exists.assert_called_once_with(private_key_path)
        mock_open.assert_called_once_with(public_key_path)


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


def test_check_ssh_access_success() -> None:
    with patch("devenv.lib.github.CI", False), patch(
        "devenv.lib.github.check_ssh_authentication", return_value=True
    ), patch("devenv.lib.github.check_sso_configuration", return_value=True):
        assert check_ssh_access()


def test_check_ssh_access_failure_no_ssh() -> None:
    with patch("devenv.lib.github.CI", False), patch(
        "devenv.lib.github.check_ssh_authentication", return_value=False
    ), patch("devenv.lib.github.check_sso_configuration", return_value=True):
        assert not check_ssh_access()


def test_check_ssh_access_failure_no_sso() -> None:
    with patch("devenv.lib.github.CI", False), patch(
        "devenv.lib.github.check_ssh_authentication", return_value=True
    ), patch("devenv.lib.github.check_sso_configuration", return_value=False):
        assert not check_ssh_access()


@pytest.mark.parametrize("ssh", [True, False])
@pytest.mark.parametrize("sso", [True, False])
def test_check_ssh_access_success_ci(ssh: bool, sso: bool) -> None:
    with patch("devenv.lib.github.CI", True), patch(
        "devenv.lib.github.check_ssh_authentication", return_value=ssh
    ), patch("devenv.lib.github.check_sso_configuration", return_value=sso):
        assert check_ssh_access()


@pytest.mark.parametrize("sso", [True, False])
def test_check_ssh_access_success_external_contributor(sso: bool) -> None:
    with patch("devenv.lib.github.CI", False), patch(
        "devenv.lib.github.EXTERNAL_CONTRIBUTOR", "1"
    ), patch(
        "devenv.lib.github.check_ssh_authentication", return_value=True
    ), patch(
        "devenv.lib.github.check_sso_configuration", return_value=sso
    ) as mock_check_sso_configuration:
        assert check_ssh_access()

    # If the user is an external contributor, we should not check for SSO
    mock_check_sso_configuration.assert_not_called()


def test_check_ssh_access_failure_external_contributor() -> None:
    with patch("devenv.lib.github.CI", False), patch(
        "devenv.lib.github.EXTERNAL_CONTRIBUTOR", "1"
    ), patch("devenv.lib.github.check_ssh_authentication", return_value=False):
        assert not check_ssh_access()


def test_add_to_known_hosts(tmp_path: str) -> None:
    with patch("devenv.lib.github.home", tmp_path), patch.object(
        os, "makedirs"
    ) as mock_makedirs, patch(
        "devenv.lib.brew.fs.idempotent_add"
    ) as mock_idempotent_add:
        add_to_known_hosts()

    mock_makedirs.assert_called_once_with(f"{tmp_path}/.ssh", exist_ok=True)
    mock_idempotent_add.assert_called_once_with(
        f"{tmp_path}/.ssh/known_hosts", fingerprints
    )
