from __future__ import annotations

import os
import shutil
import tempfile

from devenv.constants import bin_root
from devenv.constants import root
from devenv.lib import archive
from devenv.lib import fs
from devenv.lib import proc


def _install(url: str, sha256: str, into: str) -> None:
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


def uninstall() -> None:
    for d in (f"{bin_root}/google-cloud-sdk",):
        shutil.rmtree(d, ignore_errors=True)

    for f in (f"{bin_root}/gcloud", f"{bin_root}/gsutil"):
        if os.path.exists(f):
            os.remove(f)


def install(version: str, url: str, sha256: str) -> None:
    if (
        shutil.which("gcloud", path=bin_root) == f"{bin_root}/gcloud"
        and shutil.which("gsutil", path=bin_root) == f"{bin_root}/gsutil"
    ):
        with open(f"{bin_root}/google-cloud-sdk/VERSION", "r") as f:
            installed_version = f.read().strip()
            if version == installed_version:
                return
            print(f"installed gcloud {installed_version} is outdated!")

    print(f"installing gcloud {version}...")
    uninstall()
    _install(url, sha256, bin_root)

    proc.run(
        (
            f"{bin_root}/gcloud",
            "components",
            "install",
            "-q",
            "--verbosity=error",
            "gke-gcloud-auth-plugin",
        )
    )

    stdout = proc.run((f"{bin_root}/gcloud", "--version"), stdout=True)
    if "gke-gcloud-auth-plugin" not in stdout:
        raise SystemExit("Failed to install gcloud {version}!")
