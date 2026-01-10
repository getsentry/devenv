from __future__ import annotations

import os.path
import pathlib
import shutil
from collections.abc import Generator
from unittest import mock

import pytest

from devenv.checks import dockerConfig
from devenv.lib import docker


@pytest.fixture
def fake_config(tmp_path: pathlib.Path) -> Generator[pathlib.Path]:
    cfg = tmp_path.joinpath("config.json")

    def new_expanduser(s: str) -> str:
        assert s == "~/.docker/config.json"
        return str(cfg)

    with mock.patch.object(os.path, "expanduser", new_expanduser):
        yield cfg


def test_no_credsStore_ok(fake_config: pathlib.Path) -> None:
    fake_config.write_text('{"currentContext": "colima"}')
    assert dockerConfig.check() == (True, "")


def test_binary_ok(fake_config: pathlib.Path) -> None:
    fake_config.write_text(
        '{"credsStore": "example", "currentContext": "colima"}'
    )
    with mock.patch.object(shutil, "which", return_value="/fake/exe"):
        assert dockerConfig.check() == (True, "")


@pytest.mark.parametrize("name", ("desktop", "osxkeychain"))
def test_binary_missing(fake_config: pathlib.Path, name: str) -> None:
    fake_config.write_text(f'{{"credsStore": "{name}"}}')
    with mock.patch.object(shutil, "which", return_value=None):
        assert dockerConfig.check() == (
            False,
            "credsStore requires nonexistent binary",
        )


def test_fix_credsStore(fake_config: pathlib.Path) -> None:
    fake_config.write_text('{"credsStore": "bad"}')
    # Mock is_using_colima to return True so fix sets currentContext
    with mock.patch.object(dockerConfig, "is_using_colima", return_value=True):
        assert dockerConfig.fix() == (True, "")
        assert fake_config.read_text() == '{"currentContext": "colima"}'


def test_fix_cliPluginsExtraDirs(fake_config: pathlib.Path) -> None:
    fake_config.write_text('{"cliPluginsExtraDirs": ["foo/"]}')
    # Mock is_using_colima to return True so fix removes cliPluginsExtraDirs
    with mock.patch.object(dockerConfig, "is_using_colima", return_value=True):
        assert dockerConfig.fix() == (True, "")
        assert fake_config.read_text() == '{"currentContext": "colima"}'


def test_currentContext_missing_with_colima(fake_config: pathlib.Path) -> None:
    """When colima is installed but context is missing and Docker doesn't work, fail."""
    fake_config.write_text('{"auths": {}}')
    with mock.patch.object(shutil, "which", return_value="/fake/colima"):
        with mock.patch.object(
            docker, "is_docker_available", return_value=False
        ):
            assert dockerConfig.check() == (
                False,
                "currentContext is '', should be 'colima'",
            )


def test_currentContext_missing_docker_works(fake_config: pathlib.Path) -> None:
    """When colima is installed but Docker works anyway, that's fine (native Docker)."""
    fake_config.write_text('{"auths": {}}')
    with mock.patch.object(shutil, "which", return_value="/fake/colima"):
        with mock.patch.object(
            docker, "is_docker_available", return_value=True
        ):
            assert dockerConfig.check() == (True, "")


def test_currentContext_wrong_with_colima(fake_config: pathlib.Path) -> None:
    """When colima is installed, context is wrong, and Docker doesn't work, fail."""
    fake_config.write_text('{"currentContext": "desktop"}')
    with mock.patch.object(shutil, "which", return_value="/fake/colima"):
        with mock.patch.object(
            docker, "is_docker_available", return_value=False
        ):
            assert dockerConfig.check() == (
                False,
                "currentContext is 'desktop', should be 'colima'",
            )


def test_currentContext_wrong_docker_works(fake_config: pathlib.Path) -> None:
    """When colima is installed, context is wrong, but Docker works, that's fine."""
    fake_config.write_text('{"currentContext": "desktop"}')
    with mock.patch.object(shutil, "which", return_value="/fake/colima"):
        with mock.patch.object(
            docker, "is_docker_available", return_value=True
        ):
            assert dockerConfig.check() == (True, "")


def test_currentContext_correct(fake_config: pathlib.Path) -> None:
    fake_config.write_text('{"currentContext": "colima"}')
    assert dockerConfig.check() == (True, "")


def test_fix_currentContext_missing(fake_config: pathlib.Path) -> None:
    fake_config.write_text('{"auths": {}}')
    with mock.patch.object(dockerConfig, "is_using_colima", return_value=True):
        assert dockerConfig.fix() == (True, "")
        assert (
            fake_config.read_text()
            == '{"auths": {}, "currentContext": "colima"}'
        )


def test_fix_currentContext_wrong(fake_config: pathlib.Path) -> None:
    fake_config.write_text('{"currentContext": "docker-desktop"}')
    with mock.patch.object(dockerConfig, "is_using_colima", return_value=True):
        assert dockerConfig.fix() == (True, "")
        assert fake_config.read_text() == '{"currentContext": "colima"}'


def test_no_colima_installed(fake_config: pathlib.Path) -> None:
    """When colima is not installed, context check is skipped."""
    fake_config.write_text('{"currentContext": "desktop"}')
    with mock.patch.object(shutil, "which", return_value=None):
        assert dockerConfig.check() == (True, "")
