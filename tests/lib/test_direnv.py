from __future__ import annotations

from unittest.mock import call
from unittest.mock import patch

from devenv.constants import home
from devenv.constants import root
from devenv.lib.direnv import _sha256
from devenv.lib.direnv import _version
from devenv.lib.direnv import install


def test_install() -> None:
    with (
        patch("devenv.lib.direnv.MACHINE", "arm64"),
        patch("devenv.lib.direnv.sys.platform", "darwin"),
        patch("devenv.lib.archive.download") as mock_archive_download,
        patch("devenv.lib.fs.idempotent_add") as mock_lib_fs_idempotent_add,
        patch("os.chmod"),
        patch("devenv.lib.direnv.shutil.which", return_value=None),
        patch(
            "devenv.lib.direnv.proc.run", side_effect=[_version]
        ) as mock_proc_run,
    ):
        install()
        assert mock_lib_fs_idempotent_add.mock_calls == [
            # SHELL is set in conftest.py
            call(f"{home}/.bashrc", '\neval "$(direnv hook bash)"\n')
        ]
        assert mock_archive_download.mock_calls == [
            call(
                f"https://github.com/direnv/direnv/releases/download/v{_version}/direnv.darwin-arm64",
                _sha256["direnv.darwin-arm64"],
                dest=f"{root}/bin/direnv",
            )
        ]
        assert mock_proc_run.mock_calls == [
            call((f"{root}/bin/direnv", "version"), stdout=True)
        ]


def test_install_skips_when_direnv_is_already_on_path() -> None:
    with (
        patch("devenv.lib.direnv.shutil.which", return_value="/usr/bin/direnv"),
        patch("devenv.lib.archive.download") as download,
        patch("devenv.lib.fs.idempotent_add") as add,
    ):
        install()

    download.assert_not_called()
    add.assert_not_called()
