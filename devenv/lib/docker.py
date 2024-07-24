from __future__ import annotations

import socket
import subprocess
from threading import Thread


def _accept_and_close(sock: socket.socket) -> None:
    sock.listen()
    conn, addr = sock.accept()
    conn.close()


def check_docker_to_host_connectivity(timeout: int = 3) -> bool:
    sock = socket.socket()
    sock.bind(("", 0))
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
            f"/bin/echo hi | /bin/nc -w {timeout} host.docker.internal 6968",
        )
    )

    if rc != 0:
        # easiest way to terminate the socket server
        # (so the thread doesn't indefinitely hang)
        s = socket.socket()
        s.connect(("127.0.0.1", port))
        s.send(b"hi")
        s.close()
        return False

    listener.join()
    return True
