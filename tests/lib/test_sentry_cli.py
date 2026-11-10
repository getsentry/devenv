from __future__ import annotations

import gzip
import os
from unittest.mock import call
from unittest.mock import patch

import pytest

from devenv.constants import root
from devenv.lib import sentry_cli


def _fake_download(url: str, sha256: str, dest: str) -> str:
    with gzip.open(dest, "wb") as f:
        f.write(b"binary")
    return dest


def test_install() -> None:
    name, sha256 = sentry_cli._assets["darwin_arm64"]
    with (
        patch("devenv.lib.sentry_cli.SYSTEM_MACHINE", "darwin_arm64"),
        patch("devenv.lib.sentry_cli._installed", return_value=False),
        patch(
            "devenv.lib.sentry_cli.archive.download",
            side_effect=_fake_download,
        ) as download,
        patch(
            "devenv.lib.sentry_cli.proc.run",
            side_effect=[None, sentry_cli._version],
        ) as run,
    ):
        sentry_cli.install()

    url = f"https://github.com/getsentry/toolkit/releases/download/cli@{sentry_cli._version}/{name}"
    assert download.call_args.args == (url, sha256)

    setup, version = run.mock_calls
    binary = setup.args[0][0]
    assert setup.args[0][1:] == (
        "cli",
        "setup",
        "--install",
        "--method",
        "curl",
        "--channel",
        "stable",
        "--no-modify-path",
        "--quiet",
    )
    assert setup.kwargs == {"env": {"SENTRY_INSTALL_DIR": f"{root}/bin"}}
    # the temp binary is cleaned up once setup has copied it
    assert not os.path.exists(binary)
    assert version == call((f"{root}/bin/sentry", "--version"), stdout=True)


def test_install_fails_on_unexpected_version() -> None:
    with (
        patch("devenv.lib.sentry_cli.SYSTEM_MACHINE", "darwin_arm64"),
        patch("devenv.lib.sentry_cli._installed", return_value=False),
        patch(
            "devenv.lib.sentry_cli.archive.download",
            side_effect=_fake_download,
        ),
        patch("devenv.lib.sentry_cli.proc.run", side_effect=[None, "0.0.1"]),
        pytest.raises(SystemExit, match="Found: 0.0.1"),
    ):
        sentry_cli.install()


def test_install_skips_existing_install(tmp_path: str) -> None:
    bindir = f"{tmp_path}/.local/bin"
    os.makedirs(bindir)
    open(f"{bindir}/sentry", "w").close()

    with (
        patch("devenv.lib.sentry_cli.home", str(tmp_path)),
        patch("devenv.lib.sentry_cli.archive.download") as download,
        patch("devenv.lib.sentry_cli.proc.run") as run,
    ):
        sentry_cli.install()

    download.assert_not_called()
    run.assert_not_called()
