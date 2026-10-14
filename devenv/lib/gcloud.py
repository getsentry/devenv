from __future__ import annotations

import os
import shutil
import tempfile

from devenv.constants import root
from devenv.lib import archive
from devenv.lib import fs
from devenv.lib import proc

# Wrapper scripts written by _install().
_WRAPPER_BINS = ("gcloud", "gsutil", "docker-credential-gcloud")
# All binaries we own in binroot: wrapper scripts + the gke-gcloud-auth-plugin symlink.
_ALL_BINS = _WRAPPER_BINS + ("gke-gcloud-auth-plugin",)

_WRAPPER_SCRIPT = """#!/bin/sh
export CLOUDSDK_PYTHON={root}/python/bin/python3 \
       PATH={into}/google-cloud-sdk/bin:"${{PATH}}"
exec {name} "$@"
"""


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
    for name in _WRAPPER_BINS:
        fs.write_script(
            f"{into}/{name}",
            _WRAPPER_SCRIPT,
            shell_escape={"root": root, "into": into, "name": name},
        )


def uninstall(binroot: str) -> None:
    shutil.rmtree(f"{binroot}/google-cloud-sdk", ignore_errors=True)

    for name in _ALL_BINS:
        try:
            os.remove(f"{binroot}/{name}")
        except FileNotFoundError:
            # it's better to do this than to guard with
            # os.path.exists(fp) because if it's an invalid or circular
            # symlink the result'll be False!
            pass


def install(version: str, url: str, sha256: str, reporoot: str) -> None:
    print(
        "!!! devenv-managed gcloud is deprecated! run `brew install --cask gcloud-cli` !!!"
    )

    binroot = fs.ensure_binroot(reporoot)

    if all(
        shutil.which(name, path=binroot) == f"{binroot}/{name}"
        for name in _ALL_BINS
    ):
        with open(f"{binroot}/google-cloud-sdk/VERSION", "r") as f:
            installed_version = f.read().strip()
            if version == installed_version:
                return
            print(f"installed gcloud {installed_version} is unexpected!")

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

    fs.ensure_symlink(
        f"{binroot}/google-cloud-sdk/bin/gke-gcloud-auth-plugin",
        f"{binroot}/gke-gcloud-auth-plugin",
    )

    stdout = proc.run((f"{binroot}/gcloud", "--version"), stdout=True)
    if "gke-gcloud-auth-plugin" not in stdout:
        raise SystemExit("Failed to install gcloud {version}!")
