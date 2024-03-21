from __future__ import annotations

import os
import shutil
import tempfile

from devenv.constants import root
from devenv.lib import archive
from devenv.lib import fs
from devenv.lib import proc


def _install(url: str, sha256: str, into: str) -> None:
    os.makedirs(into, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=into) as tmpd:
        archive_file = archive.download(url, sha256, dest=f"{tmpd}/download")
        archive.unpack(archive_file, tmpd)

        # the archive was atomically placed into tmpd so
        # these are on the same fs and can be atomically moved too
        os.replace(f"{tmpd}/google-cloud-sdk", f"{into}/google-cloud-sdk")

    # I think gcloud will support 3.11 for quite some time, but this could
    # change to be more flexible in the future.
    # We run gcloud on 3.11 in gocd prod and it's been great,
    # and we may as well reuse devenv's internal python.
    fs.write_script(
        f"{into}/gcloud",
        f"""#!/bin/sh
exec /usr/bin/env CLOUDSDK_PYTHON={root}/python/bin/python3 PATH={into}/google-cloud-sdk/bin:$PATH gcloud "$@"
""",
    )
    fs.write_script(
        f"{into}/gsutil",
        f"""#!/bin/sh
exec /usr/bin/env CLOUDSDK_PYTHON={root}/python/bin/python3 PATH={into}/google-cloud-sdk/bin:$PATH gsutil "$@"
""",
    )


def uninstall(binroot: str) -> None:
    for d in (f"{binroot}/google-cloud-sdk",):
        shutil.rmtree(d, ignore_errors=True)

    for f in (f"{binroot}/gcloud", f"{binroot}/gsutil"):
        if os.path.exists(f):
            os.remove(f)


def install(version: str, url: str, sha256: str, reporoot: str) -> None:
    binroot = fs.ensure_binroot(reporoot)

    if (
        shutil.which("gcloud", path=binroot) == f"{binroot}/gcloud"
        and shutil.which("gsutil", path=binroot) == f"{binroot}/gsutil"
    ):
        with open(f"{binroot}/google-cloud-sdk/VERSION", "r") as f:
            installed_version = f.read().strip()
            if version == installed_version:
                return
            print(f"installed gcloud {installed_version} is outdated!")

    print(f"installing gcloud {version}...")
    uninstall(binroot)
    _install(url, sha256, binroot)

    proc.run(
        (
            f"{binroot}/gcloud",
            "components",
            "install",
            "-q",
            "--verbosity=error",
            "gke-gcloud-auth-plugin",
        )
    )

    stdout = proc.run((f"{binroot}/gcloud", "--version"), stdout=True)
    if "gke-gcloud-auth-plugin" not in stdout:
        raise SystemExit("Failed to install gcloud {version}!")
