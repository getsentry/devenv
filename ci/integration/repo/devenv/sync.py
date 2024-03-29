from __future__ import annotations

from devenv.constants import SYSTEM_MACHINE
from devenv.lib import config
from devenv.lib import tenv
from devenv.lib import venv


def main(context: dict[str, str]) -> int:
    reporoot = context["reporoot"]

    cfg = config.get_repo(reporoot)

    tenv.install(
        cfg["tenv"]["version"],
        cfg["tenv"][SYSTEM_MACHINE],
        cfg["tenv"][f"{SYSTEM_MACHINE}_sha256"],
        reporoot,
    )

    name = "foo"
    venv_dir, python_version, requirements, editable_paths, bins = venv.get(
        reporoot, name
    )
    url, sha256 = config.get_python(reporoot, python_version)
    print(f"ensuring {name} venv at {venv_dir}...")
    venv.ensure(venv_dir, python_version, url, sha256)

    print(f"syncing {name} with {requirements}...")
    venv.sync(reporoot, venv_dir, requirements, editable_paths, bins)

    return 0
