from __future__ import annotations

from unittest.mock import call
from unittest.mock import patch

from devenv.lib.volta import are_volta_and_node_installed


def test_are_volta_and_node_installed(tmp_path: str) -> None:
    with patch.multiple(
        "devenv.lib.volta", root=tmp_path, VOLTA_HOME=f"{tmp_path}/volta"
    ):
        with patch("devenv.lib.volta.which") as mock_which:
            mock_which.side_effect = [
                f"{tmp_path}/bin/volta",
                f"{tmp_path}/volta/bin/node",
            ]
            are_volta_and_node_installed(f"{tmp_path}/bin")
            assert mock_which.call_args_list == [
                call("volta", path=f"{tmp_path}/bin"),
                call("node", path=f"{tmp_path}/volta/bin"),
            ]
