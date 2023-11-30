from __future__ import annotations

import os
from unittest.mock import patch

from devenv.lib.github import add_to_known_hosts
from devenv.lib.github import fingerprints


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
