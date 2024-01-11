from __future__ import annotations

import os
import subprocess
from unittest.mock import call
from unittest.mock import patch

from devenv import main
from tests.utils import chdir


def test(tmp_path: str) -> None:
    coderoot = f"{tmp_path}/coderoot"
    configroot = f"{tmp_path}/configroot"

    with patch("devenv.main.CI", True), patch("sentry_sdk.init"), patch(
        "devenv.main.config_root", configroot
    ), patch("devenv.bootstrap.main") as mock_bootstrap, patch(
        "devenv.sync.main"
    ) as mock_sync:
        main.DEFAULT_CONFIG["devenv"]["coderoot"] = coderoot
        main.devenv(("/path/to/argv0", "bootstrap"))
        with open(f"{configroot}/config.ini", "r") as f:
            assert (
                f.read()
                == f"""[devenv]
# please enter the root directory you want to work in
coderoot = {coderoot}

"""
            )
            assert mock_bootstrap.mock_calls == [call(coderoot, [])]

        # with our config written, let's mock a repo then call sync
        repo = "repo"
        reporoot = f"{coderoot}/repo"
        os.makedirs(reporoot)
        subprocess.run(("git", "init", "--quiet", "--bare", reporoot))
        with chdir(reporoot), patch(
            "os.makedirs", wraps=os.makedirs
        ) as os_makedirs:
            main.devenv(("/path/to/argv0", "sync"))

            # this time, we should have early returned from initialize_config
            # so only the os.makedirs call to coderoot should have happened
            # otherwise we would also have a call(configroot, exist_ok=True)
            assert os_makedirs.mock_calls == [call(coderoot, exist_ok=True)]
            assert mock_sync.mock_calls == [
                call({"repo": repo, "reporoot": reporoot}, [])
            ]
