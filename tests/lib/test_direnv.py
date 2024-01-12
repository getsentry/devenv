from __future__ import annotations

from unittest.mock import call
from unittest.mock import patch

from devenv.constants import bin_root
from devenv.constants import home
from devenv.lib.direnv import _sha256
from devenv.lib.direnv import _version
from devenv.lib.direnv import install


# imo this is enough coverage (as in just keeping it to bash + darwin-arm64)
# we just want to verify that the important functions were called like fs_idempotent_add
def test_install() -> None:
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
        assert mock_lib_fs_idempotent_add.mock_calls == [
            # SHELL is set in conftest.py
            call(f"{home}/.bashrc", '\neval "$(direnv hook bash)"\n')
        ]
        assert mock_archive_download.mock_calls == [
            call(
                f"https://github.com/direnv/direnv/releases/download/v{_version}/direnv.darwin-arm64",
                _sha256["direnv.darwin-arm64"],
                dest=f"{bin_root}/direnv",
            )
        ]
        assert mock_proc_run.mock_calls == [
            call((f"{bin_root}/direnv", "version"), stdout=True)
        ]
