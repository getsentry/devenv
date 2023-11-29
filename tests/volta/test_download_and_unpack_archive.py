from __future__ import annotations

from unittest.mock import patch

from devenv.lib.volta import _sha256
from devenv.lib.volta import _version
from devenv.lib.volta import download_and_unpack_archive


def test_download_and_unpack_archive() -> None:
    with patch("devenv.lib.volta.build_url") as mock_build_url, patch(
        "devenv.lib.volta.archive.download"
    ) as mock_download, patch("devenv.lib.volta.archive.unpack") as mock_unpack:
        name = f"volta-{_version}-macos.tar.gz"
        unpack_into = "/path/to/unpack"

        # Mock the return values of the mocked functions
        mock_build_url.return_value = "http://example.com/archive"
        mock_download.return_value = "/path/to/archive_file"

        # Call the function under test
        download_and_unpack_archive(name, unpack_into)

        # Assert that the mocked functions were called with the expected arguments
        mock_build_url.assert_called_once_with(name)
        mock_download.assert_called_once_with(
            "http://example.com/archive", _sha256[name]
        )
        mock_unpack.assert_called_once_with(
            "/path/to/archive_file", unpack_into
        )
