from __future__ import annotations

import os
from unittest.mock import call
from unittest.mock import patch

from devenv.lib import fs
from devenv.lib.volta import _version
from devenv.lib.volta import install


def test_install_already_installed(tmp_path: str) -> None:
    with patch.multiple(
        "devenv.lib.volta", root=tmp_path, VOLTA_HOME=f"{tmp_path}/volta"
    ), patch(
        "devenv.lib.volta.which",
        side_effect=[f"{tmp_path}/bin/volta", f"{tmp_path}/volta/bin/node"],
    ) as mock_which:
        install()
        assert mock_which.call_args_list == [
            call("volta", path=f"{tmp_path}/bin"),
            call("node", path=f"{tmp_path}/volta/bin"),
        ]


def test_install(tmp_path: str) -> None:
    with patch.multiple(
        "devenv.lib.volta", root=tmp_path, VOLTA_HOME=f"{tmp_path}/volta"
    ):
        with patch("devenv.lib.volta.which", side_effect=[None, None]), patch(
            "devenv.lib.volta.install_volta"
        ) as mock_install_volta, patch(
            "devenv.lib.volta.proc.run",
            side_effect=[None, _version],  # volta-migrate  # volta -v
        ) as mock_proc_run, patch(
            "devenv.lib.volta.os.path.exists", return_value=True
        ) as mock_path_exists, patch(
            "devenv.lib.volta.fs.idempotent_add"
        ) as mock_idempotent_add:
            install()

            mock_install_volta.assert_called_once_with(f"{tmp_path}/bin")
            mock_proc_run.assert_has_calls(
                [
                    call((f"{tmp_path}/bin/volta-migrate",)),
                    call((f"{tmp_path}/bin/volta", "-v"), stdout=True),
                ]
            )
            assert mock_idempotent_add.call_args_list == [
                call(
                    fs.shellrc(),
                    f"""\nexport VOLTA_HOME={tmp_path}/volta\nexport PATH="{tmp_path}/volta/bin:$PATH"\n""",
                )
            ]
            mock_path_exists.assert_called_once_with(
                f"{tmp_path}/volta/bin/node"
            )
            assert os.path.exists(f"{tmp_path}/volta/bin/node")
