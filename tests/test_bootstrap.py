from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from devenv import bootstrap


def test() -> None:
    with patch("devenv.lib.github.add_to_known_hosts") as mock_add_to_known_hosts, patch("devenv.lib.github.check_ssh_access", side_effect=(False, True)) as mock_check_ssh_access, patch("devenv.lib.github.generate_and_configure_ssh_keypair") as mock_generate_and_configure_ssh_keypair, patch("devenv.lib.brew.install") as mock_brew_install, patch("devenv.lib.volta.install") as mock_volta_install, patch("devenv.lib.direnv.install") as mock_direnv_install:
        bootstrap.main(coderoot="", argv=("sentry",))
        mock_add_to_known_hosts.assert_called_once()
        mock_generate_and_configure_ssh_keypair.assert_called_once()
