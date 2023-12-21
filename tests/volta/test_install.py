from __future__ import annotations

import os
from unittest.mock import call
from unittest.mock import patch

from devenv.lib.volta import _version
from devenv.lib.volta import install


def test_install(tmp_path: str) -> None:
    VOLTA_HOME = f"{tmp_path}/volta"
    os.makedirs(f"{tmp_path}/bin")
    os.makedirs(f"{VOLTA_HOME}/bin")
    for executable in ("node", "npm", "npx", "yarn", "pnpm"):
        open(f"{VOLTA_HOME}/bin/{executable}", "a").close()

    with patch.multiple(
        "devenv.lib.volta", root=tmp_path, VOLTA_HOME=VOLTA_HOME
    ):
        with patch("devenv.lib.volta.which", side_effect=[None, None]), patch(
            "devenv.lib.volta.install_volta"
        ) as mock_install_volta, patch(
            "devenv.lib.volta.proc.run",
            side_effect=[None, _version],  # volta-migrate  # volta -v
        ) as mock_proc_run:
            install()

            mock_install_volta.assert_called_once_with(f"{tmp_path}/bin")
            mock_proc_run.assert_has_calls(
                [
                    call((f"{tmp_path}/bin/volta-migrate",)),
                    call((f"{tmp_path}/bin/volta", "-v"), stdout=True),
                ]
            )
            assert (
                os.readlink(f"{tmp_path}/bin/node")
                == f"{tmp_path}/volta/bin/node"
            )

    # now test already installed
    with patch.multiple(
        "devenv.lib.volta", root=tmp_path, VOLTA_HOME=VOLTA_HOME
    ), patch("devenv.lib.volta.install_volta") as mock_install_volta, patch(
        "devenv.lib.volta.which",
        side_effect=[f"{tmp_path}/bin/volta", f"{tmp_path}/volta/bin/node"],
    ):
        install()
        assert not mock_install_volta.called
