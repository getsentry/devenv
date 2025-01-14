from __future__ import annotations

import os.path
import pathlib
import shutil
from collections.abc import Generator
from unittest import mock

import pytest

from devenv.checks import credsStore


@pytest.fixture
def fake_config(tmp_path: pathlib.Path) -> Generator[pathlib.Path]:
    cfg = tmp_path.joinpath("config.json")

    def new_expanduser(s: str) -> str:
        assert s == "~/.docker/config.json"
        return str(cfg)

    with mock.patch.object(os.path, "expanduser", new_expanduser):
        yield cfg


def test_no_credsStore_ok(fake_config: pathlib.Path) -> None:
    fake_config.write_text("{}")
    assert credsStore.check() == (True, "")


def test_binary_ok(fake_config: pathlib.Path) -> None:
    fake_config.write_text('{"credsStore": "example"}')
    with mock.patch.object(shutil, "which", return_value="/fake/exe"):
        assert credsStore.check() == (True, "")


@pytest.mark.parametrize("name", ("desktop", "osxkeychain"))
def test_binary_missing(fake_config: pathlib.Path, name: str) -> None:
    fake_config.write_text(f'{{"credsStore": "{name}"}}')
    with mock.patch.object(shutil, "which", return_value=None):
        assert credsStore.check() == (
            False,
            "credsStore requires nonexistent binary",
        )


def test_fix(fake_config: pathlib.Path) -> None:
    fake_config.write_text('{"credsStore": "bad"}')
    assert credsStore.fix() == (True, "")
    assert fake_config.read_text() == "{}"
