from __future__ import annotations

import os
import pathlib
from unittest.mock import call
from unittest.mock import patch

import pytest

from devenv.lib import config
from devenv.lib import venv
from devenv.lib.repository import Repository

mock_config = """
[venv.sentry-kube]
python = 3.13.16
requirements = k8s/cli/requirements.txt
editable =
  k8s/cli
  k8s/cli/libsentrykube
bins =
  prek
  pyupgrade
  sentry-kube
  sentry-kube-pop

[python3.13.16]
darwin_x86_64 = https://github.com/astral-sh/python-build-standalone/releases/download/20261013/cpython-3.13.16+20261013-x86_64-apple-darwin-install_only.tar.gz
darwin_x86_64_sha256 = d1f2e7b5f0cfa25fc856fea819890bbe722f47a692e5ce2552636b5240930b38
darwin_arm64 = https://github.com/astral-sh/python-build-standalone/releases/download/20261013/cpython-3.13.16+20261013-aarch64-apple-darwin-install_only.tar.gz
darwin_arm64_sha256 = ca0e6a70fb75a0984751bd75493e3de77680aef7fbd0fea9b903c299537b3423
linux_x86_64 = https://github.com/astral-sh/python-build-standalone/releases/download/20261013/cpython-3.13.16+20261013-x86_64-unknown-linux-gnu-install_only.tar.gz
linux_x86_64_sha256 = e588e50db882fa6a89f926d9a9ad64e445183af0eda5bda226a2c151b17db8a6
linux_arm64 = https://github.com/astral-sh/python-build-standalone/releases/download/20261013/cpython-3.13.16+20261013-aarch64-unknown-linux-gnu-install_only.tar.gz
linux_arm64_sha256 = 0fce0605da7b6532d5bdaec185336ffaaddd02ec04e27382014952ca4857ed6d
"""


def test_get_ensure(tmp_path: pathlib.Path) -> None:
    repo = Repository(f"{tmp_path}/ops")

    os.makedirs(repo.config_path)
    with open(f"{repo.config_path}/config.ini", "w") as f:
        f.write(mock_config)

    venv_dir, python_version, requirements, editable_paths, bins = venv.get(
        repo.path, "sentry-kube"
    )
    os.makedirs(f"{venv_dir}/bin")

    assert (venv_dir, python_version, requirements, editable_paths, bins) == (
        f"{repo.path}/.venv-sentry-kube",
        "3.13.16",
        f"{repo.path}/k8s/cli/requirements.txt",
        (f"{repo.path}/k8s/cli", f"{repo.path}/k8s/cli/libsentrykube"),
        ("prek", "pyupgrade", "sentry-kube", "sentry-kube-pop"),
    )

    url, sha256 = config.get_python(repo.path, python_version)

    with (
        patch("devenv.lib.venv.proc.run") as mock_run,
        patch("devenv.lib.venv.uv.find", return_value="uv"),
        patch(
            "devenv.lib.venv.pythons.get", return_value="python"
        ) as mock_pythons_get,
        patch("shutil.rmtree"),
    ):
        venv.ensure(venv_dir, python_version, url, sha256)
        assert mock_pythons_get.mock_calls == [
            call(python_version, url, sha256)
        ]
        assert mock_run.mock_calls == [
            call(("uv", "venv", "--python", "python", venv_dir), exit=True)
        ]
        assert os.path.isfile(f"{venv_dir}/.gitignore")

    # fake venv
    with open(f"{venv_dir}/pyvenv.cfg", "w") as f:
        f.write(f"version = {python_version}\n")

    # venv_dir/bin/python isn't present yet since we mocked that out
    assert venv.check(venv_dir, python_version) == venv.VenvStatus.NOT_PRESENT

    with open(f"{venv_dir}/bin/python", "w"):
        pass

    assert venv.check(venv_dir, python_version) == venv.VenvStatus.OK


def test_sync_uses_uv(tmp_path: pathlib.Path) -> None:
    reporoot = str(tmp_path)
    venv_dir = f"{reporoot}/.venv-foo"
    with (
        patch("devenv.lib.venv.proc.run") as mock_run,
        patch("devenv.lib.venv.uv.find", return_value="uv"),
    ):
        venv.sync(
            reporoot,
            venv_dir,
            f"{reporoot}/requirements.txt",
            (f"{reporoot}/a", f"{reporoot}/b"),
        )

    assert mock_run.mock_calls == [
        call(
            (
                "uv",
                "pip",
                "install",
                "--quiet",
                "--python",
                f"{venv_dir}/bin/python",
                "-r",
                f"{reporoot}/requirements.txt",
                "-e",
                f"{reporoot}/a",
                "-e",
                f"{reporoot}/b",
            )
        )
    ]


@pytest.mark.parametrize(
    "pyvenv_cfg",
    (
        "home = /x\nversion = 3.13.16\n",
        "home = /x\nuv = 0.13.4\nversion_info = 3.13.16\n",
        "home = /x\nversion_info = 3.13.16.final.0\n",
        "version = 3.13.16\nversion_info = 3.13.16.final.0\n",
    ),
)
def test_check_ok(tmp_path: pathlib.Path, pyvenv_cfg: str) -> None:
    os.makedirs(f"{tmp_path}/bin")
    open(f"{tmp_path}/bin/python", "w").close()
    with open(f"{tmp_path}/pyvenv.cfg", "w") as f:
        f.write(pyvenv_cfg)

    assert venv.check(str(tmp_path), "3.13.16") == venv.VenvStatus.OK


@pytest.mark.parametrize(
    "pyvenv_cfg", ("version = 3.13.15\n", "version_info = 3.13.15.final.0\n")
)
def test_check_mismatch(tmp_path: pathlib.Path, pyvenv_cfg: str) -> None:
    os.makedirs(f"{tmp_path}/bin")
    open(f"{tmp_path}/bin/python", "w").close()
    with open(f"{tmp_path}/pyvenv.cfg", "w") as f:
        f.write(pyvenv_cfg)

    assert (
        venv.check(str(tmp_path), "3.13.16") == venv.VenvStatus.VERSION_MISMATCH
    )
