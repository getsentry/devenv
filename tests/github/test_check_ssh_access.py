from __future__ import annotations

from unittest.mock import patch

import pytest

from devenv.lib.github import check_ssh_access


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
