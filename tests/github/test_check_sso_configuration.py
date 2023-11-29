from __future__ import annotations

from unittest.mock import patch

from devenv.lib.github import check_sso_configuration


def test_check_sso_configuration_success(tmp_path: str) -> None:
    with patch("devenv.lib.github.proc.run"):
        assert check_sso_configuration()


def test_check_sso_configuration_failure(tmp_path: str) -> None:
    error = RuntimeError("Failed to clone private repos")

    with patch("devenv.lib.github.proc.run", side_effect=[error]), patch(
        "builtins.print"
    ) as mock_print:
        assert not check_sso_configuration()
        mock_print.assert_called_once_with(error)
