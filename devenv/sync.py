from __future__ import annotations

import configparser
import importlib.util
import os
import subprocess
from collections.abc import Sequence
from typing import Dict
from typing import Tuple

from devenv import constants
from devenv.constants import CI
from devenv.constants import DARWIN
from devenv.constants import home
from devenv.constants import SYSTEM_MACHINE
from devenv.constants import VOLTA_HOME
from devenv.lib import colima
from devenv.lib import limactl
from devenv.lib import proc
from devenv.lib import venv
from devenv.lib import volta

help = "Resyncs the environment."


def run_procs(
    repo: str,
    reporoot: str,
    venv_path: str,
    _procs: Tuple[Tuple[str, tuple[str, ...]], ...],
) -> bool:
    procs: list[tuple[str, tuple[str, ...], subprocess.Popen[bytes]]] = []

    for name, cmd in _procs:
        print(f"⏳ {name}")
        if constants.DEBUG:
            proc.xtrace(cmd)
        procs.append(
            (
                name,
                cmd,
                subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    env={
                        **constants.user_environ,
                        **proc.base_env,
                        "VIRTUAL_ENV": venv_path,
                        "VOLTA_HOME": VOLTA_HOME,
                        "PATH": f"{venv_path}/bin:{proc.base_path}",
                    },
                    cwd=reporoot,
                ),
            )
        )

    all_good = True
    for name, final_cmd, p in procs:
        p.wait()
        if p.returncode != 0:
            all_good = False
            if p.stdout is None:
                out = ""
            else:
                out = p.stdout.read().decode()
            print(
                f"""
❌ {name}

failed command (code p.returncode):
    {proc.quote(final_cmd)}

Output:
{out}

"""
            )
        else:
            print(f"✅ {name}")

    return all_good


def main(context: Dict[str, str], argv: Sequence[str] | None = None) -> int:
    repo = context["repo"]
    reporoot = context["reporoot"]

    if os.path.exists(f"{reporoot}/devenv/sync.py"):
        spec = importlib.util.spec_from_file_location(
            "sync", f"{reporoot}/devenv/sync.py"
        )
        module = importlib.util.module_from_spec(spec)  # type: ignore
        spec.loader.exec_module(module)  # type: ignore
        return module.main(context)  # type: ignore

    # past this point is legacy code that should only be run for sentry/getsentry
    # eventually to be moved to sentry/devenv/sync.py
    assert repo in {"sentry", "getsentry"}

    venv.ensure_repolocal(reporoot)

    print("Resyncing your dev environment.")

    if not run_procs(
        repo,
        reporoot,
        f"{reporoot}/.venv",
        (
            (
                "git and precommit",
                # this can't be done in paralell with python dependencies
                # as multiple pips cannot act on the same venv
                ("make", "setup-git"),
            ),
        ),
    ):
        return 1

    # This is for engineers with existing dev environments transitioning over.
    # Bootstrap will set devenv-managed volta up but they won't be running
    # devenv bootstrap, just installing devenv then running devenv sync.
    # make install-js-dev will fail since our run_procs expects devenv-managed
    # volta.
    volta.install()

    if DARWIN:
        repo_config = configparser.ConfigParser()
        repo_config.read(f"{reporoot}/devenv/config.ini")

        # we don't officially support colima on linux yet
        if CI:
            # colima 0.6.8 doesn't work with macos-13,
            # but integration coverage is still handy
            colima.install(
                "v0.6.2",
                "https://github.com/abiosoft/colima/releases/download/v0.6.2/colima-Darwin-x86_64",
                "43ef3fc80a8347d51b8ec1706f9caf8863bd8727a6f7532caf1ccd20497d8485",
            )
        else:
            colima.install(
                repo_config["colima"]["version"],
                repo_config["colima"][SYSTEM_MACHINE],
                repo_config["colima"][f"{SYSTEM_MACHINE}_sha256"],
            )

        # TODO: move limactl version into per-repo config
        limactl.install()

    if not run_procs(
        repo,
        reporoot,
        f"{reporoot}/.venv",
        (
            ("javascript dependencies", ("make", "install-js-dev")),
            ("python dependencies", ("make", "install-py-dev")),
        ),
    ):
        return 1

    if not os.path.exists(f"{home}/.sentry/config.yml") or not os.path.exists(
        f"{home}/.sentry/sentry.conf.py"
    ):
        proc.run((f"{reporoot}/.venv/bin/sentry", "init", "--dev"))

    # TODO: run devservices healthchecks for redis and postgres to bypass this
    proc.run(
        (
            f"{reporoot}/.venv/bin/sentry",
            "devservices",
            "up",
            "redis",
            "postgres",
        ),
        exit=True,
    )

    if run_procs(
        repo,
        reporoot,
        f"{reporoot}/.venv",
        (
            (
                "python migrations",
                (f"{reporoot}/.venv/bin/sentry", "upgrade", "--noinput"),
            ),
        ),
    ):
        return 0
    else:
        return 1
