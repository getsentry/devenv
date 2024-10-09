from __future__ import annotations

import io
import pathlib
import tarfile
import time
import typing
import urllib.request
from unittest import mock

import pytest

from devenv.lib import archive
from tests.utils import sorted_os_walk


@pytest.fixture
def tar(tmp_path: pathlib.Path) -> pathlib.Path:
    executable = tmp_path / "executable"
    executable.write_text("hi")

    tar = tmp_path / "tar"
    with tarfile.open(tar, "w:tar") as tarf:
        tarf.add(executable, arcname="executable")

    return tar


@pytest.fixture
def tgz(tmp_path: pathlib.Path) -> pathlib.Path:
    foo_v1 = tmp_path / "foo-v1"
    foo_v1.mkdir()

    foo_v1_bin = tmp_path / "foo-v1/bin"
    foo_v1_bin.mkdir()

    foo_v1_bin_foo = tmp_path / "foo-v1/bin/foo"
    foo_v1_bin_foo.write_text("")

    foo_v1_baz = tmp_path / "foo-v1/baz"
    foo_v1_baz.write_text("")

    tgz = tmp_path / "tgz"
    with tarfile.open(tgz, "w:gz") as tarf:
        tarf.add(foo_v1, arcname="foo-v1")
        # foo-v1
        # foo-v1/bin
        # foo-v1/bin/foo
        # foo-v1/baz

    return tgz


@pytest.fixture
def tar2(tmp_path: pathlib.Path) -> pathlib.Path:
    foo = tmp_path / "foo"
    foo.mkdir()

    foo_v1 = tmp_path / "foo/v1"
    foo_v1.mkdir()

    foo_v1_bin = tmp_path / "foo/v1/bin"
    foo_v1_bin.mkdir()

    foo_v1_bin_foo = tmp_path / "foo/v1/bin/foo"
    foo_v1_bin_foo.write_text("")

    foo_v1_baz = tmp_path / "foo/v1/baz"
    foo_v1_baz.mkdir()

    tar = tmp_path / "tar"
    with tarfile.open(tar, "w:tar") as tarf:
        tarf.add(foo, arcname="foo")
        # foo
        # foo/v1
        # foo/v1/bin
        # foo/v1/bin/foo
        # foo/v1/baz

    return tar


@pytest.fixture
def tar3(tmp_path: pathlib.Path) -> pathlib.Path:
    foo = tmp_path / "foo"
    foo.mkdir()

    foo_bar = tmp_path / "foo/bar"
    foo_bar.write_text("")

    foo_v1 = tmp_path / "foo/v1"
    foo_v1.mkdir()

    foo_v1_foo = tmp_path / "foo/v1/foo"
    foo_v1_foo.write_text("")

    tar = tmp_path / "tar"
    with tarfile.open(tar, "w:tar") as tarf:
        tarf.add(foo, arcname="foo")
        # foo
        # foo/bar
        # foo/v1
        # foo/v1/foo

    return tar


@pytest.fixture
def tar4(tmp_path: pathlib.Path) -> pathlib.Path:
    foo = tmp_path / "foo"
    foo.mkdir()

    foo_bar = tmp_path / "foo/bar"
    foo_bar.write_text("")

    tar = tmp_path / "tar"

    with tarfile.open(tar, "w:tar") as tarf:
        # note: arcname /foo doesn't work, it gets added as foo
        tarf.add(foo, arcname="foo")
        # /foo
        # /foo/bar
        for member in tarf.getmembers():
            member.path = f"/{member.path}"

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
    dest = tmp_path / "dest"
    archive.unpack(str(tar), str(dest))
    assert (dest / "executable").read_text() == "hi"


def test_unpack_tgz_strip1(tgz: pathlib.Path, tmp_path: pathlib.Path) -> None:
    dest = tmp_path / "dest"
    archive.unpack(str(tgz), str(dest), perform_strip1=True)

    assert [*sorted_os_walk(dest)] == [
        # bin/foo
        # baz
        (f"{dest}", ["bin"], ["baz"]),
        (f"{dest}/bin", [], ["foo"]),
    ]

    dest2 = tmp_path / "dest2"
    archive.unpack(
        str(tgz), str(dest2), perform_strip1=True, strip1_new_prefix="node"
    )

    assert [*sorted_os_walk(dest2)] == [
        # node/bin/foo
        # node/baz
        (f"{dest2}", ["node"], []),
        (f"{dest2}/node", ["bin"], ["baz"]),
        (f"{dest2}/node/bin", [], ["foo"]),
    ]


def test_unpack_strip_n(tar2: pathlib.Path, tmp_path: pathlib.Path) -> None:
    dest = tmp_path / "dest"
    archive.unpack_strip_n(str(tar2), str(dest), n=2)
    assert [*sorted_os_walk(dest)] == [
        # baz
        # bin/foo
        (f"{dest}", ["baz", "bin"], []),
        (f"{dest}/baz", [], []),
        (f"{dest}/bin", [], ["foo"]),
    ]

    dest2 = tmp_path / "dest2"
    archive.unpack_strip_n(str(tar2), str(dest2), n=2, new_prefix="x")
    assert [*sorted_os_walk(dest2)] == [
        # x/baz
        # x/bin/foo
        (f"{dest2}", ["x"], []),
        (f"{dest2}/x", ["baz", "bin"], []),
        (f"{dest2}/x/baz", [], []),
        (f"{dest2}/x/bin", [], ["foo"]),
    ]


def test_unpack_strip_n_unconditionally_removed(
    tar3: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    dest = tmp_path / "dest"
    archive.unpack_strip_n(str(tar3), str(dest), n=2)

    # foo/bar is unconditionally removed

    assert [*sorted_os_walk(dest)] == [
        # dest/foo
        (f"{dest}", [], ["foo"])
    ]


def test_unpack_strip_n_root(
    tar4: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    dest = tmp_path / "dest"
    archive.unpack_strip_n(str(tar4), str(dest), n=1)
    # leading slash in /foo/bar doesn't count as a component

    assert [*sorted_os_walk(dest)] == [
        # bar
        (f"{dest}", [], ["bar"])
    ]

    dest2 = tmp_path / "dest2"
    archive.unpack_strip_n(str(tar4), str(dest2), n=0)
    # n=0 can be used to just strip the root component

    assert [*sorted_os_walk(dest2)] == [
        # foo/bar
        (f"{dest2}", ["foo"], []),
        (f"{dest2}/foo", [], ["bar"]),
    ]
