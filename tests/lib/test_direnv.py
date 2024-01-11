from __future__ import annotations

import os
from unittest import mock
from unittest.mock import call
from unittest.mock import patch


# imo this is enough coverage for such a trivial thing
def test_install() -> None:
    with mock.patch.dict(os.environ, {"SHELL": "/bin/bash"}):
        # need to import devenv first here so that SHELL can take effect
        from devenv.constants import bin_root
        from devenv.constants import home

    from devenv.lib.direnv import install
    from devenv.lib.direnv import _version
    from devenv.lib.direnv import _sha256

    with patch("devenv.lib.direnv.MACHINE", "arm64"), patch(
        "devenv.lib.direnv.sys.platform", "darwin"
    ), patch("devenv.lib.archive.download") as mock_archive_download, patch(
        "devenv.lib.fs.idempotent_add"
    ) as mock_lib_fs_idempotent_add, patch(
        "os.chmod"
    ), patch(
        "devenv.lib.direnv.proc.run", side_effect=[_version]  # direnv version
    ) as mock_proc_run:
        install()
        mock_lib_fs_idempotent_add.assert_has_calls(
            [call(f"{home}/.bashrc", '\neval "$(direnv hook bash)"\n')]
        )
        mock_archive_download.assert_has_calls(
            [
                call(
                    f"https://github.com/direnv/direnv/releases/download/v{_version}/direnv.darwin-arm64",
                    _sha256["direnv.darwin-arm64"],
                    dest=f"{bin_root}/direnv",
                )
            ]
        )
        mock_proc_run.assert_has_calls(
            [call((f"{bin_root}/direnv", "version"), stdout=True)]
        )
