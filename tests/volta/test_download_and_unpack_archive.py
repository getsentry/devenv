from __future__ import annotations

from unittest.mock import patch

from devenv.lib.volta import _sha256
from devenv.lib.volta import _version
from devenv.lib.volta import download_and_unpack_archive


def test_download_and_unpack_archive() -> None:
    with patch("platform.system", return_value="Darwin"), patch(
        "platform.machine", return_value="x86_64"
    ), patch(
        "devenv.lib.volta.archive.download",
        return_value="/path/to/archive_file",
    ) as mock_download, patch(
        "devenv.lib.volta.archive.unpack"
    ) as mock_unpack:
        name = f"volta-{_version}-macos.tar.gz"
        unpack_into = "/path/to/unpack"

        # Call the function under test
        download_and_unpack_archive(name, unpack_into)

        # Assert that the mocked functions were called with the expected arguments
        mock_download.assert_called_once_with(
            (
                "https://github.com/volta-cli/volta/releases/download/"
                f"v{_version}/volta-{_version}-macos.tar.gz"
            ),
            _sha256[name],
        )
        mock_unpack.assert_called_once_with(
            "/path/to/archive_file", unpack_into
        )
