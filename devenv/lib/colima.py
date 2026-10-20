from __future__ import annotations

import json
import os
import platform
import re
import shutil
import stat
import tempfile
from collections.abc import Collection
from dataclasses import dataclass
from enum import Enum
from typing import cast

from devenv import constants
from devenv.constants import SYSTEM_MACHINE
from devenv.constants import home
from devenv.constants import root
from devenv.lib import archive
from devenv.lib import colima_config
from devenv.lib import docker
from devenv.lib import fs
from devenv.lib import proc
from devenv.lib import rosetta

ColimaStatus = Enum("ColimaStatus", ("UP", "DOWN", "UNHEALTHY"))


class _StartMode(Enum):
    ENSURE_RUNNING = "ensure-running"
    REQUESTED_RESTART = "requested-restart"
    HEALTH_RECOVERY = "health-recovery"


@dataclass(frozen=True)
class _StoragePolicy:
    existing_instance: bool
    expected_snapshotter: bool | None = None


def _install(url: str, sha256: str, into: str) -> None:
    os.makedirs(into, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=into) as tmpd:
        downloaded = archive.download(url, sha256, dest=f"{tmpd}/colima")
        os.chmod(downloaded, 0o775)
        os.replace(downloaded, f"{into}/colima-bin")


def uninstall(binroot: str) -> None:
    for fp in (f"{binroot}/colima", f"{binroot}/colima-bin"):
        try:
            os.remove(fp)
        except FileNotFoundError:
            pass


def install_shim(binroot: str) -> None:
    fs.write_script(
        f"{binroot}/colima",
        """#!/bin/sh
export COLIMA_HOME={home}/.colima

unset XDG_CONFIG_HOME

exec {binroot}/colima-bin "$@"
""",
        shell_escape={"binroot": binroot, "home": home},
    )


def _installed_colima_version(command: str) -> str | None:
    try:
        stdout = proc.run((command, "--version"), stdout=True)
    except RuntimeError as error:
        print(f"existing Colima installation is incomplete: {error}")
        return None
    words = stdout.strip().split()
    if not words:
        print("existing Colima installation returned no version; reinstalling")
        return None
    return words[-1]


def install_global() -> None:
    version = "v0.10.3"
    cfg = {
        "darwin_x86_64": f"https://github.com/abiosoft/colima/releases/download/{version}/colima-Darwin-x86_64",
        "darwin_x86_64_sha256": "3082737fe8a98afda11cba7d9a20b6e56fe80c6153464beda04bec630758770b",
        "darwin_arm64": f"https://github.com/abiosoft/colima/releases/download/{version}/colima-Darwin-arm64",
        "darwin_arm64_sha256": "980ad8bf61a4ca370243f4cb41401a61276dcd2c2502bee7b9b86f9250169f34",
    }

    binroot = f"{root}/bin"

    colima_path = f"{binroot}/colima"
    binary_path = f"{binroot}/colima-bin"
    if shutil.which("colima", path=binroot) == colima_path:
        installed_version = _installed_colima_version(colima_path)
        if not os.path.exists(binary_path) and installed_version is not None:
            os.replace(colima_path, binary_path)
            install_shim(binroot)
            installed_version = _installed_colima_version(colima_path)
        if version == installed_version:
            return
        if installed_version is not None:
            print(f"installed colima {installed_version} is unexpected!")

    print(f"installing colima {version}...")
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

    try:
        proc.run(
            (docker_executable, "--context=colima", "version"), stdout=True
        )
    except RuntimeError:
        return ColimaStatus.UNHEALTHY

    healthy = docker.check_docker_to_host_connectivity(context="colima")
    if not healthy:
        return ColimaStatus.UNHEALTHY

    return ColimaStatus.UP


def _colima_lima_home() -> str:
    return constants.user_environ.get("LIMA_HOME") or f"{home}/.colima/_lima"


def _instance_path() -> str:
    return f"{_colima_lima_home()}/colima"


def _config_path() -> str:
    return f"{home}/.colima/default/colima.yaml"


def _template_path() -> str:
    return f"{home}/.colima/_templates/default.yaml"


def _read_optional_config(path: str) -> colima_config.ColimaConfig | None:
    try:
        os.lstat(path)
    except FileNotFoundError:
        return None
    except OSError as error:
        raise colima_config.StorageMigrationBlocked(
            f"Unable to inspect Colima config {path}: {error}. Inspect the "
            "config before starting a new VM."
        ) from error
    return colima_config.read(path)


def _instance_exists() -> bool:
    path = _instance_path()
    try:
        mode = os.lstat(path).st_mode
    except FileNotFoundError:
        return False
    except OSError as error:
        raise colima_config.StorageMigrationBlocked(
            f"Unable to inspect Colima's Lima instance path {path}: {error}. "
            "Inspect the existing VM before starting it."
        ) from error
    if stat.S_ISLNK(mode):
        raise colima_config.StorageMigrationBlocked(
            f"Colima's Lima instance path {path} is a symlink; inspect the "
            "existing VM location before starting it."
        )
    if not stat.S_ISDIR(mode):
        raise colima_config.StorageMigrationBlocked(
            f"Colima's Lima instance path {path} is not a directory; inspect "
            "the existing VM before starting it."
        )
    return True


def _docker_store_from_info() -> bool:
    try:
        output = proc.run(
            (
                "docker",
                "--context=colima",
                "info",
                "--format",
                "{{.Driver}}|{{json .DriverStatus}}",
            ),
            stdout=True,
        )
    except RuntimeError as error:
        raise colima_config.StorageMigrationBlocked(
            "The existing Colima VM is running, but Docker's storage backend "
            f"could not be verified through the `colima` context: {error}. "
            "No backend setting was changed. Restore Docker connectivity, "
            "then run `devenv colima start` again."
        ) from error

    driver, separator, details = output.partition("|")
    if not separator:
        raise colima_config.StorageMigrationBlocked(
            "Docker returned an unrecognized `info` response for the `colima` "
            "context. No backend setting was changed. Inspect `docker "
            "--context=colima info` before starting Colima."
        )
    try:
        driver_status = json.loads(details)
    except json.JSONDecodeError as error:
        if driver.strip() == "overlay2":
            return False
        raise colima_config.StorageMigrationBlocked(
            "Docker returned invalid storage-driver details for the `colima` "
            "context. No backend setting was changed. Inspect `docker "
            "--context=colima info` before starting Colima."
        ) from error
    if isinstance(driver_status, list) and any(
        isinstance(entry, list)
        and len(entry) == 2
        and entry[0] == "driver-type"
        and entry[1] == "io.containerd.snapshotter.v1"
        for entry in driver_status
    ):
        return True
    if driver.strip() == "overlay2":
        return False
    if not isinstance(driver_status, list):
        raise colima_config.StorageMigrationBlocked(
            "Docker returned an unrecognized storage-driver response for the "
            "`colima` context. No backend setting was changed. Inspect "
            "`docker --context=colima info` before starting Colima."
        )
    raise colima_config.StorageMigrationBlocked(
        f"Docker reports storage driver `{driver.strip()}`, which devenv "
        "cannot safely classify. No backend setting was changed. Inspect "
        "`docker --context=colima info` before starting Colima."
    )


def _legacy_root_disk(config: colima_config.ColimaConfig) -> bool:
    store_path = f"{home}/.colima/_store/colima.json"
    store: dict[str, object] | None = None
    try:
        store_mode = os.lstat(store_path).st_mode
    except FileNotFoundError:
        store_mode = None
    except OSError as error:
        raise colima_config.StorageMigrationBlocked(
            f"Unable to inspect Colima store metadata {store_path}: {error}. "
            "Inspect the existing VM before starting it."
        ) from error
    if store_mode is not None and stat.S_ISLNK(store_mode):
        raise colima_config.StorageMigrationBlocked(
            f"Colima store metadata {store_path} is a symlink; inspect it "
            "before starting the VM."
        )
    if store_mode is not None:
        if not stat.S_ISREG(store_mode):
            raise colima_config.StorageMigrationBlocked(
                f"Colima store metadata {store_path} is not a regular file; "
                "inspect the existing VM before starting it."
            )
        try:
            with open(store_path, encoding="utf-8") as store_file:
                parsed = json.load(store_file)
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise colima_config.StorageMigrationBlocked(
                f"Unable to read Colima store metadata {store_path}: {error}. "
                "Inspect the existing VM before starting it."
            ) from error
        if not isinstance(parsed, dict):
            raise colima_config.StorageMigrationBlocked(
                f"Colima store metadata {store_path} has an unsupported "
                "format; inspect the existing VM before starting it."
            )
        store = cast(dict[str, object], parsed)

    if store is not None:
        formatted = store.get("disk_formatted")
        runtime = store.get("disk_runtime")
        if not isinstance(formatted, bool) or not isinstance(runtime, str):
            raise colima_config.StorageMigrationBlocked(
                f"Colima store metadata {store_path} has unknown disk fields; "
                "inspect the existing VM before starting it."
            )
        if formatted or runtime:
            return False

    limactl_path = f"{root}/bin/limactl"
    if not os.path.isfile(limactl_path):
        raise colima_config.StorageMigrationBlocked(
            f"Cannot verify whether Colima has a persistent data disk because "
            f"`{limactl_path}` is missing. Finish `devenv update` and retry."
        )
    try:
        disk_info = proc.run(
            (limactl_path, "disk", "list", "--json", "colima"),
            stdout=True,
            env={"LIMA_HOME": _colima_lima_home()},
        )
    except RuntimeError as error:
        raise colima_config.StorageMigrationBlocked(
            "Cannot verify whether the existing Colima VM has a persistent "
            f"data disk: {error}. No backend setting was changed."
        ) from error
    if disk_info.strip():
        try:
            disk = json.loads(disk_info)
        except json.JSONDecodeError as error:
            raise colima_config.StorageMigrationBlocked(
                "Lima returned invalid disk metadata for Colima. No backend "
                "setting was changed; repair the Lima installation and retry."
            ) from error
    else:
        disk = None
    if disk is not None and not isinstance(disk, dict):
        raise colima_config.StorageMigrationBlocked(
            "Lima returned an unsupported disk metadata format for Colima. "
            "No backend setting was changed."
        )
    if isinstance(disk, dict):
        disk_name = disk.get("name")
        if disk_name == "colima":
            return False
        if disk_name not in {None, ""}:
            raise colima_config.StorageMigrationBlocked(
                f"Lima reports unexpected disk `{disk_name}` for Colima. "
                "No backend setting was changed."
            )

    return (
        not config.root_disk_configured
        and config.disk_gib == 512
        and config.runtime in {None, "docker"}
    )


def _prepare_docker_store(status: ColimaStatus) -> _StoragePolicy:
    if not _instance_exists():
        config_path = _config_path()
        profile_config = _read_optional_config(config_path)
        config = profile_config
        template = None
        if config is None or config.runtime is None:
            template = _read_optional_config(_template_path())
            if template is not None:
                config = template
        if config is None:
            return _StoragePolicy(
                existing_instance=False, expected_snapshotter=True
            )
        if (
            config is profile_config
            and profile_config is not None
            and profile_config.runtime is None
            and template is None
            and profile_config.snapshotter is not None
        ):
            raise colima_config.StorageMigrationBlocked(
                f"Colima profile {config_path} has an explicit Docker storage "
                "choice but no runtime. Colima treats this profile as empty "
                "and will ignore that choice. Set `runtime: docker` before "
                "starting the VM."
            )
        if config.runtime not in {None, "docker"}:
            return _StoragePolicy(existing_instance=False)
        if (
            config.snapshotter is None
            and config is profile_config
            and config.runtime
        ):
            _persist_docker_store(config_path, True)
        if config.snapshotter is None:
            return _StoragePolicy(
                existing_instance=False, expected_snapshotter=True
            )
        return _StoragePolicy(
            existing_instance=False, expected_snapshotter=config.snapshotter
        )

    config_path = _config_path()
    config = colima_config.read(config_path)
    if config.runtime not in {None, "docker"}:
        return _StoragePolicy(existing_instance=True)
    if config.snapshotter is not None:
        return _StoragePolicy(
            existing_instance=True, expected_snapshotter=config.snapshotter
        )

    if status == ColimaStatus.DOWN:
        overlay2 = _legacy_root_disk(config)
        if not overlay2:
            raise colima_config.StorageMigrationBlocked(
                "The stopped Colima VM has no explicit Docker storage choice, "
                "and its data-disk metadata does not prove which image store "
                "contains its images and containers. Colima 0.10.3 could hide "
                "them on the next start. Inspect the existing backend, then "
                "set `docker.features.containerd-snapshotter: false` for "
                "overlay2 or `true` for containerd in "
                f"`{config_path}`. Do not delete the VM or its disks."
            )
        selected_store = False
    else:
        try:
            selected_store = _docker_store_from_info()
        except colima_config.StorageMigrationBlocked as error:
            if status != ColimaStatus.UNHEALTHY:
                raise
            try:
                overlay2 = _legacy_root_disk(config)
            except colima_config.StorageMigrationBlocked as metadata_error:
                raise colima_config.StorageMigrationBlocked(
                    f"{error} Saved Colima metadata could not establish an "
                    f"overlay2 legacy VM: {metadata_error}"
                ) from metadata_error
            if not overlay2:
                raise colima_config.StorageMigrationBlocked(
                    f"{error} Saved Colima metadata does not positively "
                    "identify an overlay2 legacy VM. Inspect the existing "
                    "Docker store before starting it."
                ) from error
            selected_store = False

    _persist_docker_store(config_path, selected_store)
    return _StoragePolicy(
        existing_instance=True, expected_snapshotter=selected_store
    )


def _persist_docker_store(config_path: str, snapshotter: bool) -> None:
    changed = colima_config.set_snapshotter(config_path, snapshotter)
    updated_config = colima_config.read(config_path)
    if updated_config.snapshotter != snapshotter:
        raise colima_config.StorageMigrationBlocked(
            f"Colima config {config_path} changed while its Docker store was "
            "being preserved. Inspect the config and Docker backend before "
            "starting Colima."
        )
    if changed:
        store = "containerd" if snapshotter else "overlay2"
        print(f"Configured Colima's Docker {store} image store.")


def _persist_new_docker_store(
    status: ColimaStatus, storage_policy: _StoragePolicy
) -> ColimaStatus:
    snapshotter = storage_policy.expected_snapshotter
    if (
        status != ColimaStatus.UP
        or storage_policy.existing_instance
        or snapshotter is None
    ):
        return status

    try:
        config_path = _config_path()
        config = colima_config.read(config_path)
        if config.runtime not in {None, "docker"}:
            raise colima_config.StorageMigrationBlocked(
                f"Colima saved runtime `{config.runtime}` for a new VM, but "
                "devenv requires Docker storage. Inspect the runtime config "
                "before restarting Colima."
            )
        if config.snapshotter is not None and config.snapshotter != snapshotter:
            raise colima_config.StorageMigrationBlocked(
                f"Colima config {config_path} selected a Docker image store "
                "that differs from the choice made before startup. Inspect "
                "the live Docker backend before restarting Colima."
            )
        if config.snapshotter is None:
            _persist_docker_store(config_path, snapshotter)
    except colima_config.StorageMigrationBlocked as error:
        print(
            "ERROR: Colima started, but devenv could not persist its Docker "
            f"image-store choice: {error}"
        )
        return ColimaStatus.UNHEALTHY

    return status


def _verify_storage_after_start(
    status: ColimaStatus,
    storage_policy: _StoragePolicy,
    *,
    vm_was_started: bool,
) -> ColimaStatus:
    if (
        status != ColimaStatus.UP
        or not vm_was_started
        or storage_policy.expected_snapshotter is None
    ):
        return status

    try:
        actual = _docker_store_from_info()
    except colima_config.StorageMigrationBlocked as error:
        print(f"ERROR: Cannot verify Colima's Docker image store: {error}")
        return ColimaStatus.UNHEALTHY

    if actual != storage_policy.expected_snapshotter:
        expected_store = (
            "containerd" if storage_policy.expected_snapshotter else "overlay2"
        )
        actual_store = "containerd" if actual else "overlay2"
        print(
            f"ERROR: Colima started with Docker's {actual_store} image store, "
            f"but devenv preserved {expected_store}. Images and containers "
            "may be hidden. Stop Colima and inspect its Docker data before "
            "changing `containerd-snapshotter`; do not delete the VM or disks."
        )
        return ColimaStatus.UNHEALTHY

    return status


_APT_GET = (
    "sudo",
    "env",
    "DEBIAN_FRONTEND=noninteractive",
    "apt-get",
    "-q",
    "-o",
    "DPkg::Lock::Timeout=120",
)


def _vm_run(*cmd: str) -> str:
    return proc.run(
        ("colima", "ssh", "--", *cmd), pathprepend=f"{root}/bin", stdout=True
    )


def _vm_exec(*cmd: str) -> None:
    proc.run(("colima", "ssh", "--", *cmd), pathprepend=f"{root}/bin")


def _host_has_sme() -> bool:
    if not (constants.DARWIN and constants.MACHINE == "arm64"):
        return False
    try:
        out = proc.run(
            ("/usr/sbin/sysctl", "-n", "hw.optional.arm.FEAT_SME"), stdout=True
        )
    except RuntimeError:
        return False
    return out == "1"


def _misreports_sve(features: Collection[str]) -> bool:
    return "sve" not in features and any(f.startswith("sve") for f in features)


def vm_misreports_sve() -> bool:
    if not _host_has_sme():
        return False
    out = _vm_run("grep", "-m1", "^Features", "/proc/cpuinfo")
    return _misreports_sve(out.partition(":")[2].split())


def _kernel_version_key(version: str) -> tuple[int, ...]:
    return tuple(int(n) for n in re.findall(r"\d+", version))


def _vm_newest_kernel() -> str:
    versions = _vm_run("linux-version", "list").split()
    if not versions:
        raise RuntimeError("found no kernels in colima's VM")
    return max(versions, key=_kernel_version_key)


def _upgrade_kernel_if_sve_misreported(*, restarting: bool) -> bool:
    try:
        if not vm_misreports_sve():
            return False
        running = _vm_run("uname", "-r")
        newest = _vm_newest_kernel()
    except RuntimeError as e:
        print(f"WARNING: failed to check colima's VM kernel: {e}")
        return False

    if newest != running:
        if restarting:
            return True
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
    status = check()
    try:
        storage_policy = _prepare_docker_store(status)
    except colima_config.StorageMigrationBlocked as error:
        print(f"ERROR: Cannot safely start Colima: {error}")
        return ColimaStatus.UNHEALTHY

    if status == ColimaStatus.UP and restart:
        boot_kernel = _upgrade_kernel_if_sve_misreported(restarting=True)
        status = _start_with_health_recovery(
            _StartMode.REQUESTED_RESTART,
            status,
            storage_policy.existing_instance,
        )
        status = _verify_storage_after_start(
            status, storage_policy, vm_was_started=True
        )
        if boot_kernel:
            return _report_booted_kernel(status)
        return status

    vm_was_started = status != ColimaStatus.UP
    if status == ColimaStatus.UNHEALTHY:
        print("colima seems unhealthy, attempting one recovery restart")
        status = _start(
            _StartMode.HEALTH_RECOVERY,
            status,
            existing_instance=storage_policy.existing_instance,
        )
    else:
        status = _start_with_health_recovery(
            _StartMode.ENSURE_RUNNING, status, storage_policy.existing_instance
        )

    vm_was_started = vm_was_started or status != ColimaStatus.UP
    status = _persist_new_docker_store(status, storage_policy)
    status = _verify_storage_after_start(
        status, storage_policy, vm_was_started=vm_was_started
    )
    if status != ColimaStatus.UP:
        return status

    boot_kernel = _upgrade_kernel_if_sve_misreported(restarting=restart)
    if not boot_kernel:
        return status

    status = _start_with_health_recovery(
        _StartMode.REQUESTED_RESTART, status, existing_instance=True
    )
    status = _verify_storage_after_start(
        status, storage_policy, vm_was_started=True
    )
    return _report_booted_kernel(status)


def _start_with_health_recovery(
    mode: _StartMode, status: ColimaStatus, existing_instance: bool
) -> ColimaStatus:
    status = _start(mode, status, existing_instance=existing_instance)
    if status != ColimaStatus.UNHEALTHY or mode == _StartMode.HEALTH_RECOVERY:
        return status

    print("colima seems unhealthy, attempting one recovery restart")
    return _start(_StartMode.HEALTH_RECOVERY, existing_instance=True)


def _report_booted_kernel(status: ColimaStatus) -> ColimaStatus:
    if status != ColimaStatus.UP:
        print("""
WARNING: colima isn't healthy after restarting to boot the VM's upgraded
kernel. Ask for help in #discuss-dev-infra.
""")
        return status

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


def _start(
    mode: _StartMode,
    status: ColimaStatus | None = None,
    *,
    existing_instance: bool = False,
) -> ColimaStatus:
    if status is None:
        status = check()

    if status == ColimaStatus.UP and mode != _StartMode.REQUESTED_RESTART:
        proc.run(("docker", "context", "use", "colima"))
        return status

    try:
        proc.run(("docker", "context", "use", "default"))
    except RuntimeError as error:
        print(f"Failed to switch docker context: {error}")

    if status == ColimaStatus.UP:
        try:
            proc.run(("colima", "stop"), pathprepend=f"{root}/bin")
        except RuntimeError as error:
            raise SystemExit(
                f"Failed to stop healthy Colima gracefully: {error}. "
                "Resolve the stop failure before retrying."
            ) from error
    elif status == ColimaStatus.UNHEALTHY:
        try:
            proc.run(("colima", "stop", "-f"), pathprepend=f"{root}/bin")
        except RuntimeError as error:
            print(f"Failed to force stop unhealthy Colima: {error}")

    rosetta.ensure()

    cpus = os.cpu_count()
    if cpus is None:
        raise SystemExit("failed to determine cpu count")

    page_size = os.sysconf("SC_PAGE_SIZE")
    physical_pages = os.sysconf("SC_PHYS_PAGES")
    if page_size == -1 or physical_pages == -1:
        raise SystemExit("failed to determine memsize_bytes")
    memsize_bytes = page_size * physical_pages

    args = ["--verbose"]
    if not existing_instance:
        args.extend(
            (
                "--save-config",
                "--cpus",
                f"{cpus // 2}",
                "--memory",
                f"{memsize_bytes // (2 * 1024**3)}",
                "--disk",
                "512",
                "--dns",
                "8.8.8.8",
                "--dns",
                "1.1.1.1",
                f"--mount=/var/folders:w,/private/tmp/colima:w,{home}:w,/tmp/sentry-profiles:w",
            )
        )
        if platform.machine() == "arm64":
            args.extend(
                ("--vm-type=vz", "--vz-rosetta", "--mount-type=virtiofs")
            )

    proc.run(("colima", "start", *args), pathprepend=f"{root}/bin")

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
