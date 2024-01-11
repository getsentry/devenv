from __future__ import annotations

from unittest.mock import call
from unittest.mock import patch

from devenv import main
from tests.utils import chdir


def test(tmp_path: str) -> None:
    coderoot = f"{tmp_path}/coderoot"
    configroot = f"{tmp_path}/configroot"
    with patch("devenv.main.CI", True), patch("sentry_sdk.init"), patch(
        "devenv.main.config_root", configroot
    ), patch("devenv.bootstrap.main") as mock_bootstrap:
        main.DEFAULT_CONFIG["devenv"]["coderoot"] = coderoot
        main.devenv(("/path/to/argv0", "bootstrap"))
        # assert mock_makedirs.mock_calls == [
        #    call(configroot, exist_ok=True),
        #    call(coderoot, exist_ok=True),
        # ]
        with open(f"{configroot}/config.ini", "r") as f:
            assert (
                f.read()
                == f"""[devenv]
# please enter the root directory you want to work in
coderoot = {coderoot}

"""
            )
        assert mock_bootstrap.mock_calls == [call(coderoot, [])]

        # with our config written, let's call sync
        with chdir(coderoot):
            main.devenv(("/path/to/argv0", "sync"))

        # this time, we should have early returned from initialize_config
