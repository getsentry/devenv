from __future__ import annotations

import os
import pathlib
from unittest.mock import call
from unittest.mock import patch

from devenv.lib import config
from devenv.lib import venv
from devenv.lib.repository import Repository

mock_config = """
[venv.sentry-kube]
python = 3.11.6
requirements = k8s/cli/requirements.txt
editable =
  k8s/cli
  k8s/cli/libsentrykube
bins =
  pre-commit
  pyupgrade
  sentry-kube
  sentry-kube-pop

[python3.11.6]
darwin_x86_64 = https://github.com/indygreg/python-build-standalone/releases/download/20231002/cpython-3.11.6+20231002-x86_64-apple-darwin-install_only.tar.gz
darwin_x86_64_sha256 = 178cb1716c2abc25cb56ae915096c1a083e60abeba57af001996e8bc6ce1a371
darwin_arm64 = https://github.com/indygreg/python-build-standalone/releases/download/20231002/cpython-3.11.6+20231002-aarch64-apple-darwin-install_only.tar.gz
darwin_arm64_sha256 = 916c35125b5d8323a21526d7a9154ca626453f63d0878e95b9f613a95006c990
linux_x86_64 = https://github.com/indygreg/python-build-standalone/releases/download/20231002/cpython-3.11.6+20231002-x86_64-unknown-linux-gnu-install_only.tar.gz
linux_x86_64_sha256 = ee37a7eae6e80148c7e3abc56e48a397c1664f044920463ad0df0fc706eacea8
linux_arm64 = https://github.com/indygreg/python-build-standalone/releases/download/20231002/cpython-3.11.6+20231002-aarch64-unknown-linux-gnu-install_only.tar.gz
linux_arm64_sha256 = 3e26a672df17708c4dc928475a5974c3fb3a34a9b45c65fb4bd1e50504cc84ec
"""


def test_get_ensure(tmp_path: pathlib.Path) -> None:
    repo = Repository(f"{tmp_path}/ops")

    os.makedirs(repo.config_path)
    with open(f"{repo.config_path}/config.ini", "w") as f:
        f.write(mock_config)

    venv_dir, python_version, requirements, editable_paths, bins = venv.get(
        repo.path, "sentry-kube"
    )
    os.makedirs(venv_dir)

    assert (venv_dir, python_version, requirements, editable_paths, bins) == (
        f"{repo.path}/.venv-sentry-kube",
        "3.11.6",
        f"{repo.path}/k8s/cli/requirements.txt",
        (f"{repo.path}/k8s/cli", f"{repo.path}/k8s/cli/libsentrykube"),
        ("pre-commit", "pyupgrade", "sentry-kube", "sentry-kube-pop"),
    )

    url, sha256 = config.get_python(repo.path, python_version)

    with patch("devenv.lib.venv.proc.run") as mock_run, patch(
        "devenv.lib.venv.pythons.get", return_value="python"
    ) as mock_pythons_get, patch("shutil.rmtree"):
        venv.ensure(venv_dir, python_version, url, sha256)
        assert mock_pythons_get.mock_calls == [
            call(python_version, url, sha256)
        ]
        assert mock_run.mock_calls == [
            call(("python", "-m", "venv", venv_dir), exit=True)
        ]
        assert os.path.isfile(f"{venv_dir}/.gitignore")

    # fake venv
    with open(f"{venv_dir}/pyvenv.cfg", "w") as f:
        f.write(f"version = {python_version}\n")

    assert venv.check(venv_dir, python_version) == venv.VenvStatus.OK

    # unittesting venv.sync(venv_dir, requirements, editable_paths, bins)
    # isn't really useful and is covered better with integration
