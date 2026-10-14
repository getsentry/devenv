from __future__ import annotations

import os
import platform
import re
import shutil
import tempfile
from collections.abc import Collection
from enum import Enum

from devenv import constants
from devenv.constants import SYSTEM_MACHINE
from devenv.constants import home
from devenv.constants import root
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


def install_global() -> None:
    version = "v0.8.1"
    cfg = {
        "darwin_x86_64": f"https://github.com/abiosoft/colima/releases/download/{version}/colima-Darwin-x86_64",
        "darwin_x86_64_sha256": "791330c62c60389f70e5e1c33a56c35502a9e36e544a418daea0273e539acbf4",
        "darwin_arm64": f"https://github.com/abiosoft/colima/releases/download/{version}/colima-Darwin-arm64",
        "darwin_arm64_sha256": "c266fcb272b39221ef6152d2093bb02a1ebadc26042233ad359e1ae52d5d5922",
    }

    binroot = f"{root}/bin"

    if shutil.which("colima", path=binroot) == f"{binroot}/colima":
        if not os.path.exists(f"{binroot}/colima-bin"):
            os.rename(f"{binroot}/colima", f"{binroot}/colima-bin")
            install_shim(binroot)

        stdout = proc.run((f"{binroot}/colima", "--version"), stdout=True)
        installed_version = stdout.strip().split()[-1]
        if version == installed_version:
            return
        print(f"installed colima {installed_version} is unexpected!")

    print(f"installing colima {version}...")
    uninstall(binroot)
    _install(cfg[SYSTEM_MACHINE], cfg[f"{SYSTEM_MACHINE}_sha256"], binroot)
    install_shim(binroot)

    if SYSTEM_MACHINE == "darwin_x86_64":
        if not shutil.which("qemu"):
            print(
                "WARNING: you're on darwin_x86_64, but QEMU isn't installed. Run: `brew install qemu`."
            )

    stdout = proc.run((f"{binroot}/colima", "--version"), stdout=True)
    if f"colima version {version}" not in stdout:
        raise SystemExit(f"Failed to install colima {version}! Found: {stdout}")


def install(version: str, url: str, sha256: str, reporoot: str) -> None:
    install_global()


def check() -> ColimaStatus:
    if not os.getenv("CI"):
        macos_version = platform.mac_ver()[0]
        macos_major_version = int(macos_version.split(".")[0])
        if macos_major_version < 15:
            raise SystemExit(
                f"macos >= 15 is required to use colima, found {macos_version}"
            )

    docker_executable = shutil.which("docker")
    if not docker_executable:
        raise SystemExit(
            "docker executable not found, you might want to run devenv sync"
        )

    colima_executable = shutil.which("colima")
    if not colima_executable:
        raise SystemExit(
            "colima executable not found, try running devenv update (twice if this is your first time doing this) to install"
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


# Linux kernels without 064737920bdb ("arm64: Filter out SVE hwcaps when
# FEAT_SVE isn't implemented", v6.14, Ubuntu Noble 6.8.0-64.67) derive the SVE2
# family of hwcaps from an ID register that SME also populates, without
# checking that SVE exists. Apple M4 and newer have SME but no SVE, and macOS
# 15.2+ exposes SME to VMs, so the kernel in VMs made by colima 0.8.1 (Ubuntu
# 24.04.1, 6.8.0-50) tells programs they can use SVE2. Anything that believes
# it, like OpenSSL 4 (bundled in Python's cryptography >= 47) or numba, dies
# with SIGILL. The image is only used to create a VM, so upgrading colima
# doesn't fix existing VMs; upgrading the kernel inside them does.
# https://lore.kernel.org/all/20250103142635.1759674-1-maz@kernel.org/

_APT_GET = (
    "sudo",
    "env",
    "DEBIAN_FRONTEND=noninteractive",
    "apt-get",
    "-q",
    # wait out apt-daily if it happens to be running
    "-o",
    "DPkg::Lock::Timeout=120",
)


def _vm_run(*cmd: str) -> str:
    """Runs cmd in colima's VM and returns its output."""
    return proc.run(
        ("colima", "ssh", "--", *cmd), pathprepend=f"{root}/bin", stdout=True
    )


def _vm_exec(*cmd: str) -> None:
    """Runs cmd in colima's VM, showing its output as it goes."""
    proc.run(("colima", "ssh", "--", *cmd), pathprepend=f"{root}/bin")


def _host_has_sme() -> bool:
    """
    Only Macs with SME can be affected, so checking this first spares
    everyone else from probing the VM on every start.
    """
    if not (constants.DARWIN and constants.MACHINE == "arm64"):
        return False
    try:
        out = proc.run(
            ("/usr/sbin/sysctl", "-n", "hw.optional.arm.FEAT_SME"), stdout=True
        )
    except RuntimeError:
        # chips without SME (M1-M3) don't have this sysctl at all
        return False
    return out == "1"


def _misreports_sve(features: Collection[str]) -> bool:
    # sve2, svei8mm, svebf16, ... all depend on sve
    return "sve" not in features and any(f.startswith("sve") for f in features)


def vm_misreports_sve() -> bool:
    """
    Whether colima's VM tells programs they can use SVE on a CPU without it.
    Raises RuntimeError if the VM can't be reached.
    """
    if not _host_has_sme():
        return False
    # Features	: fp asimd evtstrm ... sve2 ...
    out = _vm_run("grep", "-m1", "^Features", "/proc/cpuinfo")
    return _misreports_sve(out.partition(":")[2].split())


def _kernel_version_key(version: str) -> tuple[int, ...]:
    # 6.8.0-147-generic sorts after 6.8.0-50-generic
    return tuple(int(n) for n in re.findall(r"\d+", version))


def _vm_newest_kernel() -> str:
    """The kernel that grub boots by default."""
    versions = _vm_run("linux-version", "list").split()
    if not versions:
        raise RuntimeError("found no kernels in colima's VM")
    return max(versions, key=_kernel_version_key)


def _upgrade_kernel_if_sve_misreported() -> bool:
    """
    Installs a fixed kernel if colima's VM misreports SVE, and returns
    whether the VM has to be restarted to boot it.

    Failures only warn: everything that doesn't use SVE still works,
    so they shouldn't fail `devenv colima start`.
    """
    try:
        if not vm_misreports_sve():
            return False
        running = _vm_run("uname", "-r")
        newest = _vm_newest_kernel()
    except RuntimeError as e:
        print(f"WARNING: failed to check colima's VM kernel: {e}")
        return False

    if newest != running:
        # Either a previous upgrade's restart was interrupted, or the VM
        # didn't boot the new kernel. In the latter case restarting would
        # happen again on every start, so leave it to the user.
        print(f"""
WARNING: colima's VM is running Linux {running}, which misreports SVE
support on this CPU, but Linux {newest} is already installed.
Run `devenv colima restart` to boot it. If the VM still runs
Linux {running} after that, ask for help in #discuss-dev-infra.
""")
        return False

    print(f"""
colima's VM is running Linux {running}, which tells programs that this Mac's
CPU supports SVE2. Apple M4 and newer don't have SVE, so anything that
believes it (e.g. OpenSSL 4 in Python's cryptography >= 47, or numba) crashes
with "Illegal instruction".

Installing a newer kernel in the VM, then restarting colima once to boot it.
Your containers and volumes are kept.
""")
    try:
        _vm_exec(*_APT_GET, "update")
        _vm_exec(*_APT_GET, "install", "-y", "linux-image-virtual")
        # make sure the kernel, initrd and grub config are on disk
        # in case the VM ends up being force stopped
        _vm_exec("sync")
        newest = _vm_newest_kernel()
    except RuntimeError as e:
        print(f"""
WARNING: failed to upgrade colima's VM kernel: {e}
`devenv colima start` will try again next time.
""")
        return False

    if newest == running:
        print(f"""
WARNING: no kernel newer than Linux {running} is available to colima's VM.
Ask for help in #discuss-dev-infra.
""")
        return False

    print(f"Installed Linux {newest}, restarting colima to boot it.")
    return True


def start(restart: bool = False) -> ColimaStatus:
    status = _start(restart)
    if status != ColimaStatus.UP:
        return status

    if not _upgrade_kernel_if_sve_misreported():
        return status

    # unlike when _start stops it, the VM is healthy here,
    # so let its containers shut down cleanly
    try:
        proc.run(("colima", "stop"), pathprepend=f"{root}/bin")
    except RuntimeError as e:
        print(f"Failed to stop colima: {e}")

    status = _start(restart=True)
    if status != ColimaStatus.UP:
        print("""
WARNING: colima isn't healthy after restarting to boot the VM's upgraded
kernel. Ask for help in #discuss-dev-infra.
""")
        return status

    # only ever upgrade and restart once: if that didn't work,
    # doing it again won't either
    try:
        running = _vm_run("uname", "-r")
        still_misreported = vm_misreports_sve()
    except RuntimeError as e:
        print(f"WARNING: failed to check colima's VM kernel: {e}")
        return status

    if still_misreported:
        print(f"""
WARNING: colima's VM still misreports SVE support after booting
Linux {running}. Ask for help in #discuss-dev-infra.
""")
    else:
        print(f"colima's VM is now running Linux {running}.")

    return status


def _start(restart: bool) -> ColimaStatus:
    # switch to default context to avoid broken contexts (e.g., desktop-linux)
    try:
        proc.run(("docker", "context", "use", "default"))
    except RuntimeError as e:
        print(f"Failed to switch docker context: {e}")

    status = check()

    if status == ColimaStatus.UP:
        if not restart:
            return ColimaStatus.UP

    # always stop first (colima's internal state can get out of sync)
    try:
        proc.run(("colima", "stop", "-f"), pathprepend=f"{root}/bin")
    except RuntimeError as e:
        print(f"Failed to stop colima: {e}")

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

    args = [
        "--cpu",
        f"{cpus // 2}",
        "--memory",
        f"{memsize_bytes // (2 * 1024**3)}",
    ]
    if platform.machine() == "arm64":
        args = [*args, "--vm-type=vz", "--vz-rosetta", "--mount-type=virtiofs"]

    proc.run(
        (
            # we share the "default" machine across repositories
            "colima",
            "start",
            "--verbose",
            # we're overprovisioning a 512 GiB disk here which is fine because
            # the disk doesn't reserve space and is copy-on-write
            "--disk",
            "512",
            # this effectively makes the vm's resolvectl status use:
            # DNS Servers: 8.8.8.8 1.1.1.1 192.168.5.2
            # https://lima-vm.io/docs/config/network/user/
            # 192.168.5.2 is the host, accessible from the vm
            # sometimes using only the host will result in dns breaking
            # for any number of reasons (public wifi that gives you some weird dns server,
            # tethering, vpn, what have you)
            "--dns",
            "8.8.8.8",
            "--dns",
            "1.1.1.1",
            # ideally we keep ~ ro, but currently the "default" vm
            # is shared across repositories, so for ease of use we'll let home rw
            f"--mount=/var/folders:w,/private/tmp/colima:w,{home}:w,/tmp/sentry-profiles:w",
            # note: it is not allowed by lima to add top-level root directories like /tmp!
            *args,
        ),
        pathprepend=f"{root}/bin",
    )

    proc.run(("docker", "context", "use", "colima"))

    status = check()
    return status


def restart() -> ColimaStatus:
    status = start(restart=True)
    return status


def stop() -> ColimaStatus:
    proc.run(("colima", "stop"), pathprepend=f"{root}/bin")
    status = check()
    return status
