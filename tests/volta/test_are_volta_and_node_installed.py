from __future__ import annotations

from unittest.mock import call
from unittest.mock import patch

from devenv.lib.volta import are_volta_and_node_installed


def test_are_volta_and_node_installed(tmp_path: str) -> None:
    with patch.multiple(
        "devenv.lib.volta",
        root=str(tmp_path),
        VOLTA_HOME=f"{str(tmp_path)}/volta",
    ):
        with patch("devenv.lib.volta.which") as mock_which:
            mock_which.side_effect = [
                f"{str(tmp_path)}/bin/volta",
                f"{str(tmp_path)}/volta/bin/node",
            ]
            are_volta_and_node_installed(f"{str(tmp_path)}/bin")
            assert mock_which.call_args_list == [
                call("volta", path=f"{str(tmp_path)}/bin"),
                call("node", path=f"{str(tmp_path)}/volta/bin"),
            ]
