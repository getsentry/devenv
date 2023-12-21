from __future__ import annotations

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


def test_unpack_tar(tar: pathlib.Path, tmp_path: pathlib.Path) -> None:
    dest = tmp_path.joinpath("dest")
    archive.unpack(str(tar), str(dest))
    assert dest.joinpath("hello.txt").read_text() == "hello world\n"
