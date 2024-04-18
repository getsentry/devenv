from __future__ import annotations

import os
import subprocess
from unittest.mock import call
from unittest.mock import patch

from devenv import main
from devenv.lib import config
from devenv.lib.config import DEFAULT_CONFIG
from tests.utils import chdir


def _test(tmp_path: str) -> None:
    with patch("devenv.constants.CI", True), patch(
        "devenv.bootstrap.main"
    ) as mock_bootstrap, patch("devenv.sync.main") as mock_sync:
        config_path = f"{tmp_path}/.config/sentry-devenv/config.ini"
        coderoot = f"{tmp_path}/code"
        DEFAULT_CONFIG["devenv"]["coderoot"] = coderoot

        config.initialize_config(config_path, DEFAULT_CONFIG)

        main.devenv(("/path/to/argv0", "bootstrap"), config_path)
        assert mock_bootstrap.mock_calls == [call({}, [])]

        with open(config_path, "r") as f:
            assert (
                f.read()
                == f"""[devenv]
coderoot = {coderoot}

"""
            )

        # with our config written, let's mock a repo then call sync
        repo = "sentry"
        reporoot = f"{coderoot}/sentry"
        os.makedirs(reporoot)
        subprocess.run(("git", "init", "--quiet", "--bare", reporoot))
        with chdir(reporoot), patch(
            "os.makedirs", wraps=os.makedirs
        ) as os_makedirs:
            main.devenv(("/path/to/argv0", "sync"), config_path)

            # this time, we should have early returned from initialize_config
            # so only the os.makedirs call to coderoot should have happened
            # otherwise we would also have a call(configroot, exist_ok=True)
            assert os_makedirs.mock_calls == [call(coderoot, exist_ok=True)]
            assert mock_sync.mock_calls == [
                call({"repo": repo, "reporoot": reporoot}, [])
            ]
