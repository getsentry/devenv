from __future__ import annotations

import os
import pathlib
from unittest.mock import patch

from devenv.lib import node
from devenv.lib.repository import Repository


def test_install_pnpm(tmp_path: pathlib.Path) -> None:
    repo = Repository(f"{tmp_path}/test")

    binroot = f"{repo.path}/.devenv/bin"
    os.makedirs(binroot)
    open(f"{binroot}/node", "w").close()

    with patch("devenv.lib.archive.download"), patch(
        "devenv.lib.archive.unpack",
        side_effect=lambda archive_file, tmpd, perform_strip1, strip1_new_prefix: os.makedirs(
            f"{tmpd}/{strip1_new_prefix}"
        ),
    ), patch("devenv.lib.node.os.path.exists"), patch(
        "devenv.lib.direnv.proc.run", side_effect=["0.0.0"]  # node --version
    ):
        node.install("0.0.0", "bar", "baz", repo.path)

    with open(f"{binroot}/npm", "r") as f:
        text = f.read()
        assert (
            text
            == f"""#!/bin/sh
export PATH={binroot}/node-env/bin:"${{PATH}}"
export NPM_CONFIG_PREFIX={binroot}/node-env
exec {binroot}/node-env/bin/npm "$@"
"""
        )
