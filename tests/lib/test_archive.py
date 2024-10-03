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
def tar2(tmp_path: pathlib.Path) -> pathlib.Path:
    a = tmp_path.joinpath("a")
    a.write_text("")
    b = tmp_path.joinpath("b")
    b.write_text("")

    tar = tmp_path.joinpath("tar")

    with tarfile.open(tar, "w:tar") as tarf:
        tarf.add(a, arcname="foo/v1/bin/foo")
        tarf.add(b, arcname="foo/v1/baz")

    return tar


@pytest.fixture
def tar3(tmp_path: pathlib.Path) -> pathlib.Path:
    a = tmp_path.joinpath("a")
    a.write_text("")
    b = tmp_path.joinpath("b")
    b.write_text("")

    tar = tmp_path.joinpath("tar")

    with tarfile.open(tar, "w:tar") as tarf:
        tarf.add(a, arcname="foo/v1/bin/foo")
        tarf.add(b, arcname="foo/bad")

    return tar


@pytest.fixture
def tar4(tmp_path: pathlib.Path) -> pathlib.Path:
    a = tmp_path.joinpath("a")
    a.write_text("")

    tar = tmp_path.joinpath("tar")

    with tarfile.open(tar, "w:tar") as tarf:
        tarf.add(a, arcname="/foo/bar")

    return tar


@pytest.fixture
def tar5(tmp_path: pathlib.Path) -> pathlib.Path:
    a = tmp_path.joinpath("a")
    a.write_text("")
    b = tmp_path.joinpath("b")
    b.write_text("")

    tar = tmp_path.joinpath("tar")

    with tarfile.open(tar, "w:tar") as tarf:
        tarf.add(a, arcname="foo/v1/bar")
        tarf.add(b, arcname="foo/v2/baz")

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


def test_unpack_tar_strip1(tar: pathlib.Path, tmp_path: pathlib.Path) -> None:
    dest = tmp_path.joinpath("dest")
    with pytest.raises(ValueError) as excinfo:
        archive.unpack(str(tar), str(dest), perform_strip1=True)

    assert (
        f"{excinfo.value}"
        == """unexpected archive structure:

trying to strip 1 leading components but hello.txt isn't that deep
"""
    )


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


def test_unpack_strip_n(tar2: pathlib.Path, tmp_path: pathlib.Path) -> None:
    dest = tmp_path.joinpath("dest")
    archive.unpack_strip_n(str(tar2), str(dest), n=2)
    assert os.path.exists(f"{tmp_path}/dest/bin/foo")
    assert os.path.exists(f"{tmp_path}/dest/baz")

    dest2 = tmp_path.joinpath("dest2")
    archive.unpack_strip_n(str(tar2), str(dest2), n=2, new_prefix="x")
    assert os.path.exists(f"{tmp_path}/dest2/x/bin/foo")
    assert os.path.exists(f"{tmp_path}/dest2/x/baz")


def test_unpack_strip_n_unexpected_structure(
    tar3: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    dest = tmp_path.joinpath("dest")
    with pytest.raises(ValueError) as excinfo:
        archive.unpack_strip_n(str(tar3), str(dest), n=2)

    assert (
        f"{excinfo.value}"
        == """unexpected archive structure:

foo/bad doesn't have the prefix to be removed (foo/v1/)
"""
    )


def test_unpack_strip_n_root(
    tar4: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    dest = tmp_path.joinpath("dest")
    archive.unpack_strip_n(str(tar4), str(dest), n=1)
    # leading slash in /foo/bar doesn't count as a component
    assert os.path.exists(f"{tmp_path}/dest/bar")

    dest2 = tmp_path.joinpath("dest")
    archive.unpack_strip_n(str(tar4), str(dest2), n=0)
    # n=0 can be used to just strip the root component
    assert os.path.exists(f"{tmp_path}/dest/foo/bar")


def test_unpack_strip_n_unexpected_structure_inconsistent_components(
    tar5: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    dest = tmp_path.joinpath("dest")
    with pytest.raises(ValueError) as excinfo:
        archive.unpack_strip_n(str(tar5), str(dest), n=2)

    assert (
        f"{excinfo.value}"
        == """unexpected archive structure:

foo/v2/baz doesn't have the prefix to be removed (foo/v1/)
"""
    )
