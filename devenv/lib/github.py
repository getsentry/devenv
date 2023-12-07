from __future__ import annotations

import os
import tempfile

from devenv.constants import CI
from devenv.constants import EXTERNAL_CONTRIBUTOR
from devenv.constants import home
from devenv.lib import fs
from devenv.lib import proc

# https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/githubs-ssh-key-fingerprints
fingerprints = """
github.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl
github.com ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBEmKSENjQEezOmxkZMy7opKgwFB9nkt5YRrYMjNuG5N87uRgg6CLrbo5wAdT/y6v0mKV0U2w0WZ2YB/++Tpockg=
github.com ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCj7ndNxQowgcQnjshcLrqPEiiphnt+VTTvDP6mHBL9j1aNUkY4Ue1gvwnGLVlOhGeYrnZaMgRK6+PKCUXaDbC7qtbW8gIkhL7aGCsOr/C56SJMy/BCZfxd1nWzAOxSDPgVsmerOBYfNqltV9/hWCqBywINIR+5dIg6JTJ72pcEpEjcYgXkE2YEFXV1JHnsKgbLWNlhScqb2UmyRkQyytRLtL+38TGxkxCflmO+5Z8CSSNY7GidjMIZ7Q4zMjA2n1nGrlTDkzwDCsw+wqFPGQA179cnfGWOWRVruj16z6XyvxvjJwbz0wQZ75XK5tKSb7FNyeIEs4TT4jk+S4dhPeAUC5y+bDYirYgM4GC7uEnztnZyaVWQ7B381AK4Qdrwt51ZqExKbQpTUNn+EjqoTwvqNj4kqx5QUCI0ThS/YkOxJCXmPUWZbhjpCg56i+2aB6CmK2JGhn57K5mj0MNdBXA4/WnwH6XoPWJzK5Nyu2zB3nAZp+S5hpQs+p1vN1/wsjk=
"""  # noqa


def check_ssh_authentication() -> bool:
    try:
        # The remote prints to stderr and exits with code 1 in all cases.
        proc.run(("sh", "-c", "ssh -T git@github.com 2>&1"), stdout=True)
    except RuntimeError as e:
        # https://docs.github.com/en/authentication/connecting-to-github-with-ssh/testing-your-ssh-connection
        if "You've successfully authenticated" not in str(e):
            print(e)
            return False
    return True


def check_sso_configuration() -> bool:
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            proc.run(
                (
                    "git",
                    "-C",
                    tmpdir,
                    "clone",
                    "--quiet",
                    "--depth=1",
                    "git@github.com:getsentry/private.git",
                )
            )
            return True
    except RuntimeError as e:
        # Failing to clone private repos under getsentry
        # means that SSO isn't configured for the ssh key.
        print(e)
    return False


def check_ssh_access() -> bool:
    if CI:
        return True
    ssh_auth = check_ssh_authentication()
    return (
        ssh_auth
        if EXTERNAL_CONTRIBUTOR
        else ssh_auth and check_sso_configuration()
    )


def add_to_known_hosts() -> None:
    os.makedirs(f"{home}/.ssh", exist_ok=True)
    fs.idempotent_add(f"{home}/.ssh/known_hosts", fingerprints)


def generate_and_configure_ssh_keypair() -> str:
    fs.idempotent_add(
        f"{home}/.ssh/config",
        """Host github.com
  User git
  Hostname github.com
  PreferredAuthentications publickey
  IdentityFile ~/.ssh/sentry-github""",
    )
    private_key_path = f"{home}/.ssh/sentry-github"
    if not os.path.exists(private_key_path):
        proc.run(
            (
                "ssh-keygen",
                "-t",
                "ed25519",
                "-a",
                "100",
                "-N",
                "",
                "-f",
                private_key_path,
            ),
            exit=True,
        )
    with open(f"{private_key_path}.pub") as f:
        return f.read().strip()
