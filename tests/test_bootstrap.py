from __future__ import annotations

from unittest.mock import call
from unittest.mock import patch

from devenv import bootstrap


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
        bootstrap.main(coderoot=coderoot, argv=("sentry",))
        mock_add_to_known_hosts.assert_called_once()
        mock_generate_and_configure_ssh_keypair.assert_called_once()
        mock_brew_install.assert_called_once()
        mock_volta_install.assert_called_once()
        mock_direnv_install.assert_called_once()
        mock_colima_install.assert_called_once()
        mock_limactl_install.assert_called_once()
        assert mock_proc_run.mock_calls == [
            call(
                (
                    "git",
                    "-C",
                    coderoot,
                    "clone",
                    "--filter=blob:none",
                    "--depth",
                    "1",
                    "https://github.com/getsentry/sentry",
                ),
                exit=True,
            ),
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
        bootstrap.main(coderoot=coderoot, argv=("sentry",))
        mock_add_to_known_hosts.assert_called_once()
        mock_generate_and_configure_ssh_keypair.assert_called_once()
        mock_brew_install.assert_called_once()
        mock_volta_install.assert_called_once()
        mock_direnv_install.assert_called_once()
        mock_colima_install.assert_not_called()
        mock_limactl_install.assert_not_called()
        assert mock_proc_run.mock_calls == [
            call(
                (
                    "git",
                    "-C",
                    coderoot,
                    "clone",
                    "--filter=blob:none",
                    "--depth",
                    "1",
                    "https://github.com/getsentry/sentry",
                ),
                exit=True,
            ),
            call(("devenv", "sync"), cwd=f"{coderoot}/sentry"),
            call(
                ("make", "bootstrap"),
                env={"VIRTUAL_ENV": f"{coderoot}/sentry/.venv"},
                pathprepend=f"{coderoot}/sentry/.venv/bin",
                cwd=f"{coderoot}/sentry",
            ),
        ]
