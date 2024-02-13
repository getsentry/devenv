from __future__ import annotations

import os
import pathlib
from unittest.mock import call
from unittest.mock import patch


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

[venv.salt]
python = 3.10.13
requirements = salt/requirements.txt
bins =
  salt
  salt-ssh
  salt-call
  salt-api
  salt-run

[python3.11.6]
darwin_x86_64 = https://github.com/indygreg/python-build-standalone/releases/download/20231002/cpython-3.11.6+20231002-x86_64-apple-darwin-install_only.tar.gz
darwin_x86_64_sha256 = 178cb1716c2abc25cb56ae915096c1a083e60abeba57af001996e8bc6ce1a371
darwin_arm64 = https://github.com/indygreg/python-build-standalone/releases/download/20231002/cpython-3.11.6+20231002-aarch64-apple-darwin-install_only.tar.gz
darwin_arm64_sha256 = 916c35125b5d8323a21526d7a9154ca626453f63d0878e95b9f613a95006c990
linux_x86_64 = https://github.com/indygreg/python-build-standalone/releases/download/20231002/cpython-3.11.6+20231002-x86_64-unknown-linux-gnu-install_only.tar.gz
linux_x86_64_sha256 = ee37a7eae6e80148c7e3abc56e48a397c1664f044920463ad0df0fc706eacea8
linux_arm64 = https://github.com/indygreg/python-build-standalone/releases/download/20231002/cpython-3.11.6+20231002-aarch64-unknown-linux-gnu-install_only.tar.gz
linux_arm64_sha256 = 3e26a672df17708c4dc928475a5974c3fb3a34a9b45c65fb4bd1e50504cc84ec

[python3.10.13]
darwin_x86_64 = https://github.com/indygreg/python-build-standalone/releases/download/20231002/cpython-3.10.13+20231002-x86_64-apple-darwin-install_only.tar.gz
darwin_x86_64_sha256 = be0b19b6af1f7d8c667e5abef5505ad06cf72e5a11bb5844970c395a7e5b1275
darwin_arm64 = https://github.com/indygreg/python-build-standalone/releases/download/20231002/cpython-3.10.13+20231002-aarch64-apple-darwin-install_only.tar.gz
darwin_arm64_sha256 = fd027b1dedf1ea034cdaa272e91771bdf75ddef4c8653b05d224a0645aa2ca3c
linux_x86_64 = https://github.com/indygreg/python-build-standalone/releases/download/20231002/cpython-3.10.13+20231002-x86_64-unknown-linux-gnu-install_only.tar.gz
linux_x86_64_sha256 = 5d0429c67c992da19ba3eb58b3acd0b35ec5e915b8cae9a4aa8ca565c423847a
linux_arm64 = https://github.com/indygreg/python-build-standalone/releases/download/20231002/cpython-3.10.13+20231002-aarch64-unknown-linux-gnu-install_only.tar.gz
linux_arm64_sha256 = 8675915ff454ed2f1597e27794bc7df44f5933c26b94aa06af510fe91b58bb97
"""


def test_get_ensure_sync(tmp_path: pathlib.Path) -> None:
    os.environ["HOME"] = f"{tmp_path}"

    from devenv.lib import venv
    from devenv.lib import config
    from devenv.constants import venvs_root

    reporoot = f"{tmp_path}/ops"
    os.makedirs(f"{reporoot}/devenv")
    with open(f"{reporoot}/devenv/config.ini", "w") as f:
        f.write(mock_config)

    venv_dir, python_version, requirements, editable_paths, bins = venv.get(
        reporoot, "sentry-kube"
    )

    assert (venv_dir, python_version, requirements, editable_paths, bins) == (
        f"{venvs_root}/ops-sentry-kube",
        "3.11.6",
        f"{reporoot}/k8s/cli/requirements.txt",
        (f"{reporoot}/k8s/cli", f"{reporoot}/k8s/cli/libsentrykube"),
        ("pre-commit", "pyupgrade", "sentry-kube", "sentry-kube-pop"),
    )

    url, sha256 = config.get_python(reporoot, python_version)

    with patch("devenv.lib.venv.proc.run") as mock_run, patch(
        "devenv.lib.venv.pythons.get", return_value="python"
    ) as mock_pythons_get:
        venv.ensure(venv_dir, python_version, url, sha256)
        assert mock_pythons_get.mock_calls == [
            call(python_version, url, sha256)
        ]
        assert mock_run.mock_calls == [
            call(("python", "-m", "venv", venv_dir), exit=True)
        ]

    # venv.sync(venv_dir, requirements, editable_paths, bins)


# test_ensure_no_python_defined
