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
python = 3.13.18
requirements = k8s/cli/requirements.txt
editable =
  k8s/cli
  k8s/cli/libsentrykube
bins =
  prek
  pyupgrade
  sentry-kube
  sentry-kube-pop

[python3.13.18]
darwin_x86_64 = https://github.com/astral-sh/python-build-standalone/releases/download/20261026/cpython-3.13.18+20261026-x86_64-apple-darwin-install_only.tar.gz
darwin_x86_64_sha256 = 708be9e7df297f68bdae589ea9e62a621db5abe7708f79e851c41410347452d1
darwin_arm64 = https://github.com/astral-sh/python-build-standalone/releases/download/20261026/cpython-3.13.18+20261026-aarch64-apple-darwin-install_only.tar.gz
darwin_arm64_sha256 = e5af2fde6a937a0e0c795a0c595c4efb70578d57463a2657c819992b9b9acbac
linux_x86_64 = https://github.com/astral-sh/python-build-standalone/releases/download/20261026/cpython-3.13.18+20261026-x86_64-unknown-linux-gnu-install_only.tar.gz
linux_x86_64_sha256 = 126343c54daff4068efc1ac269518d0cc202d57857794948103dd1454e8881be
linux_arm64 = https://github.com/astral-sh/python-build-standalone/releases/download/20261026/cpython-3.13.18+20261026-aarch64-unknown-linux-gnu-install_only.tar.gz
linux_arm64_sha256 = b48451865bde9a39e2f3e71d7fdcbf1f32615f50f24d78dc50d04ede6501cf81
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
        "3.13.18",
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
        "home = /x\nversion = 3.13.18\n",
        "home = /x\nuv = 0.13.4\nversion_info = 3.13.18\n",
        "home = /x\nversion_info = 3.13.18.final.0\n",
        "version = 3.13.18\nversion_info = 3.13.18.final.0\n",
    ),
)
def test_check_ok(tmp_path: pathlib.Path, pyvenv_cfg: str) -> None:
    os.makedirs(f"{tmp_path}/bin")
    open(f"{tmp_path}/bin/python", "w").close()
    with open(f"{tmp_path}/pyvenv.cfg", "w") as f:
        f.write(pyvenv_cfg)

    assert venv.check(str(tmp_path), "3.13.18") == venv.VenvStatus.OK


@pytest.mark.parametrize(
    "pyvenv_cfg", ("version = 3.13.15\n", "version_info = 3.13.15.final.0\n")
)
def test_check_mismatch(tmp_path: pathlib.Path, pyvenv_cfg: str) -> None:
    os.makedirs(f"{tmp_path}/bin")
    open(f"{tmp_path}/bin/python", "w").close()
    with open(f"{tmp_path}/pyvenv.cfg", "w") as f:
        f.write(pyvenv_cfg)

    assert (
        venv.check(str(tmp_path), "3.13.18") == venv.VenvStatus.VERSION_MISMATCH
    )
