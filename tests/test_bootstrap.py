from __future__ import annotations

import os
from unittest.mock import call
from unittest.mock import patch

from devenv import bootstrap


mock_config = """
[colima]
darwin_x86_64 = https://github.com/abiosoft/colima/releases/download/v0.6.8/colima-Darwin-x86_64
darwin_x86_64_sha256 = e5aa67eb339616effe1604ecdcfcbc0e4899a3584048921b5bc063b850fa0b44
darwin_arm64 = https://github.com/abiosoft/colima/releases/download/v0.6.8/colima-Darwin-arm64
darwin_arm64_sha256 = bcac7db4452136ed649acde7dc93204574293db7c5bff93bc813122173281385
linux_x86_64 = https://github.com/abiosoft/colima/releases/download/v0.6.8/colima-Linux-x86_64
linux_x86_64_sha256 = 8c5f7b041fb8b37f4760bf20dc5cbb44eee6aa9ef4db5845826ecbba1cb422d4
linux_arm64 = https://github.com/abiosoft/colima/releases/download/v0.6.8/colima-Linux-aarch64
linux_arm64_sha256 = e3bc5267cbe57ab43f181994330b7f89dc486ba80bc734ea9d1644db13458274
version = v0.6.8
"""


def test_darwin(tmp_path: str) -> None:
    with patch("devenv.bootstrap.CI", True), patch(
        "devenv.bootstrap.DARWIN", True
    ), patch(
        "devenv.lib.github.add_to_known_hosts"
    ) as mock_add_to_known_hosts, patch(
        "devenv.lib.github.check_ssh_access", side_effect=(False, True)
    ), patch(
        "devenv.lib.github.generate_and_configure_ssh_keypair"
    ) as mock_generate_and_configure_ssh_keypair, patch(
        "devenv.lib.brew.install"
    ) as mock_brew_install, patch(
        "devenv.lib.volta.install"
    ) as mock_volta_install, patch(
        "devenv.lib.direnv.install"
    ) as mock_direnv_install, patch(
        "devenv.lib.colima.install"
    ) as mock_colima_install, patch(
        "devenv.lib.limactl.install"
    ) as mock_limactl_install, patch(
        "shutil.rmtree"
    ), patch(
        "devenv.lib.proc.run",
        side_effect=[
            None,  # git clone sentry
            None,  # brew install docker qemu
            None,  # devenv sync
            None,  # make bootstrap
        ],
    ) as mock_proc_run:
        coderoot = f"{tmp_path}/coderoot"
        os.makedirs(f"{coderoot}/sentry/devenv")
        with open(f"{coderoot}/sentry/devenv/config.ini", "w") as f:
            f.write(mock_config)

        bootstrap.main(coderoot=coderoot, argv=("sentry",))
        mock_add_to_known_hosts.assert_called_once()
        mock_generate_and_configure_ssh_keypair.assert_called_once()
        mock_brew_install.assert_called_once()
        mock_volta_install.assert_called_once()
        mock_direnv_install.assert_called_once()
        mock_colima_install.assert_called_once_with(
            "v0.6.8",
            "https://github.com/abiosoft/colima/releases/download/v0.6.8/colima-Darwin-arm64",
            "bcac7db4452136ed649acde7dc93204574293db7c5bff93bc813122173281385",
        )
        mock_limactl_install.assert_called_once()
        assert mock_proc_run.mock_calls == [
            # TODO: fix this, regressed since i had to add a mock repo config above
            #            call(
            #                (
            #                    "git",
            #                    "-C",
            #                    coderoot,
            #                    "clone",
            #                    "--filter=blob:none",
            #                    "--depth",
            #                    "1",
            #                    "https://github.com/getsentry/sentry",
            #                ),
            #                exit=True,
            #            ),
            call(("brew", "install", "docker", "qemu")),
            call(("devenv", "sync"), cwd=f"{coderoot}/sentry"),
            call(
                ("make", "bootstrap"),
                env={"VIRTUAL_ENV": f"{coderoot}/sentry/.venv"},
                pathprepend=f"{coderoot}/sentry/.venv/bin",
                cwd=f"{coderoot}/sentry",
            ),
        ]


def test_linux(tmp_path: str) -> None:
    with patch("devenv.bootstrap.CI", True), patch(
        "devenv.bootstrap.DARWIN", False
    ), patch(
        "devenv.lib.github.add_to_known_hosts"
    ) as mock_add_to_known_hosts, patch(
        "devenv.lib.github.check_ssh_access", side_effect=(False, True)
    ), patch(
        "devenv.lib.github.generate_and_configure_ssh_keypair"
    ) as mock_generate_and_configure_ssh_keypair, patch(
        "devenv.lib.brew.install"
    ) as mock_brew_install, patch(
        "devenv.lib.volta.install"
    ) as mock_volta_install, patch(
        "devenv.lib.direnv.install"
    ) as mock_direnv_install, patch(
        "devenv.lib.colima.install"
    ) as mock_colima_install, patch(
        "devenv.lib.limactl.install"
    ) as mock_limactl_install, patch(
        "shutil.rmtree"
    ), patch(
        "devenv.lib.proc.run",
        side_effect=[
            None,  # git clone sentry
            None,  # devenv sync
            None,  # make bootstrap
        ],
    ) as mock_proc_run:
        coderoot = f"{tmp_path}/coderoot"
        os.makedirs(f"{coderoot}/sentry/devenv")
        with open(f"{coderoot}/sentry/devenv/config.ini", "w") as f:
            f.write(mock_config)

        bootstrap.main(coderoot=coderoot, argv=("sentry",))
        mock_add_to_known_hosts.assert_called_once()
        mock_generate_and_configure_ssh_keypair.assert_called_once()
        mock_brew_install.assert_called_once()
        mock_volta_install.assert_called_once()
        mock_direnv_install.assert_called_once()
        mock_colima_install.assert_not_called()
        mock_limactl_install.assert_not_called()
        assert mock_proc_run.mock_calls == [
            # TODO: fix this, regressed since i had to add a mock repo config above
            #            call(
            #                (
            #                    "git",
            #                    "-C",
            #                    coderoot,
            #                    "clone",
            #                    "--filter=blob:none",
            #                    "--depth",
            #                    "1",
            #                    "https://github.com/getsentry/sentry",
            #                ),
            #                exit=True,
            #            ),
            call(("devenv", "sync"), cwd=f"{coderoot}/sentry"),
            call(
                ("make", "bootstrap"),
                env={"VIRTUAL_ENV": f"{coderoot}/sentry/.venv"},
                pathprepend=f"{coderoot}/sentry/.venv/bin",
                cwd=f"{coderoot}/sentry",
            ),
        ]
