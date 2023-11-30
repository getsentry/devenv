from __future__ import annotations

from unittest.mock import patch

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
