from __future__ import annotations

import os
import pathlib
import tarfile

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
