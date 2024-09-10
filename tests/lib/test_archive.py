from __future__ import annotations

import io
import os
import pathlib
import tarfile
import time
import typing
import urllib.request
from unittest import mock

import pytest

from devenv.lib import archive


@pytest.fixture
def tar(tmp_path: pathlib.Path) -> pathlib.Path:
    plain = tmp_path.joinpath("plain")
    plain.write_text("hello world\n")

    tar = tmp_path.joinpath("tar")

    with tarfile.open(tar, "w:tar") as tarf:
        tarf.add(plain, arcname="hello.txt")

    return tar


@pytest.fixture
def tgz(tmp_path: pathlib.Path) -> pathlib.Path:
    a = tmp_path.joinpath("a")
    a.write_text("a")
    b = tmp_path.joinpath("b")
    b.write_text("b")

    tar = tmp_path.joinpath("tgz")

    with tarfile.open(tar, "w:gz") as tarf:
        # faster to arcname than to actually mkdirs in tmp_path
        tarf.add(a, arcname="foo-v1/bin/foo")
        tarf.add(b, arcname="foo-v1/baz")

    return tar


@pytest.fixture
def mock_sleep() -> typing.Generator[mock.MagicMock, None, None]:
    with mock.patch.object(time, "sleep", autospec=True) as mock_sleep:
        yield mock_sleep


def test_download(tmp_path: pathlib.Path, mock_sleep: mock.MagicMock) -> None:
    data = b"foo\n"
    data_sha256 = (
        "b5bb9d8014a0f9b1d61e21e796d78dccdf1352f23cd32812f4850b878ae4944c"
    )

    err = urllib.error.HTTPError(
        "https://example.com/foo",
        503,
        "Service Unavailable",
        "",  # type: ignore
        io.BytesIO(b""),
    )

    dest = f"{tmp_path}/a"
    with mock.patch.object(
        urllib.request,
        "urlopen",
        autospec=True,
        side_effect=(err, err, err, io.BytesIO(data)),
    ):
        archive.download("https://example.com/foo", data_sha256, dest)

    # successful download after 3 retries
    assert mock_sleep.mock_calls == [
        mock.call(1.0),
        mock.call(2.0),
        mock.call(4.0),
    ]
    with open(dest, "rb") as f:
        assert f.read() == data

    dest = f"{tmp_path}/b"
    with pytest.raises(RuntimeError) as excinfo:
        with mock.patch.object(
            urllib.request,
            "urlopen",
            autospec=True,
            side_effect=(err, err, err, err),
        ):
            archive.download("https://example.com/foo", data_sha256, dest)

    # exceeded retry limits
    assert (
        f"{excinfo.value}"
        == "Error getting https://example.com/foo: HTTP Error 503: Service Unavailable"
    )

    dest = f"{tmp_path}/b"
    with pytest.raises(RuntimeError) as excinfo:
        with mock.patch.object(
            urllib.request,
            "urlopen",
            autospec=True,
            side_effect=(io.BytesIO(data),),
        ):
            archive.download("https://example.com/foo", "wrong sha", dest)

    # sha mismatch
    assert (
        f"{excinfo.value}"
        == f"checksum mismatch for https://example.com/foo:\n- got: {data_sha256}\n- expected: wrong sha\n"
    )


def test_unpack_tar(tar: pathlib.Path, tmp_path: pathlib.Path) -> None:
    dest = tmp_path.joinpath("dest")
    archive.unpack(str(tar), str(dest))
    assert dest.joinpath("hello.txt").read_text() == "hello world\n"


def test_unpack_tgz_strip1(tgz: pathlib.Path, tmp_path: pathlib.Path) -> None:
    dest = tmp_path.joinpath("dest")
    archive.unpack(str(tgz), str(dest), perform_strip1=True)
    assert os.path.exists(f"{tmp_path}/dest/bin/foo")
    assert os.path.exists(f"{tmp_path}/dest/baz")

    dest2 = tmp_path.joinpath("dest2")
    archive.unpack(
        str(tgz), str(dest2), perform_strip1=True, strip1_new_prefix="node"
    )
    assert os.path.exists(f"{tmp_path}/dest2/node/bin/foo")
    assert os.path.exists(f"{tmp_path}/dest2/node/baz")
