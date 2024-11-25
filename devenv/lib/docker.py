from __future__ import annotations

import os
import shutil
import socket
import subprocess
import tempfile
from threading import Thread

from devenv.constants import root
from devenv.constants import SYSTEM_MACHINE
from devenv.lib import archive
from devenv.lib import proc


def _accept_and_close(sock: socket.socket) -> None:
    sock.listen()
    conn, addr = sock.accept()
    conn.close()


def check_docker_to_host_connectivity(timeout: int = 3) -> bool:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]

    listener = Thread(target=_accept_and_close, args=(sock,))
    listener.start()

    rc = subprocess.call(
        (
            "docker",
            "run",
            "--rm",
            "--add-host=host.docker.internal:host-gateway",
            "busybox:1.36.1-musl",
            "/bin/sh",
            "-c",
            f"/bin/echo hi | /bin/nc -w {timeout} host.docker.internal {port}",
        )
    )

    if rc != 0:
        # easiest way to terminate the socket server
        # (so the thread doesn't indefinitely hang)
        with socket.socket() as s:
            s.connect(("127.0.0.1", port))
            s.send(b"die")

        listener.join()
        return False

    listener.join()
    return True


def uninstall(binroot: str) -> None:
    for fp in (f"{binroot}/docker",):
        try:
            os.remove(fp)
        except FileNotFoundError:
            # it's better to do this than to guard with
            # os.path.exists(fp) because if it's an invalid or circular
            # symlink the result'll be False!
            pass


def _install(url: str, sha256: str, into: str) -> None:
    os.makedirs(into, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=into) as tmpd:
        archive_file = archive.download(url, sha256, dest=f"{tmpd}/download")
        archive.unpack_strip_n(archive_file, tmpd, n=1)

        # the archive was atomically placed into tmpd so
        # these are on the same fs and can be atomically moved too
        os.replace(f"{tmpd}/docker", f"{into}/docker")


def install_global() -> None:
    version = "27.3.1"
    cfg = {
        "darwin_x86_64": "https://download.docker.com/mac/static/stable/x86_64/docker-27.3.1.tgz",
        "darwin_x86_64_sha256": "1b621d4c9a57ff361811cf29754aafb0c28bc113c70011927af8d73c2c162186",
        "darwin_arm64": "https://download.docker.com/mac/static/stable/aarch64/docker-27.3.1.tgz",
        "darwin_arm64_sha256": "9dae125282116146b06eb777c2125ddda6c0468c0b9ad6c72a82edbc6783a77b",
        "linux_x86_64": "https://download.docker.com/linux/static/stable/x86_64/docker-27.3.1.tgz",
        "linux_x86_64_sha256": "9b4f6fe406e50f9085ee474c451e2bb5adb119a03591f467922d3b4e2ddf31d3",
    }

    binroot = f"{root}/bin"

    if shutil.which("docker", path=binroot) == f"{binroot}/docker":
        stdout = proc.run((f"{binroot}/docker", "--version"), stdout=True)
        installed_version = stdout.strip().split()[2][:-1]
        if version == installed_version:
            return
        print(f"installed docker {installed_version} is outdated!")

    print(f"installing docker (cli, not desktop) {version}...")
    uninstall(binroot)
    _install(cfg[SYSTEM_MACHINE], cfg[f"{SYSTEM_MACHINE}_sha256"], binroot)

    stdout = proc.run((f"{binroot}/docker", "--version"), stdout=True)
    if f"Docker version {version}" not in stdout:
        raise SystemExit(f"Failed to install docker {version}! Found: {stdout}")
