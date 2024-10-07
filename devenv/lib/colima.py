from __future__ import annotations

import os
import platform
import shutil
import tempfile
from enum import Enum

from devenv.constants import home
from devenv.lib import archive
from devenv.lib import docker
from devenv.lib import fs
from devenv.lib import proc
from devenv.lib import rosetta


ColimaStatus = Enum("ColimaStatus", ("UP", "DOWN", "UNHEALTHY"))


def _install(url: str, sha256: str, into: str) -> None:
    os.makedirs(into, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=into) as tmpd:
        archive.download(url, sha256, dest=f"{tmpd}/colima")
        os.replace(f"{tmpd}/colima", f"{into}/colima-bin")
        os.chmod(f"{into}/colima-bin", 0o775)


def uninstall(binroot: str) -> None:
    for d in (f"{home}/.lima",):
        shutil.rmtree(d, ignore_errors=True)

    for fp in (f"{binroot}/colima",):
        try:
            os.remove(fp)
        except FileNotFoundError:
            # it's better to do this than to guard with
            # os.path.exists(fp) because if it's an invalid or circular
            # symlink the result'll be False!
            pass


def install_shim(binroot: str) -> None:
    fs.write_script(
        f"{binroot}/colima",
        """#!/bin/sh
export COLIMA_HOME={home}/.colima

# needed to ensure COLIMA_HOME is what we want it to be
unset XDG_CONFIG_HOME

exec {binroot}/colima-bin "$@"
""",
        shell_escape={"binroot": binroot, "home": home},
    )


def install(version: str, url: str, sha256: str, reporoot: str) -> None:
    binroot = fs.ensure_binroot(reporoot)

    if shutil.which("colima", path=binroot) == f"{binroot}/colima":
        if not os.path.exists(f"{binroot}/colima-bin"):
            os.rename(f"{binroot}/colima", f"{binroot}/colima-bin")
            install_shim(binroot)

        stdout = proc.run((f"{binroot}/colima", "--version"), stdout=True)
        installed_version = stdout.strip().split()[-1]
        if version == installed_version:
            return
        print(f"installed colima {installed_version} is outdated!")

    print(f"installing colima {version}...")
    uninstall(binroot)
    _install(url, sha256, binroot)
    install_shim(binroot)

    stdout = proc.run((f"{binroot}/colima", "--version"), stdout=True)
    if f"colima version {version}" not in stdout:
        raise SystemExit(f"Failed to install colima {version}! Found: {stdout}")


def check(reporoot: str) -> ColimaStatus:
    if not os.getenv("CI"):
        macos_version = platform.mac_ver()[0]
        macos_major_version = int(macos_version.split(".")[0])
        if macos_major_version < 14:
            raise SystemExit(
                f"macos >= 14 is required to use colima, found {macos_version}"
            )

    docker_executable = shutil.which("docker")
    if not docker_executable:
        raise SystemExit(
            "docker executable not found, you might want to run devenv sync"
        )

    colima = f"{reporoot}/.devenv/bin/colima"
    if not os.path.isfile(colima):
        raise SystemExit(
            f"colima not found at {colima}, you might want to run devenv sync"
        )

    if not os.path.exists(f"{home}/.colima/default/docker.sock"):
        return ColimaStatus.DOWN

    # if colima's up, we should be able to communicate with that docker socket
    # at the most basic level
    try:
        proc.run(
            (docker_executable, "--context=colima", "version"), stdout=True
        )
    except RuntimeError:
        return ColimaStatus.UNHEALTHY

    # https://github.com/abiosoft/colima/issues/949
    healthy = docker.check_docker_to_host_connectivity()
    if not healthy:
        return ColimaStatus.UNHEALTHY

    return ColimaStatus.UP


def start(reporoot: str, restart: bool = False) -> ColimaStatus:
    status = check(reporoot)

    if status == ColimaStatus.UP:
        if not restart:
            return ColimaStatus.UP
        proc.run(("colima", "stop"), pathprepend=f"{reporoot}/.devenv/bin")
    elif status == ColimaStatus.DOWN:
        pass
    elif status == ColimaStatus.UNHEALTHY:
        print("colima seems to be unhealthy, stopping it")
        proc.run(("colima", "stop"), pathprepend=f"{reporoot}/.devenv/bin")

    # colima start will only WARN if rosetta is unavailable and keep going without it,
    # so we need to ensure it's installed and running ourselves
    rosetta.ensure()

    cpus = os.cpu_count()
    if cpus is None:
        raise SystemExit("failed to determine cpu count")

    # SC_PAGE_SIZE is POSIX 2008
    # SC_PHYS_PAGES is a linux addition but also supported by more recent MacOS versions
    SC_PAGE_SIZE = os.sysconf("SC_PAGE_SIZE")
    SC_PHYS_PAGES = os.sysconf("SC_PHYS_PAGES")
    if SC_PAGE_SIZE == -1 or SC_PHYS_PAGES == -1:
        raise SystemExit("failed to determine memsize_bytes")
    memsize_bytes = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")

    args = ["--cpu", f"{cpus//2}", "--memory", f"{memsize_bytes//(2*1024**3)}"]
    if platform.machine() == "arm64":
        args = [*args, "--vm-type=vz", "--vz-rosetta", "--mount-type=virtiofs"]

    proc.run(
        (
            # we share the "default" machine across repositories
            "colima",
            "start",
            "--verbose",
            # ideally we keep ~ ro and reporoot rw, but currently the "default" vm
            # is shared across repositories, so for ease of use we'll let home rw
            f"--mount=/var/folders:w,/private/tmp/colima:w,{home}:w",
            *args,
        ),
        pathprepend=f"{reporoot}/.devenv/bin",
    )

    proc.run(("docker", "context", "use", "colima"))

    status = check(reporoot)
    return status


def restart(reporoot: str) -> ColimaStatus:
    status = start(reporoot, restart=True)
    return status


def stop(reporoot: str) -> ColimaStatus:
    proc.run(("colima", "stop"), pathprepend=f"{reporoot}/.devenv/bin")
    status = check(reporoot)
    return status
