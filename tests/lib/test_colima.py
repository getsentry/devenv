from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from unittest import mock

import pytest

from devenv import constants
from devenv.lib import colima

# /proc/cpuinfo in colima 0.8.1's VM (Linux 6.8.0-50-generic) on an M4 Pro
M4_BUGGY_FEATURES = (
    "fp asimd evtstrm aes pmull sha1 sha2 crc32 atomics fphp asimdhp cpuid "
    "asimdrdm jscvt fcma lrcpc dcpop sha3 asimddp sha512 asimdfhm dit uscat "
    "ilrcpc flagm sb paca pacg dcpodp sve2 flagm2 frint svei8mm svebf16 i8mm "
    "bf16 bti afp sme smei16i64 smef64f64 smei8i32 smef16f32 smeb16f32 "
    "smef32f32 sme2 smei16i32 smebi32i32"
)
# ... and after upgrading it to Linux 6.8.0-147-generic
M4_FIXED_FEATURES = (
    "fp asimd evtstrm aes pmull sha1 sha2 crc32 atomics fphp asimdhp cpuid "
    "asimdrdm jscvt fcma lrcpc dcpop sha3 asimddp sha512 asimdfhm dit uscat "
    "ilrcpc flagm sb paca pacg dcpodp flagm2 frint i8mm bf16 bti afp"
)

BUGGY_KERNEL = "6.8.0-50-generic"
FIXED_KERNEL = "6.8.0-147-generic"

SYSCTL_SME = ("/usr/sbin/sysctl", "-n", "hw.optional.arm.FEAT_SME")
APT_UPDATE = ("colima", "ssh", "--", *colima._APT_GET, "update")
APT_INSTALL = (
    "colima",
    "ssh",
    "--",
    *colima._APT_GET,
    "install",
    "-y",
    "linux-image-virtual",
)


class FakeVM:
    """Answers the commands devenv runs on the host and in colima's VM."""

    def __init__(
        self,
        *,
        running: str = BUGGY_KERNEL,
        available: str = FIXED_KERNEL,
        buggy: frozenset[str] = frozenset((BUGGY_KERNEL,)),
        host_sme: bool = True,
        apt_works: bool = True,
        boots_newest: bool = True,
        start_results: tuple[colima.ColimaStatus, ...] = (),
    ) -> None:
        self.running = running
        self.installed = {running}
        self.available = available
        self.buggy = buggy
        self.host_sme = host_sme
        self.apt_works = apt_works
        self.boots_newest = boots_newest
        self.cmds: list[tuple[str, ...]] = []
        self.events: list[tuple[str, object]] = []
        self.restarts = 0
        self.recoveries = 0
        self.start_modes: list[colima._StartMode] = []
        self.start_existing_instances: list[bool] = []
        self.start_results = list(start_results)

    def run(
        self,
        cmd: tuple[str, ...],
        *,
        pathprepend: str = "",
        stdout: bool = False,
    ) -> str | None:
        self.cmds.append(cmd)
        self.events.append(("command", cmd))
        if cmd == SYSCTL_SME:
            if not self.host_sme:
                raise RuntimeError("sysctl: unknown oid")
            return "1"
        if cmd == ("colima", "stop"):
            return None
        if cmd in (APT_UPDATE, APT_INSTALL):
            if not self.apt_works:
                raise RuntimeError("Command `apt-get` failed! (code 100)")
            if cmd == APT_INSTALL:
                self.installed.add(self.available)
            return None

        assert cmd[:3] == ("colima", "ssh", "--"), cmd
        vm_cmd = cmd[3:]
        if vm_cmd == ("grep", "-m1", "^Features", "/proc/cpuinfo"):
            if self.running in self.buggy:
                return f"Features\t: {M4_BUGGY_FEATURES}"
            return f"Features\t: {M4_FIXED_FEATURES}"
        if vm_cmd == ("uname", "-r"):
            return self.running
        if vm_cmd == ("linux-version", "list"):
            return "\n".join(sorted(self.installed))
        if vm_cmd == ("sync",):
            return None
        raise AssertionError(f"unexpected command: {cmd}")

    def start(
        self,
        mode: colima._StartMode,
        status: colima.ColimaStatus | None = None,
        *,
        existing_instance: bool = False,
    ) -> colima.ColimaStatus:
        self.start_modes.append(mode)
        self.start_existing_instances.append(existing_instance)
        self.events.append(("start", mode))
        if mode == colima._StartMode.REQUESTED_RESTART:
            self.restarts += 1
        elif mode == colima._StartMode.HEALTH_RECOVERY:
            self.recoveries += 1
        if mode in {
            colima._StartMode.REQUESTED_RESTART,
            colima._StartMode.HEALTH_RECOVERY,
        }:
            if self.boots_newest:
                self.running = max(
                    self.installed, key=colima._kernel_version_key
                )
        if self.start_results:
            return self.start_results.pop(0)
        return colima.ColimaStatus.UP

    def ran(self, cmd: tuple[str, ...]) -> bool:
        return cmd in self.cmds


@pytest.fixture
def m4_mac() -> Generator[None]:
    with (
        mock.patch.object(constants, "DARWIN", True),
        mock.patch.object(constants, "MACHINE", "arm64"),
    ):
        yield


def _start(
    vm: FakeVM,
    restart: bool = False,
    initial_status: colima.ColimaStatus = colima.ColimaStatus.UP,
) -> colima.ColimaStatus:
    with (
        mock.patch("devenv.lib.colima.proc.run", side_effect=vm.run),
        mock.patch.object(colima, "_start", side_effect=vm.start),
        mock.patch.object(colima, "check", return_value=initial_status),
        mock.patch.object(
            colima,
            "_prepare_docker_store",
            return_value=colima._StoragePolicy(existing_instance=False),
        ),
    ):
        return colima.start(restart)


@pytest.mark.parametrize(
    ("features", "expected"),
    (
        # M4 and newer with an unfixed kernel
        (M4_BUGGY_FEATURES, True),
        (M4_FIXED_FEATURES, False),
        # e.g. AWS Graviton 3, which really has SVE
        ("fp asimd sve sve2 svei8mm svebf16 i8mm bf16", False),
        # M1-M3, no SVE or SME
        ("fp asimd evtstrm aes pmull sha1 sha2 crc32 atomics", False),
    ),
)
def test_misreports_sve(features: str, expected: bool) -> None:
    assert colima._misreports_sve(features.split()) is expected


def test_kernel_version_key_sorts_abi_numerically() -> None:
    newest = max(
        ("6.8.0-50-generic", "6.8.0-147-generic", "6.8.0-64-generic"),
        key=colima._kernel_version_key,
    )
    assert newest == "6.8.0-147-generic"


@pytest.mark.parametrize(
    ("darwin", "machine"),
    ((False, "x86_64"), (False, "aarch64"), (True, "x86_64")),
)
def test_vm_isnt_probed_on_linux_or_intel_macs(
    darwin: bool, machine: str
) -> None:
    vm = FakeVM()
    with (
        mock.patch.object(constants, "DARWIN", darwin),
        mock.patch.object(constants, "MACHINE", machine),
        mock.patch("devenv.lib.colima.proc.run", side_effect=vm.run),
    ):
        assert colima.vm_misreports_sve() is False
    assert vm.cmds == []


@pytest.mark.usefixtures("m4_mac")
def test_vm_isnt_probed_on_macs_without_sme() -> None:
    vm = FakeVM(host_sme=False)
    with mock.patch("devenv.lib.colima.proc.run", side_effect=vm.run):
        assert colima.vm_misreports_sve() is False
    assert vm.cmds == [SYSCTL_SME]


@pytest.mark.usefixtures("m4_mac")
def test_start_leaves_a_fixed_vm_alone() -> None:
    vm = FakeVM(running=FIXED_KERNEL)

    assert _start(vm) == colima.ColimaStatus.UP

    assert vm.restarts == 0
    assert not vm.ran(APT_INSTALL)


@pytest.mark.usefixtures("m4_mac")
def test_start_upgrades_the_kernel_and_restarts_once(
    capsys: pytest.CaptureFixture[str],
) -> None:
    vm = FakeVM()

    assert _start(vm) == colima.ColimaStatus.UP

    assert vm.ran(APT_UPDATE)
    assert vm.ran(APT_INSTALL)
    assert vm.events.index(("command", ("colima", "ssh", "--", "sync"))) < (
        vm.events.index(("start", colima._StartMode.REQUESTED_RESTART))
    )
    assert vm.restarts == 1
    assert vm.running == FIXED_KERNEL
    assert f"colima's VM is now running Linux {FIXED_KERNEL}." in (
        capsys.readouterr().out
    )

    # and a second start has nothing left to do
    vm.cmds.clear()
    assert _start(vm) == colima.ColimaStatus.UP
    assert vm.restarts == 1
    assert not vm.ran(APT_INSTALL)


@pytest.mark.usefixtures("m4_mac")
def test_start_restarts_only_once_if_the_new_kernel_doesnt_help(
    capsys: pytest.CaptureFixture[str],
) -> None:
    vm = FakeVM(buggy=frozenset((BUGGY_KERNEL, FIXED_KERNEL)))

    assert _start(vm) == colima.ColimaStatus.UP

    assert vm.restarts == 1
    assert vm.cmds.count(APT_INSTALL) == 1
    assert "still misreports SVE support" in capsys.readouterr().out

    # the newest kernel's running, but there's nothing newer to upgrade to
    vm.cmds.clear()
    assert _start(vm) == colima.ColimaStatus.UP
    assert vm.restarts == 1
    assert f"no kernel newer than Linux {FIXED_KERNEL}" in (
        capsys.readouterr().out
    )


@pytest.mark.usefixtures("m4_mac")
def test_start_doesnt_keep_restarting_into_an_old_kernel(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # e.g. grub pinned to an older kernel
    vm = FakeVM(boots_newest=False)

    assert _start(vm) == colima.ColimaStatus.UP
    assert vm.restarts == 1
    assert vm.running == BUGGY_KERNEL
    assert "still misreports SVE support" in capsys.readouterr().out

    for _ in range(2):
        vm.cmds.clear()
        assert _start(vm) == colima.ColimaStatus.UP
        assert vm.restarts == 1
        assert not vm.ran(APT_INSTALL)
        assert "Run `devenv colima restart` to boot it" in (
            capsys.readouterr().out
        )


@pytest.mark.usefixtures("m4_mac")
def test_restart_installs_the_kernel_before_its_one_reboot() -> None:
    vm = FakeVM()

    assert _start(vm, restart=True) == colima.ColimaStatus.UP

    assert vm.restarts == 1
    assert vm.ran(APT_INSTALL)
    assert vm.running == FIXED_KERNEL


@pytest.mark.usefixtures("m4_mac")
def test_restart_boots_an_installed_kernel_after_an_interrupted_repair(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # e.g. an earlier upgrade was interrupted before colima restarted
    vm = FakeVM()
    vm.installed.add(FIXED_KERNEL)

    assert _start(vm, restart=True) == colima.ColimaStatus.UP

    assert vm.running == FIXED_KERNEL
    assert vm.restarts == 1
    assert not vm.ran(APT_INSTALL)
    output = capsys.readouterr().out
    assert f"colima's VM is now running Linux {FIXED_KERNEL}." in output
    assert "Run `devenv colima restart`" not in output


@pytest.mark.usefixtures("m4_mac")
def test_start_carries_on_if_apt_fails(
    capsys: pytest.CaptureFixture[str],
) -> None:
    vm = FakeVM(apt_works=False)

    assert _start(vm) == colima.ColimaStatus.UP

    assert vm.restarts == 0
    assert "failed to upgrade colima's VM kernel" in capsys.readouterr().out


@pytest.mark.usefixtures("m4_mac")
def test_start_carries_on_if_the_vm_cant_be_probed(
    capsys: pytest.CaptureFixture[str],
) -> None:
    def run(cmd: tuple[str, ...], **kwargs: object) -> str:
        if cmd == SYSCTL_SME:
            return "1"
        raise RuntimeError("Command `colima ssh` failed! (code 1)")

    with (
        mock.patch("devenv.lib.colima.proc.run", side_effect=run),
        mock.patch.object(colima, "check", return_value=colima.ColimaStatus.UP),
        mock.patch.object(
            colima,
            "_prepare_docker_store",
            return_value=colima._StoragePolicy(existing_instance=False),
        ),
        mock.patch.object(
            colima, "_start", return_value=colima.ColimaStatus.UP
        ),
    ):
        assert colima.start() == colima.ColimaStatus.UP

    assert "failed to check colima's VM kernel" in capsys.readouterr().out


@pytest.mark.usefixtures("m4_mac")
def test_start_doesnt_probe_an_unhealthy_vm() -> None:
    vm = FakeVM()
    with (
        mock.patch("devenv.lib.colima.proc.run", side_effect=vm.run),
        mock.patch.object(
            colima, "check", return_value=colima.ColimaStatus.UNHEALTHY
        ),
        mock.patch.object(
            colima,
            "_prepare_docker_store",
            return_value=colima._StoragePolicy(existing_instance=False),
        ),
        mock.patch.object(
            colima, "_start", return_value=colima.ColimaStatus.UNHEALTHY
        ),
    ):
        assert colima.start() == colima.ColimaStatus.UNHEALTHY

    assert vm.cmds == []


@pytest.mark.usefixtures("m4_mac")
def test_start_warns_if_colima_doesnt_come_back_after_the_upgrade(
    capsys: pytest.CaptureFixture[str],
) -> None:
    vm = FakeVM(
        start_results=(
            colima.ColimaStatus.UP,
            colima.ColimaStatus.UNHEALTHY,
            colima.ColimaStatus.UNHEALTHY,
        )
    )
    with (
        mock.patch("devenv.lib.colima.proc.run", side_effect=vm.run),
        mock.patch.object(colima, "_start", side_effect=vm.start),
        mock.patch.object(colima, "check", return_value=colima.ColimaStatus.UP),
        mock.patch.object(
            colima,
            "_prepare_docker_store",
            return_value=colima._StoragePolicy(existing_instance=False),
        ),
    ):
        assert colima.start() == colima.ColimaStatus.UNHEALTHY

    assert "isn't healthy after restarting" in capsys.readouterr().out
    assert vm.restarts == 1
    assert vm.recoveries == 1


def test_start_only_selects_colima_context_when_up() -> None:
    with (
        mock.patch(
            "devenv.lib.colima.check", return_value=colima.ColimaStatus.UP
        ),
        mock.patch.object(
            colima,
            "_prepare_docker_store",
            return_value=colima._StoragePolicy(existing_instance=False),
        ),
        mock.patch("devenv.lib.colima.proc.run") as mock_run,
        mock.patch(
            "devenv.lib.colima._upgrade_kernel_if_sve_misreported",
            return_value=False,
        ),
    ):
        assert colima.start() == colima.ColimaStatus.UP

    # no restart, but a previously interrupted start may have left docker
    # on the "default" context
    mock_run.assert_called_once_with(("docker", "context", "use", "colima"))


def test_start_switches_context_around_starting() -> None:
    with (
        mock.patch(
            "devenv.lib.colima.check",
            side_effect=[colima.ColimaStatus.DOWN, colima.ColimaStatus.UP],
        ),
        mock.patch.object(
            colima,
            "_prepare_docker_store",
            return_value=colima._StoragePolicy(existing_instance=False),
        ),
        mock.patch("devenv.lib.colima.rosetta.ensure"),
        mock.patch("devenv.lib.colima.proc.run") as mock_run,
        mock.patch(
            "devenv.lib.colima._upgrade_kernel_if_sve_misreported",
            return_value=False,
        ),
    ):
        assert colima.start() == colima.ColimaStatus.UP

    cmds = [c.args[0][:3] for c in mock_run.call_args_list]
    assert cmds == [
        ("docker", "context", "use"),
        ("colima", "start", "--verbose"),
        ("docker", "context", "use"),
    ]
    assert mock_run.call_args_list[0].args[0][3] == "default"
    assert mock_run.call_args_list[-1].args[0][3] == "colima"


def test_restart_when_up() -> None:
    with (
        mock.patch(
            "devenv.lib.colima.check",
            side_effect=[colima.ColimaStatus.UP, colima.ColimaStatus.UP],
        ),
        mock.patch.object(
            colima,
            "_prepare_docker_store",
            return_value=colima._StoragePolicy(existing_instance=False),
        ),
        mock.patch("devenv.lib.colima.rosetta.ensure"),
        mock.patch("devenv.lib.colima.proc.run") as mock_run,
        mock.patch(
            "devenv.lib.colima._upgrade_kernel_if_sve_misreported",
            return_value=False,
        ),
    ):
        assert colima.restart() == colima.ColimaStatus.UP

    cmds = [c.args[0][:2] for c in mock_run.call_args_list]
    assert ("colima", "stop") in cmds
    assert ("colima", "stop", "-f") not in [
        c.args[0][:3] for c in mock_run.call_args_list
    ]
    assert ("colima", "start") in cmds


def test_unhealthy_start_gets_one_bounded_recovery() -> None:
    from devenv import colima as colima_cmd
    from devenv.lib.context import Context

    context: Context = {"config_path": "", "code_root": "", "repo": None}
    with mock.patch(
        "devenv.colima.colima.start", return_value=colima.ColimaStatus.UNHEALTHY
    ) as start:
        assert colima_cmd.main(context, ["start"]) == 1

    start.assert_called_once_with()


@pytest.mark.usefixtures("m4_mac")
def test_post_start_health_recovery_still_repairs_the_kernel() -> None:
    vm = FakeVM(
        start_results=(
            colima.ColimaStatus.UNHEALTHY,
            colima.ColimaStatus.UP,
            colima.ColimaStatus.UP,
        )
    )

    assert (
        _start(vm, initial_status=colima.ColimaStatus.DOWN)
        == colima.ColimaStatus.UP
    )

    assert vm.start_modes == [
        colima._StartMode.ENSURE_RUNNING,
        colima._StartMode.HEALTH_RECOVERY,
        colima._StartMode.REQUESTED_RESTART,
    ]
    assert vm.start_existing_instances == [False, True, True]
    assert vm.recoveries == 1
    assert vm.restarts == 1
    assert vm.running == FIXED_KERNEL


@pytest.mark.usefixtures("m4_mac")
def test_kernel_restart_recovery_validates_the_booted_kernel(
    capsys: pytest.CaptureFixture[str],
) -> None:
    vm = FakeVM(
        start_results=(
            colima.ColimaStatus.UP,
            colima.ColimaStatus.UNHEALTHY,
            colima.ColimaStatus.UP,
        )
    )

    assert _start(vm) == colima.ColimaStatus.UP

    assert vm.start_modes == [
        colima._StartMode.ENSURE_RUNNING,
        colima._StartMode.REQUESTED_RESTART,
        colima._StartMode.HEALTH_RECOVERY,
    ]
    assert vm.start_existing_instances == [False, True, True]
    assert vm.restarts == 1
    assert vm.recoveries == 1
    assert vm.running == FIXED_KERNEL
    assert vm.cmds.count(APT_INSTALL) == 1
    assert vm.ran(
        ("colima", "ssh", "--", "grep", "-m1", "^Features", "/proc/cpuinfo")
    )
    assert f"colima's VM is now running Linux {FIXED_KERNEL}." in (
        capsys.readouterr().out
    )


def test_start_from_down_does_not_force_stop() -> None:
    with (
        mock.patch.object(colima, "rosetta") as rosetta,
        mock.patch.object(colima, "check", return_value=colima.ColimaStatus.UP),
        mock.patch.object(colima, "proc") as proc,
        mock.patch("devenv.lib.colima.platform.machine", return_value="arm64"),
        mock.patch("devenv.lib.colima.os.cpu_count", return_value=8),
        mock.patch(
            "devenv.lib.colima.os.sysconf", side_effect=(4096, 8_388_608)
        ),
    ):
        assert (
            colima._start(
                colima._StartMode.ENSURE_RUNNING,
                colima.ColimaStatus.DOWN,
                existing_instance=False,
            )
            == colima.ColimaStatus.UP
        )

    rosetta.ensure.assert_called_once_with()
    commands = [call.args[0] for call in proc.run.call_args_list]
    assert ("colima", "stop", "-f") not in commands
    start = next(
        command for command in commands if command[:2] == ("colima", "start")
    )
    assert "--cpus" in start
    assert "--cpu" not in start
    assert "--disk" in start and "512" in start
    assert "--save-config" in start
    assert "--mount-inotify" not in start
    assert "--vm-type=vz" in start
    assert "--vz-rosetta" in start
    assert "--mount-type=virtiofs" in start


def test_existing_start_preserves_saved_vm_settings() -> None:
    with (
        mock.patch.object(colima, "rosetta") as rosetta,
        mock.patch.object(colima, "check", return_value=colima.ColimaStatus.UP),
        mock.patch.object(colima, "proc") as proc,
        mock.patch("devenv.lib.colima.os.cpu_count", return_value=8),
        mock.patch(
            "devenv.lib.colima.os.sysconf", side_effect=(4096, 8_388_608)
        ),
    ):
        assert (
            colima._start(
                colima._StartMode.REQUESTED_RESTART,
                colima.ColimaStatus.UP,
                existing_instance=True,
            )
            == colima.ColimaStatus.UP
        )

    rosetta.ensure.assert_called_once_with()
    commands = [call.args[0] for call in proc.run.call_args_list]
    assert ("colima", "stop") in commands
    assert ("colima", "stop", "-f") not in commands
    start = next(
        command for command in commands if command[:2] == ("colima", "start")
    )
    assert start == ("colima", "start", "--verbose")
    assert "--mount-inotify" not in start


def test_colima_upgrade_and_uninstall_preserve_standalone_lima_data(
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    sentinel = home / ".lima/default/lima.yaml"
    sentinel.parent.mkdir(parents=True)
    sentinel.write_bytes(b"independent lima vm\x00state")
    original = sentinel.read_bytes()
    colima_disk = home / ".colima/_lima/colima/diffdisk"
    colima_disk.parent.mkdir(parents=True)
    colima_disk.write_bytes(b"persistent Colima data")
    original_colima_disk = colima_disk.read_bytes()
    binroot = tmp_path / "sentry-devenv/bin"
    binroot.mkdir(parents=True)
    unrelated_binary = binroot / "docker"
    unrelated_binary.write_bytes(b"unrelated executable")
    old_shim = binroot / "colima"
    old_shim.write_text("#!/bin/sh\nexit 0\n")
    old_shim.chmod(0o755)
    old_binary = binroot / "colima-bin"
    old_binary.write_bytes(b"old Colima executable")
    downloads: list[tuple[str, str, str]] = []
    versions = iter(("colima version v0.8.1", "colima version v0.10.3"))

    def which(command: str, path: str | None = None) -> str | None:
        if command == "colima" and path == str(binroot):
            return str(binroot / "colima")
        return None

    def install(url: str, sha256: str, into: str) -> None:
        downloads.append((url, sha256, into))
        binary = Path(into) / "colima-bin"
        binary.write_text("#!/bin/sh\nexit 0\n")
        binary.chmod(0o775)

    with (
        mock.patch.object(colima, "home", str(home)),
        mock.patch.object(colima, "root", str(tmp_path / "sentry-devenv")),
        mock.patch.object(colima, "SYSTEM_MACHINE", "darwin_arm64"),
        mock.patch("devenv.lib.colima.shutil.which", side_effect=which),
        mock.patch(
            "devenv.lib.colima.proc.run",
            side_effect=lambda *a, **k: next(versions),
        ),
        mock.patch("devenv.lib.colima._install", side_effect=install),
    ):
        colima.install_global()
        assert sentinel.read_bytes() == original
        assert colima_disk.read_bytes() == original_colima_disk
        assert unrelated_binary.read_bytes() == b"unrelated executable"
        colima.uninstall(str(binroot))

    assert downloads == [
        (
            "https://github.com/abiosoft/colima/releases/download/v0.10.3/colima-Darwin-arm64",
            "980ad8bf61a4ca370243f4cb41401a61276dcd2c2502bee7b9b86f9250169f34",
            str(binroot),
        )
    ]
    assert sorted(path.name for path in binroot.iterdir()) == ["docker"]
    assert unrelated_binary.read_bytes() == b"unrelated executable"
    assert sentinel.read_bytes() == original
    assert colima_disk.read_bytes() == original_colima_disk


def test_interrupted_colima_upgrade_preserves_installed_binary_and_lima_data(
    tmp_path: Path,
) -> None:
    home = tmp_path / "home"
    sentinel = home / ".lima/default/lima.yaml"
    sentinel.parent.mkdir(parents=True)
    sentinel.write_bytes(b"independent lima vm\x00state")
    original = sentinel.read_bytes()
    binroot = tmp_path / "sentry-devenv/bin"
    binroot.mkdir(parents=True)
    shim = binroot / "colima"
    shim.write_text("#!/bin/sh\nexec colima-bin\n")
    shim.chmod(0o755)
    binary = binroot / "colima-bin"
    binary.write_bytes(b"Colima 0.8.1")
    original_binary = binary.read_bytes()

    with (
        mock.patch.object(colima, "root", str(tmp_path / "sentry-devenv")),
        mock.patch.object(colima, "SYSTEM_MACHINE", "darwin_arm64"),
        mock.patch("devenv.lib.colima.shutil.which", return_value=str(shim)),
        mock.patch(
            "devenv.lib.colima.proc.run", return_value="colima version v0.8.1"
        ),
        mock.patch(
            "devenv.lib.colima._install",
            side_effect=RuntimeError("download interrupted"),
        ),
        pytest.raises(RuntimeError, match="download interrupted"),
    ):
        colima.install_global()

    assert binary.read_bytes() == original_binary
    assert shim.is_file()
    assert sentinel.read_bytes() == original


def test_interrupted_colima_shim_is_reinstalled(tmp_path: Path) -> None:
    binroot = tmp_path / "sentry-devenv/bin"
    binroot.mkdir(parents=True)
    shim = binroot / "colima"
    shim.write_text("#!/bin/sh\nexec colima-bin\n")
    shim.chmod(0o755)
    versions = iter(
        (RuntimeError("colima-bin is missing"), "colima version v0.10.3")
    )

    def installed_version(command: tuple[str, ...], **kwargs: object) -> str:
        result = next(versions)
        if isinstance(result, RuntimeError):
            raise result
        return result

    def install(url: str, sha256: str, into: str) -> None:
        binary = Path(into) / "colima-bin"
        binary.write_bytes(b"reinstalled Colima")
        binary.chmod(0o775)

    with (
        mock.patch.object(colima, "root", str(tmp_path / "sentry-devenv")),
        mock.patch.object(colima, "SYSTEM_MACHINE", "darwin_arm64"),
        mock.patch("devenv.lib.colima.shutil.which", return_value=str(shim)),
        mock.patch("devenv.lib.colima.proc.run", side_effect=installed_version),
        mock.patch("devenv.lib.colima._install", side_effect=install),
    ):
        colima.install_global()

    assert (binroot / "colima-bin").read_bytes() == b"reinstalled Colima"
    assert f"exec {binroot}/colima-bin" in shim.read_text()
