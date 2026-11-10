from __future__ import annotations

import gzip
import os
from collections.abc import Callable
from collections.abc import Generator
from unittest.mock import call
from unittest.mock import patch

import pytest

from devenv.lib import sentry_cli


def _fake_download(url: str, sha256: str, dest: str) -> str:
    with gzip.open(dest, "wb") as f:
        f.write(b"binary")
    return dest


def _fake_run(version: str) -> Callable[..., str | None]:
    def run(
        cmd: tuple[str, ...],
        *,
        env: dict[str, str] | None = None,
        stdout: bool = False,
    ) -> str | None:
        if cmd[1:3] != ("cli", "setup"):
            return version
        # what `sentry cli setup --install` does: copy itself into the dir
        assert env is not None
        os.makedirs(env["SENTRY_INSTALL_DIR"], exist_ok=True)
        open(f"{env['SENTRY_INSTALL_DIR']}/sentry", "w").close()
        return None

    return run


@pytest.fixture
def dirs(tmp_path: str) -> Generator[tuple[str, str], None, None]:
    home = f"{tmp_path}/home"
    root = f"{tmp_path}/root"
    os.makedirs(f"{root}/bin")
    with (
        patch("devenv.lib.sentry_cli.home", home),
        patch("devenv.lib.sentry_cli.root", root),
        patch("devenv.lib.sentry_cli.user_environ", {"PATH": "/usr/bin"}),
    ):
        yield home, root


def test_install(dirs: tuple[str, str]) -> None:
    home, root = dirs
    into = f"{home}/.local/bin"
    name, sha256 = sentry_cli._assets["darwin_arm64"]

    with (
        patch("devenv.lib.sentry_cli.SYSTEM_MACHINE", "darwin_arm64"),
        patch(
            "devenv.lib.sentry_cli.archive.download", side_effect=_fake_download
        ) as download,
        patch(
            "devenv.lib.sentry_cli.proc.run",
            side_effect=_fake_run(sentry_cli._version),
        ) as mock_run,
    ):
        sentry_cli.install()

    url = f"https://github.com/getsentry/toolkit/releases/download/cli@{sentry_cli._version}/{name}"
    assert download.call_args.args == (url, sha256)

    setup, version = mock_run.mock_calls
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
    assert setup.kwargs == {"env": {"SENTRY_INSTALL_DIR": into}}
    # the temp binary is cleaned up once setup has copied it
    assert not os.path.exists(setup.args[0][0])
    assert version == call((f"{into}/sentry", "--version"), stdout=True)
    assert os.readlink(f"{root}/bin/sentry") == f"{into}/sentry"


def test_install_fails_on_unexpected_version(dirs: tuple[str, str]) -> None:
    with (
        patch("devenv.lib.sentry_cli.SYSTEM_MACHINE", "linux_x86_64"),
        patch(
            "devenv.lib.sentry_cli.archive.download", side_effect=_fake_download
        ),
        patch("devenv.lib.sentry_cli.proc.run", side_effect=_fake_run("0.0.1")),
        pytest.raises(SystemExit, match="Found: 0.0.1"),
    ):
        sentry_cli.install()


def test_existing_install_is_only_linked(dirs: tuple[str, str]) -> None:
    home, root = dirs
    into = f"{home}/custom"
    os.makedirs(into)
    open(f"{into}/sentry", "w").close()
    # a stale link from an earlier install dir
    os.symlink(f"{home}/.local/bin/sentry", f"{root}/bin/sentry")

    with (
        patch(
            "devenv.lib.sentry_cli.user_environ", {"SENTRY_INSTALL_DIR": into}
        ),
        patch("devenv.lib.sentry_cli.archive.download") as download,
        patch("devenv.lib.sentry_cli.proc.run") as run,
    ):
        sentry_cli.install()

    download.assert_not_called()
    run.assert_not_called()
    assert os.readlink(f"{root}/bin/sentry") == f"{into}/sentry"


@pytest.mark.parametrize(
    ("environ", "expected"),
    (
        ({"SENTRY_INSTALL_DIR": "/opt/sentry"}, "/opt/sentry"),
        ({"XDG_BIN_HOME": "/xdg/bin"}, "/xdg/bin"),
        ({"XDG_BIN_HOME": "relative"}, "{home}/.local/bin"),
        ({"PATH": "{home}/bin:/usr/bin"}, "{home}/bin"),
        ({"PATH": "/usr/bin"}, "{home}/.local/bin"),
    ),
)
def test_install_dir(
    dirs: tuple[str, str], environ: dict[str, str], expected: str
) -> None:
    home, _ = dirs
    os.makedirs(f"{home}/bin")
    environ = {k: v.format(home=home) for k, v in environ.items()}
    with patch("devenv.lib.sentry_cli.user_environ", environ):
        assert sentry_cli._install_dir() == expected.format(home=home)
