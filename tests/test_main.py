from __future__ import annotations

from unittest.mock import call
from unittest.mock import patch

from devenv import main
from devenv.constants import home


def test_bootstrap(tmp_path: str) -> None:
    configroot = tmp_path
    with patch("devenv.main.CI", True), patch("sentry_sdk.init"), patch(
        "devenv.main.config_root", configroot
    ), patch("os.makedirs") as mock_makedirs, patch(
        "devenv.bootstrap.main"
    ) as mock_bootstrap:
        main.devenv(("/path/to/argv0", "bootstrap"))
        # TODO: replace assert_has_calls with something serial, not subset check
        mock_makedirs.assert_has_calls(
            [
                call(configroot, exist_ok=True),
                call(f"{home}/code", exist_ok=True),
            ]
        )
        # TODO: assert for file contents of config.ini that defaults were written
        """[devenv]
# please enter the root directory you want to work in
coderoot = /Users/josh/dev"""

        mock_bootstrap.assert_has_calls([call(f"{home}/code", [])])


# def test_sync() -> None:
# this time let's also just write a config beforehand so we immediately return from init config
